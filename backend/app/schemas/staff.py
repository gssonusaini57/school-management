from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime


class StaffBase(BaseModel):
    name: str
    designation: str
    phone: str = ""
    assigned_classes: list[str]
    email: EmailStr
    # Menu permission grants — see backend/app/permissions.py for valid keys.
    # Optional on create; falls back to DEFAULT_STAFF_MENUS server-side.
    allowed_menus: list[str] | None = None


class StaffCreate(StaffBase):
    pass


class StaffUpdate(BaseModel):
    name: str | None = None
    designation: str | None = None
    phone: str | None = None
    assigned_classes: list[str] | None = None
    email: EmailStr | None = None
    allowed_menus: list[str] | None = None
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
    allowed_menus: list[str] = Field(default_factory=list)
    force_password_change: bool = False
    # Admin-set temporary-password state (the hash itself is never exposed).
    has_temp_password: bool = False
    temp_password_set_at: datetime | None = None
    temp_password_set_by: str | None = None
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


class SetTempPasswordRequest(BaseModel):
    """Admin/super-admin sets a custom temporary password for a staff member."""
    password: str = Field(min_length=4, max_length=128)
