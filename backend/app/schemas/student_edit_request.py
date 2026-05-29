from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any


class EditRequestRejectBody(BaseModel):
    reason: str | None = None


class EditRequestOut(BaseModel):
    """Serialized edit-request row used by the super-admin queue."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    student_name: str
    class_name: str | None = None
    requested_at: datetime
    requested_by: str
    requested_by_role: str
    changes: dict[str, dict[str, Any]]
    status: str
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    reject_reason: str | None = None


class EditRequestList(BaseModel):
    items: list[EditRequestOut]
