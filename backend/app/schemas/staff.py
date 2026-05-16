from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime


class StaffBase(BaseModel):
    name: str
    designation: str
    phone: str = ""
    assigned_classes: list[str]
    email: EmailStr


class StaffCreate(StaffBase):
    pass


class StaffUpdate(BaseModel):
    name: str | None = None
    designation: str | None = None
    phone: str | None = None
    assigned_classes: list[str] | None = None
    email: EmailStr | None = None
    reset_password: bool = False


class StaffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    designation: str
    phone: str
    email: str
    employee_id: str
    assigned_classes: list[str]
    force_password_change: bool = False
    created_at: datetime
    # Soft-delete workflow fields (see backend/app/models/record_status.py).
    status: str = "active"
    delete_requested_at: datetime | None = None
    delete_requested_by: str | None = None
    delete_reason: str | None = None
    deleted_at: datetime | None = None
    deleted_by: str | None = None


class StaffCreateResponse(StaffOut):
    initial_password: str


class StaffUpdateResponse(StaffOut):
    new_password: str | None = None


class StaffChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)
