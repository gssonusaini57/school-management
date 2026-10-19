from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Literal


BatchStatusT = Literal["draft", "submitted"]
SummaryStatusT = Literal["draft", "submitted", "none"]   # none: no marks saved for the exam yet
MerStatusT = Literal["pending", "approved", "rejected"]
MerRoleT = Literal["admin", "staff"]


# ── Marks rows shipped with a batch ─────────────────────────────
class MarkItemIn(BaseModel):
    """`marks` for numeric components; `grade` (A1…D) for grading components (max 0)."""
    student_id: int
    marks: int | None = None
    grade: str | None = Field(default=None, max_length=4)


class MarkItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    marks: int
    grade: str | None = None


# ── Batch CRUD ──────────────────────────────────────────────────
class BatchSaveBody(BaseModel):
    """Upsert payload for POST /marks/batches.

    The 4-tuple (class_name, subject, exam_type, session) identifies the batch.
    If no batch matches, one is created in `draft` status; if a draft batch
    exists, items are upserted (existing rows updated, new rows inserted).
    Submitted batches refuse this call for non-super-admin.
    """
    class_name: str = Field(min_length=1, max_length=20)
    subject: str = Field(min_length=1, max_length=60)
    exam_type: str = Field(min_length=1, max_length=80)
    session: str = Field(min_length=1, max_length=20)
    max_marks: int = Field(ge=0, le=1000)   # 0 = grading component (letters)
    items: list[MarkItemIn] = Field(default_factory=list)
    # The batch the screen loaded before the teacher edited it: its id, or
    # 0 / null when the test had no saved marks. When sent, the save is
    # refused (409) if the server's batch for the 4-tuple is a different one,
    # so a stale or failed load can't overwrite or prune saved marks.
    # Older apps omit it: their saves go through unchecked, except that they
    # may not remove saved marks (409).
    base_batch_id: int | None = Field(default=None, ge=0)
    # The `revision` of the batch the screen loaded. When sent and the batch
    # exists, the save is refused (409) if the batch changed since: an
    # outdated screen can't put back old marks or prune newer ones.
    base_revision: int | None = Field(default=None, ge=0)


class BatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    class_name: str
    subject: str
    exam_type: str
    session: str
    max_marks: int
    status: BatchStatusT
    created_at: datetime
    created_by: str
    submitted_at: datetime | None = None
    submitted_by: str | None = None
    updated_at: datetime
    revision: int         # send back as base_revision on the next save


class BatchDetailOut(BatchOut):
    items: list[MarkItemOut] = []
    pending_edit_request_id: int | None = None
    last_rejection: str | None = None


# ── Marks progress (GET /marks/batches/summary) ─────────────────
class BatchSummaryItem(BaseModel):
    """One exam component of a class subject in a session, with its batch's state."""
    class_name: str
    subject: str
    exam_type: str                 # the exam component's name
    term: int | None = None        # 1, 2, or None for both terms
    status: SummaryStatusT
    entered: int                   # students in class_size with a mark (or a grade, for graded exams)
    class_size: int                # active students; for an optional subject, the active students who take it
    updated_at: datetime | None = None   # None when status is "none"
    revision: int = 0              # 0 when status is "none"
    pending_edit_request: bool = False


class BatchSummaryTotals(BaseModel):
    draft: int
    submitted: int
    missing: int                   # items with status "none"


class BatchSummaryOut(BaseModel):
    session: str
    items: list[BatchSummaryItem]
    totals: BatchSummaryTotals


# ── Edit-request CRUD ───────────────────────────────────────────
class RequestEditBody(BaseModel):
    """Teacher submits a reason explaining why the locked batch needs editing."""
    reason: str = Field(min_length=1, max_length=2000)


class RejectRequestBody(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class MarksEditRequestOut(BaseModel):
    """Serialized row for the super-admin queue page."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    batch_id: int
    # Hydrated batch summary so the queue page doesn't need a second fetch.
    class_name: str
    subject: str
    exam_type: str
    session: str
    student_count: int
    requested_at: datetime
    requested_by: str
    requested_by_role: MerRoleT
    reason: str
    status: MerStatusT
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    reject_reason: str | None = None


class MarksEditRequestList(BaseModel):
    items: list[MarksEditRequestOut]
