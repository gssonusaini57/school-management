from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Literal


BatchStatusT = Literal["draft", "submitted"]
MerStatusT = Literal["pending", "approved", "rejected"]
MerRoleT = Literal["admin", "staff"]


# ── Marks rows shipped with a batch ─────────────────────────────
class MarkItemIn(BaseModel):
    student_id: int
    marks: int


class MarkItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    marks: int


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
    max_marks: int = Field(ge=1, le=1000)
    items: list[MarkItemIn] = Field(default_factory=list)


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


class BatchDetailOut(BatchOut):
    items: list[MarkItemOut] = []
    pending_edit_request_id: int | None = None
    last_rejection: str | None = None


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
