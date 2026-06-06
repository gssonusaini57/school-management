from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import date as date_t
from ..deps import db_dep, current_user, CurrentUser, assert_class_allowed
from ..schemas.attendance import AttendanceSave, AttendanceOut, AttendanceSummary, MarkedDatesOut
from ..models.attendance import Attendance, AttendanceRecord, AttendanceStatus
from ..events import broker
from ..logging_config import get_logger
from ._bulk import read_csv, parse_date_field, must_str, must_int, must_choice, FieldError, error_dict

router = APIRouter(prefix="/attendance", tags=["attendance"])
log = get_logger("app.audit.attendance")


@router.get("", response_model=AttendanceOut | None)
def get_attendance(
    class_name: str = Query(alias="class"),
    date: date_t = Query(...),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    assert_class_allowed(user, class_name)
    a = db.execute(
        select(Attendance).where(Attendance.class_name == class_name, Attendance.date == date)
    ).scalar_one_or_none()
    if not a:
        return None
    return AttendanceOut(
        class_name=a.class_name,
        date=a.date,
        records={r.student_id: r.status.value for r in a.records},
        is_holiday=a.is_holiday,
    )


@router.put("", status_code=204)
def save_attendance(
    payload: AttendanceSave,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    assert_class_allowed(user, payload.class_name)
    a = db.execute(
        select(Attendance).where(
            Attendance.class_name == payload.class_name, Attendance.date == payload.date
        )
    ).scalar_one_or_none()
    if not a:
        a = Attendance(class_name=payload.class_name, date=payload.date, updated_by=user.name)
        db.add(a)
        db.flush()
    else:
        a.updated_by = user.name
        for r in list(a.records):
            db.delete(r)
        db.flush()
    a.is_holiday = payload.is_holiday
    # A holiday is a day-level marker with no per-student records.
    if not payload.is_holiday:
        for sid, status in payload.records.items():
            if status not in ("P", "A", "L", "H"):
                raise HTTPException(status_code=400, detail=f"Bad status: {status}")
            db.add(AttendanceRecord(attendance_id=a.id, student_id=int(sid), status=AttendanceStatus(status)))
    db.commit()
    broker.publish("dashboard", "attendance_changed", date=str(payload.date))


@router.delete("", status_code=204)
def clear_attendance(
    class_name: str = Query(alias="class"),
    date: date_t = Query(...),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Clear a wrongly-marked day — remove the attendance row (records cascade)
    so the day is fully un-marked (also clears a holiday). Idempotent if absent."""
    assert_class_allowed(user, class_name)
    a = db.execute(
        select(Attendance).where(Attendance.class_name == class_name, Attendance.date == date)
    ).scalar_one_or_none()
    if a:
        db.delete(a)
        db.commit()
        broker.publish("dashboard", "attendance_changed", date=str(date))


@router.get("/today-summary", response_model=AttendanceSummary)
def today_summary(user: CurrentUser = Depends(current_user), db: Session = Depends(db_dep)):
    today = date_t.today()
    stmt = select(Attendance).where(Attendance.date == today)
    if user.role == "staff" and user.allowed_classes:
        stmt = stmt.where(Attendance.class_name.in_(user.allowed_classes))
    rows = db.execute(stmt).scalars().all()
    p = a = l = h = 0
    for att in rows:
        for r in att.records:
            if r.status == AttendanceStatus.P:
                p += 1
            elif r.status == AttendanceStatus.A:
                a += 1
            elif r.status == AttendanceStatus.L:
                l += 1
            else:
                h += 1
    total = p + a + l + h
    return AttendanceSummary(
        date=today, total=total, present=p, absent=a, leave=l, half_day=h,
        percent=round((p / total * 100), 2) if total else 0.0,
    )


@router.get("/marked-dates", response_model=MarkedDatesOut)
def marked_dates(
    class_name: str = Query(alias="class"),
    from_: date_t = Query(alias="from"),
    to: date_t = Query(alias="to"),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Which dates in [from, to] have an attendance record for this class.
    Staff-scoped (assert_class_allowed). Powers the mobile coverage calendar so
    one request covers a whole month instead of one GET per day."""
    assert_class_allowed(user, class_name)
    base = select(Attendance.date).where(
        Attendance.class_name == class_name,
        Attendance.date >= from_,
        Attendance.date <= to,
    )
    # Holidays have an attendance row too, so split them out — else they'd show
    # as "marked" on the calendar.
    marked = db.execute(
        base.where(~Attendance.is_holiday).distinct().order_by(Attendance.date)
    ).scalars().all()
    holidays = db.execute(
        base.where(Attendance.is_holiday).distinct().order_by(Attendance.date)
    ).scalars().all()
    return MarkedDatesOut(dates=marked, holidays=holidays)


@router.post("/bulk-import", status_code=201)
async def bulk_import_attendance(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Bulk-import attendance. CSV columns: class_name, date, student_id, status (P/A/L).

    Atomic: if any row fails validation, nothing is saved — admin fixes the
    sheet and re-uploads. Existing class+date attendance entries are replaced
    only after the entire file passes validation.
    """
    rows = await read_csv(file)
    errors: list[dict] = []
    grouped: dict[tuple[str, date_t], list[tuple[int, AttendanceStatus]]] = defaultdict(list)

    for i, row in enumerate(rows, start=2):
        try:
            cls = must_str(row, "class_name")
            try:
                assert_class_allowed(user, cls)
            except HTTPException as he:
                raise FieldError("class_name", cls, str(he.detail)) from None
            d = parse_date_field(must_str(row, "date"), field="date")
            sid = must_int(row, "student_id")
            status = must_choice(
                {**row, "status": (row.get("status") or "").strip().upper()},
                "status", ("P", "A", "L"),
            )
            grouped[(cls, d)].append((sid, AttendanceStatus(status)))
        except Exception as e:
            errors.append(error_dict(i, e, row))

    if errors:
        log.warning(
            "bulk import rejected",
            extra={"event": "bulk_import_rejected", "entity": "attendance", "rows_total": len(rows), "error_count": len(errors)},
        )
        return {"inserted": 0, "errors": errors, "aborted": True}

    inserted = 0
    for (cls, d), records in grouped.items():
        a = db.execute(
            select(Attendance).where(Attendance.class_name == cls, Attendance.date == d)
        ).scalar_one_or_none()
        if not a:
            a = Attendance(class_name=cls, date=d, updated_by=user.name)
            db.add(a)
            db.flush()
        else:
            a.updated_by = user.name
            for r in list(a.records):
                db.delete(r)
            db.flush()
        for sid, status in records:
            db.add(AttendanceRecord(attendance_id=a.id, student_id=sid, status=status))
        inserted += len(records)

    db.commit()
    if inserted:
        broker.publish("dashboard", "attendance_changed")
    log.info(
        "bulk import committed",
        extra={
            "event": "bulk_import_committed",
            "entity": "attendance",
            "row_count": inserted,
            "groups": len(grouped),
        },
    )
    return {"inserted": inserted, "errors": [], "aborted": False}
