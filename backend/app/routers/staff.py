import re
import secrets
from datetime import datetime
from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ..deps import db_dep, require_admin, current_user, CurrentUser
from ..schemas.staff import (
    StaffCreate,
    StaffUpdate,
    StaffOut,
    StaffCreateResponse,
    StaffUpdateResponse,
    StaffChangePasswordRequest,
    SetTempPasswordRequest,
)
from ..schemas.student import DeleteRequestBody
from ..models.staff import Staff, StaffClass
from ..models.record_status import RecordStatus
from ..security import hash_password, verify_password
from ..events import broker
from ..permissions import DEFAULT_STAFF_MENUS, sanitize_menus
from ..logging_config import get_logger
from ._bulk import read_csv, must_str, opt_str, title_case, FieldError, error_dict

router = APIRouter(prefix="/staff", tags=["staff"])
log = get_logger("app.audit.staff")

_EMPLOYEE_ID_RE = re.compile(r"^KIS/EMP/(\d{4})/(\d+)$")


def _to_out(s: Staff) -> StaffOut:
    return StaffOut(
        id=s.id,
        name=s.name,
        designation=s.designation,
        phone=s.phone,
        email=s.email,
        employee_id=s.employee_id,
        assigned_classes=[c.class_name for c in s.classes],
        allowed_menus=list(s.allowed_menus or []),
        force_password_change=bool(s.force_password_change),
        has_temp_password=bool(s.temp_password_hash),
        temp_password_set_at=s.temp_password_set_at,
        temp_password_set_by=s.temp_password_set_by,
        created_at=s.created_at,
        status=s.status.value if hasattr(s.status, "value") else str(s.status),
        delete_requested_at=s.delete_requested_at,
        delete_requested_by=s.delete_requested_by,
        delete_reason=s.delete_reason,
        deleted_at=s.deleted_at,
        deleted_by=s.deleted_by,
    )


def _gen_password() -> str:
    """6-digit numeric initial/reset password."""
    return f"{secrets.randbelow(900000) + 100000:06d}"


def _next_employee_id(db: Session, year: int) -> str:
    """Assign next sequence within the year for `KIS/EMP/{year}/{seq:04d}`."""
    prefix = f"KIS/EMP/{year:04d}/"
    rows = db.execute(
        select(Staff.employee_id).where(Staff.employee_id.like(f"{prefix}%"))
    ).scalars().all()
    max_seq = 0
    for eid in rows:
        m = _EMPLOYEE_ID_RE.match(eid or "")
        if m and m.group(1) == f"{year:04d}":
            try:
                max_seq = max(max_seq, int(m.group(2)))
            except ValueError:
                pass
    return f"{prefix}{max_seq + 1:04d}"


def _check_email_unique(db: Session, email: str, ignore_id: int | None = None) -> None:
    stmt = select(Staff.id).where(func.lower(Staff.email) == email.lower())
    if ignore_id is not None:
        stmt = stmt.where(Staff.id != ignore_id)
    row = db.execute(stmt).first()
    if row is not None:
        raise HTTPException(status_code=409, detail=f"Email {email} is already used by another staff member")


@router.get("", response_model=list[StaffOut])
def list_staff(
    include_deleted: bool = Query(default=False),
    status: str | None = Query(default=None, description="filter by status (e.g. pending_delete)"),
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    stmt = select(Staff)
    if status == "pending_delete":
        stmt = stmt.where(Staff.status == RecordStatus.pending_delete)
    elif status == "active":
        stmt = stmt.where(Staff.status == RecordStatus.active)
    elif not (include_deleted and user.role == "super_admin"):
        stmt = stmt.where(Staff.status != RecordStatus.deleted)
    rows = db.execute(stmt.order_by(Staff.name)).scalars().all()
    return [_to_out(s) for s in rows]


@router.post("", response_model=StaffCreateResponse, status_code=201)
def create_staff(
    payload: StaffCreate,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    email = payload.email.strip().lower()
    _check_email_unique(db, email)
    initial_password = _gen_password()
    employee_id = _next_employee_id(db, datetime.utcnow().year)
    menus = sanitize_menus(payload.allowed_menus) if payload.allowed_menus is not None else list(DEFAULT_STAFF_MENUS)
    s = Staff(
        name=payload.name,
        designation=payload.designation,
        phone=payload.phone,
        email=email,
        employee_id=employee_id,
        password_hash=hash_password(initial_password),
        force_password_change=True,
        allowed_menus=menus,
        updated_by=user.name,
    )
    s.classes = [StaffClass(class_name=c) for c in payload.assigned_classes]
    db.add(s)
    db.commit()
    db.refresh(s)
    broker.publish("staff", "upsert", id=s.id)
    log.info(
        "staff created",
        extra={
            "event": "staff_created",
            "staff_id": s.id,
            "staff_name": s.name,
            "employee_id": s.employee_id,
            "designation": s.designation,
            "assigned_classes": list(payload.assigned_classes),
        },
    )
    base = _to_out(s).model_dump()
    return StaffCreateResponse(**base, initial_password=initial_password)


@router.patch("/{sid}", response_model=StaffUpdateResponse)
def update_staff(
    sid: int,
    payload: StaffUpdate,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    s = db.get(Staff, sid)
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    if s.status == RecordStatus.deleted and user.role != "super_admin":
        raise HTTPException(status_code=404, detail="Not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data: s.name = data["name"]
    if "designation" in data: s.designation = data["designation"]
    if "phone" in data: s.phone = data["phone"]
    if "email" in data and data["email"]:
        new_email = str(data["email"]).strip().lower()
        if new_email != s.email:
            _check_email_unique(db, new_email, ignore_id=s.id)
            s.email = new_email
    new_password: str | None = None
    if data.get("reset_password"):
        new_password = _gen_password()
        s.password_hash = hash_password(new_password)
        s.force_password_change = True
    if "assigned_classes" in data and data["assigned_classes"] is not None:
        for c in list(s.classes):
            db.delete(c)
        db.flush()
        s.classes = [StaffClass(staff_id=s.id, class_name=c) for c in data["assigned_classes"]]
    if "allowed_menus" in data and data["allowed_menus"] is not None:
        s.allowed_menus = sanitize_menus(data["allowed_menus"])
    s.updated_by = user.name
    db.commit()
    db.refresh(s)
    broker.publish("staff", "upsert", id=s.id)
    log.info(
        "staff updated",
        extra={
            "event": "staff_updated",
            "staff_id": s.id,
            "fields": [k for k in data.keys() if k != "reset_password"],
            "password_reset": bool(new_password),
        },
    )
    base = _to_out(s).model_dump()
    return StaffUpdateResponse(**base, new_password=new_password)


@router.post("/change-password", status_code=204)
def staff_change_password(
    payload: StaffChangePasswordRequest,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    if user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff-only")
    try:
        sid = int(user.sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid subject") from None
    s = db.get(Staff, sid)
    if not s or s.status == RecordStatus.deleted:
        raise HTTPException(status_code=404, detail="Not found")
    if not verify_password(payload.current_password, s.password_hash):
        log.warning(
            "staff password change failed",
            extra={"event": "staff_password_change_failed", "staff_id": s.id},
        )
        raise HTTPException(status_code=400, detail="Current password incorrect")
    s.password_hash = hash_password(payload.new_password)
    s.force_password_change = False
    db.commit()
    broker.publish("staff", "upsert", id=s.id)
    log.info("staff password changed", extra={"event": "staff_password_changed", "staff_id": s.id})


@router.post("/{sid}/temp-password", response_model=StaffOut)
def set_temp_password(
    sid: int,
    payload: SetTempPasswordRequest,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    """Set a custom temporary password for a staff member (admin/super-admin).

    This is a SECOND credential — it does NOT change `password_hash`, so the teacher
    keeps logging in with their own password. The temp password also works (e.g. so an
    admin can cover an absent teacher) until an admin clears it. No auto-expiry.
    """
    s = db.get(Staff, sid)
    if not s or s.status == RecordStatus.deleted:
        raise HTTPException(status_code=404, detail="Not found")
    s.temp_password_hash = hash_password(payload.password)
    s.temp_password_set_at = datetime.utcnow()
    s.temp_password_set_by = user.name
    db.commit()
    db.refresh(s)
    broker.publish("staff", "upsert", id=s.id)
    log.info(
        "staff temp password set",
        extra={"event": "staff_temp_password_set", "staff_id": s.id, "actor": user.name},
    )
    return _to_out(s)


@router.delete("/{sid}/temp-password", response_model=StaffOut)
def clear_temp_password(
    sid: int,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    """Clear the temporary password (admin/super-admin). The teacher's own password is
    unaffected — it was never touched."""
    s = db.get(Staff, sid)
    if not s or s.status == RecordStatus.deleted:
        raise HTTPException(status_code=404, detail="Not found")
    s.temp_password_hash = None
    s.temp_password_set_at = None
    s.temp_password_set_by = None
    db.commit()
    db.refresh(s)
    broker.publish("staff", "upsert", id=s.id)
    log.info(
        "staff temp password cleared",
        extra={"event": "staff_temp_password_cleared", "staff_id": s.id, "actor": user.name},
    )
    return _to_out(s)


@router.delete("/{sid}", response_model=StaffOut)
def delete_staff(
    sid: int,
    body: DeleteRequestBody | None = Body(default=None),
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    """Soft-delete request workflow.

    - Admin       → status `active` → `pending_delete`.
    - Super-admin → status straight to `deleted`.
    - Hard purge is at DELETE /api/admin/deletion-requests/staff/{id}.
    """
    s = db.get(Staff, sid)
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    if s.status == RecordStatus.deleted and user.role != "super_admin":
        raise HTTPException(status_code=404, detail="Not found")

    reason = (body.reason if body else None) or None
    now = datetime.utcnow()

    if user.role == "super_admin":
        if s.status == RecordStatus.active:
            s.delete_requested_at = now
            s.delete_requested_by = user.name
            if reason:
                s.delete_reason = reason
        elif s.status == RecordStatus.pending_delete and reason:
            s.delete_reason = reason
        s.status = RecordStatus.deleted
        s.deleted_at = now
        s.deleted_by = user.name
        event = "staff_archived"
    else:  # admin
        if s.status != RecordStatus.active:
            raise HTTPException(status_code=409, detail="Already pending deletion or deleted")
        s.status = RecordStatus.pending_delete
        s.delete_requested_at = now
        s.delete_requested_by = user.name
        s.delete_reason = reason
        event = "staff_delete_requested"

    db.commit()
    db.refresh(s)
    broker.publish("staff", "upsert", id=sid)
    broker.publish("deletion_requests", "upsert", kind="staff", id=sid)
    log.warning(
        event,
        extra={"event": event, "staff_id": sid, "staff_name": s.name, "actor": user.name, "reason": reason},
    )
    return _to_out(s)


@router.post("/bulk-import", status_code=201)
async def bulk_import_staff(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    """Bulk-import staff. CSV columns: name, designation, phone, assigned_classes (semicolon-sep), email.

    Server auto-generates `employee_id` and a 6-digit `initial_password` for every row.
    Atomic: if any row fails validation, nothing is saved.
    Response includes `credentials[]` so the admin can export issued passwords.
    """
    rows = await read_csv(file)
    errors: list[dict] = []
    prepared: list[tuple[Staff, list[str], str]] = []  # (staff, classes, initial_password)
    seen_emails: set[str] = set()
    year = datetime.utcnow().year
    # Pre-compute starting sequence so multi-row imports get monotonic IDs.
    next_seq_start = _next_employee_id(db, year)
    m = _EMPLOYEE_ID_RE.match(next_seq_start)
    next_seq = int(m.group(2)) if m else 1
    for i, row in enumerate(rows, start=2):
        try:
            name = title_case(must_str(row, "name"))
            email = must_str(row, "email").strip().lower()
            if "@" not in email or "." not in email.split("@")[-1]:
                raise FieldError("email", email, "must be a valid email address")
            if email in seen_emails:
                raise FieldError("email", email, "duplicate email within this upload")
            classes = [c.strip() for c in (row.get("assigned_classes") or "").split(";") if c.strip()]
            if not classes:
                classes = ["All"]
            initial_password = _gen_password()
            employee_id = f"KIS/EMP/{year:04d}/{next_seq:04d}"
            next_seq += 1
            s = Staff(
                name=name,
                designation=opt_str(row, "designation", "Class Teacher"),
                phone=opt_str(row, "phone"),
                email=email,
                employee_id=employee_id,
                password_hash=hash_password(initial_password),
                force_password_change=True,
                allowed_menus=list(DEFAULT_STAFF_MENUS),
                updated_by=user.name,
            )
            prepared.append((s, classes, initial_password))
            seen_emails.add(email)
        except Exception as e:
            errors.append(error_dict(i, e, row))

    if errors:
        log.warning(
            "bulk import rejected",
            extra={"event": "bulk_import_rejected", "entity": "staff", "rows_total": len(rows), "error_count": len(errors)},
        )
        return {"inserted": 0, "errors": errors, "aborted": True, "credentials": []}

    # Cross-check against DB for email collisions before insert.
    if prepared:
        existing = db.execute(
            select(func.lower(Staff.email)).where(
                func.lower(Staff.email).in_([s.email for s, _, _ in prepared])
            )
        ).scalars().all()
        if existing:
            log.warning(
                "bulk import rejected",
                extra={"event": "bulk_import_rejected", "entity": "staff", "reason": "duplicate_emails", "collisions": list(existing)},
            )
            return {
                "inserted": 0,
                "errors": [{"row": 0, "reason": f"Emails already exist: {', '.join(existing)}", "data": {}}],
                "aborted": True,
                "credentials": [],
            }

    credentials: list[dict] = []
    for s, classes, initial_password in prepared:
        s.classes = [StaffClass(class_name=c) for c in classes]
        db.add(s)
        credentials.append({"email": s.email, "employee_id": s.employee_id, "initial_password": initial_password})
    db.commit()
    if prepared:
        broker.publish("staff", "upsert", id=0)
    log.info(
        "bulk import committed",
        extra={"event": "bulk_import_committed", "entity": "staff", "row_count": len(prepared)},
    )
    return {"inserted": len(prepared), "errors": [], "aborted": False, "credentials": credentials}
