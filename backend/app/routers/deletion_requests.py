"""Super-admin queue for soft-deletion approvals.

Sits on top of the `status` column on `students` and `staff` (see
`backend/app/models/record_status.py`). Three actions: **approve** (move
pending → deleted; super-admin only), **restore** (anything → active; admin
or super-admin), and **purge** (hard-delete the row, cascading to documents/
attendance/marks/fees/staff_classes; super-admin only, and only after the
row is already in the `deleted` state).
"""
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..deps import db_dep, current_user, require_super_admin, CurrentUser
from ..models.student import Student
from ..models.staff import Staff
from ..models.record_status import RecordStatus
from ..events import broker
from ..logging_config import get_logger

router = APIRouter(prefix="/admin/deletion-requests", tags=["deletion-requests"])
log = get_logger("app.audit.deletion_requests")

Kind = Literal["student", "staff"]


def _row(db: Session, kind: Kind, rid: int):
    model = Student if kind == "student" else Staff
    s = db.get(model, rid)
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    return s


def _serialize(kind: Kind, s) -> dict:
    return {
        "kind": kind,
        "id": s.id,
        "name": s.name,
        "class_name": getattr(s, "class_name", None),
        "designation": getattr(s, "designation", None),
        "status": s.status.value if hasattr(s.status, "value") else str(s.status),
        "delete_requested_at": s.delete_requested_at.isoformat() if s.delete_requested_at else None,
        "delete_requested_by": s.delete_requested_by,
        "delete_reason": s.delete_reason,
        "deleted_at": s.deleted_at.isoformat() if s.deleted_at else None,
        "deleted_by": s.deleted_by,
    }


@router.get("")
def list_requests(
    status: str | None = Query(default=None, description="pending_delete | deleted"),
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    wanted: tuple[RecordStatus, ...]
    if status == "pending_delete":
        wanted = (RecordStatus.pending_delete,)
    elif status == "deleted":
        wanted = (RecordStatus.deleted,)
    else:
        wanted = (RecordStatus.pending_delete, RecordStatus.deleted)

    students = db.execute(
        select(Student).where(Student.status.in_(wanted))
    ).scalars().all()
    staff = db.execute(
        select(Staff).where(Staff.status.in_(wanted))
    ).scalars().all()

    items = [_serialize("student", s) for s in students] + [_serialize("staff", s) for s in staff]
    # Most-recent request/deletion first.
    items.sort(
        key=lambda r: r.get("delete_requested_at") or r.get("deleted_at") or "",
        reverse=True,
    )
    return {"items": items}


@router.post("/{kind}/{rid}/approve")
def approve(
    kind: Kind,
    rid: int,
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    """Pending → Deleted. 409 if not currently `pending_delete`."""
    s = _row(db, kind, rid)
    if s.status != RecordStatus.pending_delete:
        raise HTTPException(status_code=409, detail="Not pending deletion")
    now = datetime.utcnow()
    s.status = RecordStatus.deleted
    s.deleted_at = now
    s.deleted_by = user.name
    db.commit()
    broker.publish(f"{kind}s" if kind == "student" else "staff", "upsert", id=rid)
    broker.publish("deletion_requests", "upsert", kind=kind, id=rid)
    if kind == "student":
        broker.publish("dashboard", "students_changed")
    log.warning(
        f"{kind}_delete_approved",
        extra={"event": f"{kind}_delete_approved", f"{kind}_id": rid, "actor": user.name},
    )
    return _serialize(kind, s)


@router.post("/{kind}/{rid}/restore")
def restore(
    kind: Kind,
    rid: int,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Any non-active → Active. Available to both admin and super-admin."""
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    s = _row(db, kind, rid)
    if s.status == RecordStatus.active:
        raise HTTPException(status_code=409, detail="Already active")
    s.status = RecordStatus.active
    s.delete_requested_at = None
    s.delete_requested_by = None
    s.delete_reason = None
    s.deleted_at = None
    s.deleted_by = None
    db.commit()
    broker.publish(f"{kind}s" if kind == "student" else "staff", "upsert", id=rid)
    broker.publish("deletion_requests", "upsert", kind=kind, id=rid)
    if kind == "student":
        broker.publish("dashboard", "students_changed")
    log.warning(
        f"{kind}_restored",
        extra={"event": f"{kind}_restored", f"{kind}_id": rid, "actor": user.name},
    )
    return _serialize(kind, s)


@router.delete("/{kind}/{rid}", status_code=204)
def purge(
    kind: Kind,
    rid: int,
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    """Hard-delete (forces FK CASCADE). Only allowed from `deleted` status.

    Forces the two-step: super-admin must first approve a `pending_delete`
    into `deleted` before they can purge it. Prevents accidental
    one-click obliteration.
    """
    s = _row(db, kind, rid)
    if s.status != RecordStatus.deleted:
        raise HTTPException(status_code=409, detail="Must approve before purging (status must be 'deleted')")
    purged_name = s.name
    db.delete(s)
    db.commit()
    broker.publish(f"{kind}s" if kind == "student" else "staff", "delete", id=rid)
    broker.publish("deletion_requests", "delete", kind=kind, id=rid)
    if kind == "student":
        broker.publish("dashboard", "students_changed")
    log.warning(
        f"{kind}_purged",
        extra={"event": f"{kind}_purged", f"{kind}_id": rid, f"{kind}_name": purged_name, "actor": user.name},
    )
    return Response(status_code=204)
