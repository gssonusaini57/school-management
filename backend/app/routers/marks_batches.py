"""Draft → Submit → Lock → Edit-request workflow for marks entry.

Mirrors the student-edit-request pattern (`edit_requests.py`):
- Admin / staff can create + update draft batches and submit them.
- Once `submitted`, the batch is locked for admin/staff. They must file a
  `MarksEditRequest` with a reason; super-admin approves to flip the batch
  back to `draft`, or rejects with a reason.
- Super-admin bypasses everything: they can save / submit / edit a submitted
  batch directly. No request row written when super-admin acts.

Batches are identified by their (class, subject, exam_type, session) quadruple.
The UNIQUE index on (batch_id, student_id) on `marks` enforces upsert semantics
so re-saving never creates duplicate rows.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session, selectinload

from ..deps import db_dep, current_user, require_super_admin, CurrentUser, assert_class_allowed
from ..events import broker
from ..notifications import (
    notify_marks_edit_request, notify_marks_submitted, notify_request_outcome,
)
from ..logging_config import get_logger
from ..models.marks import Marks
from ..models.marks_batch import (
    MarksBatch, MarksBatchStatus,
    MarksEditRequest, MarksEditRequestStatus, MarksEditRequestRole,
)
from ..schemas.marks_batch import (
    BatchSaveBody, BatchOut, BatchDetailOut, MarkItemOut,
    RequestEditBody, RejectRequestBody,
    MarksEditRequestOut, MarksEditRequestList,
)

router = APIRouter(prefix="/marks/batches", tags=["marks-batches"])
queue_router = APIRouter(prefix="/admin/marks-edit-requests", tags=["marks-edit-requests"])
log = get_logger("app.audit.marks_batches")


# ── Helpers ─────────────────────────────────────────────────────
def _find_batch(db: Session, class_name: str, subject: str, exam_type: str, session: str) -> MarksBatch | None:
    return db.execute(
        select(MarksBatch).where(
            MarksBatch.class_name == class_name,
            MarksBatch.subject == subject,
            MarksBatch.exam_type == exam_type,
            MarksBatch.session == session,
        )
    ).scalar_one_or_none()


def _pending_request(db: Session, batch_id: int) -> MarksEditRequest | None:
    return db.execute(
        select(MarksEditRequest).where(
            MarksEditRequest.batch_id == batch_id,
            MarksEditRequest.status == MarksEditRequestStatus.pending,
        )
    ).scalar_one_or_none()


def _last_rejection(db: Session, batch_id: int) -> str | None:
    row = db.execute(
        select(MarksEditRequest)
        .where(
            MarksEditRequest.batch_id == batch_id,
            MarksEditRequest.status == MarksEditRequestStatus.rejected,
        )
        .order_by(MarksEditRequest.reviewed_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    return row.reject_reason if row else None


def _detail(db: Session, batch: MarksBatch) -> BatchDetailOut:
    items = db.execute(
        select(Marks).where(Marks.batch_id == batch.id).order_by(Marks.student_id)
    ).scalars().all()
    pending = _pending_request(db, batch.id)
    last_rej = None if pending else _last_rejection(db, batch.id)
    return BatchDetailOut(
        id=batch.id,
        class_name=batch.class_name,
        subject=batch.subject,
        exam_type=batch.exam_type,
        session=batch.session,
        max_marks=batch.max_marks,
        status=batch.status.value,
        created_at=batch.created_at,
        created_by=batch.created_by,
        submitted_at=batch.submitted_at,
        submitted_by=batch.submitted_by,
        updated_at=batch.updated_at,
        items=[MarkItemOut.model_validate(m) for m in items],
        pending_edit_request_id=pending.id if pending else None,
        last_rejection=last_rej,
    )


def _validate_items(items, max_marks: int) -> None:
    bad = [(it.student_id, it.marks) for it in items if it.marks < 0 or it.marks > max_marks]
    if bad:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"{len(bad)} entries are out of range (0–{max_marks})",
                "rows": [{"student_id": s, "marks": m, "max_marks": max_marks} for s, m in bad[:10]],
            },
        )


# ── Batch endpoints ─────────────────────────────────────────────
@router.get("", response_model=BatchDetailOut | None)
def get_batch(
    class_name: str = Query(alias="class"),
    subject: str = Query(),
    exam_type: str = Query(),
    session: str = Query(),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Return the single batch matching the 4-tuple, or `null` if none exists."""
    assert_class_allowed(user, class_name)
    batch = _find_batch(db, class_name, subject, exam_type, session)
    if not batch:
        return None
    return _detail(db, batch)


@router.post("", response_model=BatchDetailOut, status_code=200)
def save_batch(
    payload: BatchSaveBody,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Upsert a draft batch + its mark rows.

    - Refuses if the batch is submitted and the caller is not super-admin
      (they must request edit).
    - Creates a new draft batch if none exists for the 4-tuple.
    - Otherwise replaces the entire mark set under that batch via per-row upsert.
    """
    assert_class_allowed(user, payload.class_name)
    _validate_items(payload.items, payload.max_marks)

    batch = _find_batch(db, payload.class_name, payload.subject, payload.exam_type, payload.session)
    if batch and batch.status == MarksBatchStatus.submitted and user.role != "super_admin":
        raise HTTPException(
            status_code=409,
            detail="Batch is submitted (locked). Request edit before changing marks.",
        )

    if not batch:
        batch = MarksBatch(
            class_name=payload.class_name,
            subject=payload.subject,
            exam_type=payload.exam_type,
            session=payload.session,
            max_marks=payload.max_marks,
            status=MarksBatchStatus.draft,
            created_by=user.name,
        )
        db.add(batch)
        db.flush()  # need batch.id for the FK below

    # Sync max_marks in case super-admin updated the master after a draft was started.
    batch.max_marks = payload.max_marks

    # Upsert each item; delete entries that the client dropped from the payload
    # so the batch reflects exactly what the teacher sees on screen.
    existing = {
        m.student_id: m
        for m in db.execute(select(Marks).where(Marks.batch_id == batch.id)).scalars().all()
    }
    incoming_ids = {it.student_id for it in payload.items}

    for sid, m in existing.items():
        if sid not in incoming_ids:
            db.delete(m)

    for it in payload.items:
        m = existing.get(it.student_id)
        if m is None:
            db.add(Marks(
                student_id=it.student_id,
                batch_id=batch.id,
                class_name=batch.class_name,
                exam_type=batch.exam_type,
                subject=batch.subject,
                marks=it.marks,
                max_marks=batch.max_marks,
                session=batch.session,
                saved_by=user.name,
            ))
        else:
            m.marks = it.marks
            m.max_marks = batch.max_marks
            m.saved_by = user.name

    db.commit()
    db.refresh(batch)
    broker.publish("marks_batches", "upsert", id=batch.id)
    log.info(
        "marks_batch_saved",
        extra={
            "event": "marks_batch_saved",
            "batch_id": batch.id,
            "class_name": batch.class_name,
            "subject": batch.subject,
            "exam_type": batch.exam_type,
            "session": batch.session,
            "items": len(payload.items),
            "actor": user.name,
        },
    )
    return _detail(db, batch)


@router.post("/{batch_id}/submit", response_model=BatchDetailOut)
def submit_batch(
    batch_id: int,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Lock the batch (admin/staff/super-admin)."""
    batch = db.get(MarksBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    assert_class_allowed(user, batch.class_name)
    if batch.status == MarksBatchStatus.submitted:
        raise HTTPException(status_code=409, detail="Batch is already submitted")
    batch.status = MarksBatchStatus.submitted
    batch.submitted_at = datetime.utcnow()
    batch.submitted_by = user.name
    db.commit()
    db.refresh(batch)
    broker.publish("marks_batches", "upsert", id=batch.id)
    log.warning(
        "marks_batch_submitted",
        extra={
            "event": "marks_batch_submitted",
            "batch_id": batch.id,
            "class_name": batch.class_name,
            "subject": batch.subject,
            "exam_type": batch.exam_type,
            "actor": user.name,
        },
    )
    return _detail(db, batch)


@router.post("/{batch_id}/request-edit", response_model=MarksEditRequestOut, status_code=201)
def request_edit(
    batch_id: int,
    payload: RequestEditBody,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Admin/staff enqueue a request to unlock a submitted batch."""
    batch = db.get(MarksBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    assert_class_allowed(user, batch.class_name)
    if user.role == "super_admin":
        # Super-admin shouldn't be filing requests; they edit directly.
        raise HTTPException(status_code=403, detail="Super-admin should edit directly, not request approval")
    if batch.status != MarksBatchStatus.submitted:
        raise HTTPException(status_code=409, detail="Only submitted batches can be edit-requested")
    if _pending_request(db, batch.id):
        raise HTTPException(status_code=409, detail="A pending edit request already exists for this batch")

    role = MarksEditRequestRole(user.role) if user.role in ("admin", "staff") else MarksEditRequestRole.staff
    req = MarksEditRequest(
        batch_id=batch.id,
        requested_by=user.name,
        requested_by_role=role,
        reason=payload.reason.strip(),
        status=MarksEditRequestStatus.pending,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    broker.publish("marks_batches", "upsert", id=batch.id)
    broker.publish("marks_edit_requests", "upsert", id=req.id)
    notify_marks_edit_request(db, req, batch)
    log.warning(
        "marks_edit_requested",
        extra={
            "event": "marks_edit_requested",
            "batch_id": batch.id,
            "request_id": req.id,
            "actor": user.name,
            "reason": payload.reason,
        },
    )
    return _serialize_request(db, req, batch)


# ── Super-admin queue ───────────────────────────────────────────
def _serialize_request(db: Session, req: MarksEditRequest, batch: MarksBatch | None = None) -> MarksEditRequestOut:
    if batch is None:
        batch = db.get(MarksBatch, req.batch_id)
    student_count = 0
    if batch is not None:
        student_count = db.execute(
            select(func.count(Marks.id)).where(Marks.batch_id == batch.id)
        ).scalar_one() or 0
    return MarksEditRequestOut(
        id=req.id,
        batch_id=req.batch_id,
        class_name=batch.class_name if batch else "(deleted)",
        subject=batch.subject if batch else "(deleted)",
        exam_type=batch.exam_type if batch else "(deleted)",
        session=batch.session if batch else "(deleted)",
        student_count=student_count,
        requested_at=req.requested_at,
        requested_by=req.requested_by,
        requested_by_role=req.requested_by_role.value if hasattr(req.requested_by_role, "value") else str(req.requested_by_role),
        reason=req.reason,
        status=req.status.value if hasattr(req.status, "value") else str(req.status),
        reviewed_at=req.reviewed_at,
        reviewed_by=req.reviewed_by,
        reject_reason=req.reject_reason,
    )


@queue_router.get("", response_model=MarksEditRequestList)
def list_requests(
    _user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    rows = db.execute(
        select(MarksEditRequest).order_by(MarksEditRequest.requested_at.desc())
    ).scalars().all()
    return MarksEditRequestList(items=[_serialize_request(db, r) for r in rows])


@queue_router.post("/{rid}/approve", response_model=MarksEditRequestOut)
def approve_request(
    rid: int,
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    req = db.get(MarksEditRequest, rid)
    if not req:
        raise HTTPException(status_code=404, detail="Not found")
    if req.status != MarksEditRequestStatus.pending:
        raise HTTPException(status_code=409, detail="Already reviewed")
    batch = db.get(MarksBatch, req.batch_id)
    if not batch:
        raise HTTPException(status_code=410, detail="Batch no longer exists")
    # Approval flips the batch back to draft so the teacher can edit + re-submit.
    # submitted_at / submitted_by are kept as the last-known submission audit.
    batch.status = MarksBatchStatus.draft
    req.status = MarksEditRequestStatus.approved
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by = user.name
    db.commit()
    db.refresh(req)
    broker.publish("marks_batches", "upsert", id=batch.id)
    broker.publish("marks_edit_requests", "upsert", id=rid)
    notify_request_outcome(
        db, kind="marks edit", outcome="approved", requester=req.requested_by,
        detail=f"{batch.class_name} · {batch.subject} ({batch.exam_type})",
    )
    log.warning(
        "marks_edit_approved",
        extra={
            "event": "marks_edit_approved",
            "request_id": rid,
            "batch_id": batch.id,
            "requested_by": req.requested_by,
            "actor": user.name,
        },
    )
    return _serialize_request(db, req, batch)


@queue_router.post("/{rid}/reject", response_model=MarksEditRequestOut)
def reject_request(
    rid: int,
    body: RejectRequestBody | None = None,
    user: CurrentUser = Depends(require_super_admin),
    db: Session = Depends(db_dep),
):
    req = db.get(MarksEditRequest, rid)
    if not req:
        raise HTTPException(status_code=404, detail="Not found")
    if req.status != MarksEditRequestStatus.pending:
        raise HTTPException(status_code=409, detail="Already reviewed")
    batch = db.get(MarksBatch, req.batch_id)
    req.status = MarksEditRequestStatus.rejected
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by = user.name
    req.reject_reason = (body.reason if body else None) or None
    db.commit()
    db.refresh(req)
    broker.publish("marks_batches", "upsert", id=req.batch_id)
    broker.publish("marks_edit_requests", "upsert", id=rid)
    notify_request_outcome(
        db, kind="marks edit", outcome="rejected", requester=req.requested_by,
        detail=(f"{batch.class_name} · {batch.subject} ({batch.exam_type})" if batch else f"batch #{req.batch_id}"),
        reason=req.reject_reason,
    )
    log.warning(
        "marks_edit_rejected",
        extra={
            "event": "marks_edit_rejected",
            "request_id": rid,
            "batch_id": req.batch_id,
            "reason": req.reject_reason,
            "requested_by": req.requested_by,
            "actor": user.name,
        },
    )
    return _serialize_request(db, req, batch)
