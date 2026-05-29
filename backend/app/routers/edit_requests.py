"""Super-admin queue for student edit approvals.

Mirrors `deletion_requests.py` but writes to a dedicated `student_edit_requests`
table (keeps the old/new diff). PATCH /students/{id} for staff+admin enqueues a
row here; super-admin approves to apply the diff, or rejects with a reason.
Super-admin's own PATCHes apply directly (handled in students.py).
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import db_dep, require_super_admin, CurrentUser
from ..models.student import Student
from ..models.student_edit_request import StudentEditRequest, EditRequestStatus
from ..schemas.student_edit_request import EditRequestOut, EditRequestList, EditRequestRejectBody
from ..events import broker
from ..notifications import notify_request_outcome
from ..logging_config import get_logger
from .students import _compute_admission_id, _check_uniqueness

router = APIRouter(prefix="/admin/edit-requests", tags=["edit-requests"])
log = get_logger("app.audit.edit_requests")


def _serialize(req: StudentEditRequest, student: Student | None) -> EditRequestOut:
    return EditRequestOut(
        id=req.id,
        student_id=req.student_id,
        student_name=student.name if student else "(deleted)",
        class_name=student.class_name if student else None,
        requested_at=req.requested_at,
        requested_by=req.requested_by,
        requested_by_role=req.requested_by_role.value if hasattr(req.requested_by_role, "value") else str(req.requested_by_role),
        changes=dict(req.changes or {}),
        status=req.status.value if hasattr(req.status, "value") else str(req.status),
        reviewed_at=req.reviewed_at,
        reviewed_by=req.reviewed_by,
        reject_reason=req.reject_reason,
    )


@router.get("", response_model=EditRequestList)
def list_edit_requests(
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    rows = db.execute(
        select(StudentEditRequest).order_by(StudentEditRequest.requested_at.desc())
    ).scalars().all()
    items = []
    for r in rows:
        s = db.get(Student, r.student_id)
        items.append(_serialize(r, s))
    return EditRequestList(items=items)


def _apply_diff(db: Session, student: Student, changes: dict, actor: str) -> list[str]:
    """Apply each {field: {new: ...}} entry to the Student row.

    Re-validates uniqueness on admission_no/class_name/roll_no shifts. Recomputes
    admission_id from admission_no if it changed. Returns list of fields applied.
    """
    from ..schemas.student import StudentUpdate
    new_values = {k: v.get("new") for k, v in changes.items()}
    # Re-validate type coercion (Decimal/date) via Pydantic.
    validated = StudentUpdate(**new_values).model_dump(exclude_unset=True)
    applied: list[str] = []
    for k, v in validated.items():
        setattr(student, k, v)
        applied.append(k)
    if "admission_no" in validated:
        year = (student.created_at or datetime.utcnow()).year
        student.admission_id = _compute_admission_id(year, student.admission_no)
    if any(k in validated for k in ("admission_no", "class_name", "roll_no")):
        _check_uniqueness(
            db,
            admission_id=student.admission_id,
            class_name=student.class_name,
            roll_no=student.roll_no or None,
            exclude_id=student.id,
        )
    student.updated_by = f"super-admin (approved {actor})"
    return applied


@router.post("/{rid}/approve", response_model=EditRequestOut)
def approve(
    rid: int,
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    req = db.get(StudentEditRequest, rid)
    if not req:
        raise HTTPException(status_code=404, detail="Not found")
    if req.status != EditRequestStatus.pending:
        raise HTTPException(status_code=409, detail="Already reviewed")
    student = db.get(Student, req.student_id)
    if not student:
        raise HTTPException(status_code=410, detail="Student no longer exists")
    applied = _apply_diff(db, student, dict(req.changes or {}), req.requested_by)
    req.status = EditRequestStatus.approved
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by = user.name
    db.commit()
    db.refresh(req)
    broker.publish("edit_requests", "upsert", id=rid)
    broker.publish("students", "upsert", id=student.id, class_name=student.class_name)
    broker.publish("dashboard", "students_changed")
    notify_request_outcome(
        db, kind="student edit", outcome="approved", requester=req.requested_by,
        detail=student.name,
    )
    log.warning(
        "student_edit_approved",
        extra={
            "event": "student_edit_approved",
            "edit_request_id": rid,
            "student_id": student.id,
            "fields": applied,
            "requested_by": req.requested_by,
            "actor": user.name,
        },
    )
    return _serialize(req, student)


@router.post("/{rid}/reject", response_model=EditRequestOut)
def reject(
    rid: int,
    body: EditRequestRejectBody | None = None,
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    req = db.get(StudentEditRequest, rid)
    if not req:
        raise HTTPException(status_code=404, detail="Not found")
    if req.status != EditRequestStatus.pending:
        raise HTTPException(status_code=409, detail="Already reviewed")
    req.status = EditRequestStatus.rejected
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by = user.name
    req.reject_reason = (body.reason if body else None) or None
    db.commit()
    db.refresh(req)
    student = db.get(Student, req.student_id)
    broker.publish("edit_requests", "upsert", id=rid)
    broker.publish("students", "upsert", id=req.student_id, class_name=student.class_name if student else None)
    notify_request_outcome(
        db, kind="student edit", outcome="rejected", requester=req.requested_by,
        detail=student.name if student else f"#{req.student_id}", reason=req.reject_reason,
    )
    log.warning(
        "student_edit_rejected",
        extra={
            "event": "student_edit_rejected",
            "edit_request_id": rid,
            "student_id": req.student_id,
            "reason": req.reject_reason,
            "requested_by": req.requested_by,
            "actor": user.name,
        },
    )
    return _serialize(req, student)
