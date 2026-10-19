from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import date as date_t
from ..constants import fold_name
from ..deps import ADMIN_ROLES, db_dep, current_user, CurrentUser, assert_class_allowed, classes_in_scope
from ..schemas.attendance import (
    AttendanceSave, AttendanceOut, AttendanceSummary, MarkedDatesOut,
    ClassAttendanceRow, ClassAttendanceSummaryOut, ClassAttendanceTotals,
)
from ..models.attendance import Attendance, AttendanceRecord, AttendanceStatus
from ..services.attendance_summary import summarize_counts
from ..services.roster import active_class_sizes
from ..events import broker
from ..logging_config import get_logger
from ._bulk import read_csv, parse_date_field, must_str, must_int, must_choice, FieldError, error_dict

router = APIRouter(prefix="/attendance", tags=["attendance"])
log = get_logger("app.audit.attendance")

STATUS_KEYS = ("P", "A", "L", "H")
CLASS_SUMMARY_MAX_DAYS = 92   # about a quarter: enough for a month or a term so far


def _today() -> date_t:
    """The server's date; one place so tests can pin "today"."""
    return date_t.today()


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
    today = _today()
    stmt = select(Attendance).where(Attendance.date == today)
    if user.role not in ADMIN_ROLES:
        # A teacher sees their own classes; with none assigned that is nothing
        # (an empty IN matches no rows), never every class.
        stmt = stmt.where(Attendance.class_name.in_(user.allowed_classes or []))
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
    # Same rule as the per-student totals: a half day counts as half present.
    counted = summarize_counts({"P": p, "A": a, "L": l, "H": h})
    total = counted.working_days
    return AttendanceSummary(
        date=today, total=total, present=p, absent=a, leave=l, half_day=h,
        percent=round(counted.days_present / total * 100, 2) if total else 0.0,
    )


def _summary_range(from_: date_t | None, to: date_t | None) -> tuple[date_t, date_t]:
    """[from, to] for the class summary: both default to today and `to` stops at
    today. 422 when from is after to, or the range is over the day limit."""
    today = _today()
    start = from_ or today
    end = min(to or today, today)
    if start > end:
        raise HTTPException(
            status_code=422,
            detail=f"The start date {start} is after the end date {end}. "
                   "Pick a start date on or before the end date (the end date is never later than today).",
        )
    days = (end - start).days + 1
    if days > CLASS_SUMMARY_MAX_DAYS:
        raise HTTPException(
            status_code=422,
            detail=f"Pick a range of at most {CLASS_SUMMARY_MAX_DAYS} days ({start} to {end} is {days} days).",
        )
    return start, end


def _count_fields(c: dict[str, int]) -> dict:
    """present / absent / leave / half_day / records / percent for status counts."""
    s = summarize_counts(c)
    return dict(present=c["P"], absent=c["A"], leave=c["L"], half_day=c["H"],
                records=s.working_days, percent=s.pct)


@router.get("/class-summary", response_model=ClassAttendanceSummaryOut)
def class_summary(
    from_: date_t | None = Query(default=None, alias="from"),
    to: date_t | None = Query(default=None),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Attendance per class over [from, to] for the marked / pending classes view.

    Admins and the super-admin get every class, a teacher their own classes (none
    assigned: an empty list). Every class in scope is listed, marked or not, in
    CLASSES order. Holidays are counted in holiday_days and left out of the
    counts; percent counts a half day as half present (None with no records).
    """
    start, end = _summary_range(from_, to)
    classes = classes_in_scope(user)
    counts: dict[str, dict[str, int]] = {c: dict.fromkeys(STATUS_KEYS, 0) for c in classes}
    marked = dict.fromkeys(classes, 0)
    holidays = dict.fromkeys(classes, 0)
    if classes:
        requested = {fold_name(c): c for c in classes}   # rows may come back as "l.k.g" on MySQL
        in_range = (
            Attendance.class_name.in_(classes),
            Attendance.date >= start,
            Attendance.date <= end,
        )
        record_counts = db.execute(
            select(Attendance.class_name, AttendanceRecord.status, func.count())
            .select_from(AttendanceRecord)
            .join(Attendance, Attendance.id == AttendanceRecord.attendance_id)
            .where(*in_range, Attendance.is_holiday.is_(False))
            .group_by(Attendance.class_name, AttendanceRecord.status)
        ).all()
        for name, status, n in record_counts:
            cls = requested.get(fold_name(name))
            if cls is not None:
                counts[cls][getattr(status, "value", status)] += int(n)
        day_counts = db.execute(
            select(Attendance.class_name, Attendance.is_holiday, func.count(func.distinct(Attendance.date)))
            .where(*in_range)
            .group_by(Attendance.class_name, Attendance.is_holiday)
        ).all()
        for name, is_holiday, n in day_counts:
            cls = requested.get(fold_name(name))
            if cls is not None:
                (holidays if is_holiday else marked)[cls] += int(n)
    sizes = active_class_sizes(db, classes)

    rows = [
        ClassAttendanceRow(class_name=c, class_size=sizes[c], marked_days=marked[c],
                           holiday_days=holidays[c], **_count_fields(counts[c]))
        for c in classes
    ]
    totals = ClassAttendanceTotals(
        class_size=sum(sizes.values()),
        classes_marked=sum(1 for c in classes if marked[c] >= 1),
        classes_total=len(classes),
        **_count_fields({k: sum(c[k] for c in counts.values()) for k in STATUS_KEYS}),
    )
    return ClassAttendanceSummaryOut(from_=start, to=end, classes=rows, totals=totals)


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
            # Imported marks make the day a working day, so a holiday flag on it goes.
            a.is_holiday = False
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
