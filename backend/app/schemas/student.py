from pydantic import BaseModel, ConfigDict, Field
from datetime import date, datetime
from decimal import Decimal


class StudentBase(BaseModel):
    name: str
    father: str
    mother: str
    dob: date | None = None
    gender: str = ""
    village: str = ""
    phone: str = ""
    aadhar: str = ""
    alt_phone: str = "N/A"
    religion: str = "N/A"
    prev_school: str = "N/A"
    bank_name: str = "N/A"
    bank_acc: str = "N/A"
    bank_ifsc: str = "N/A"
    annual_fee: Decimal = Field(default=Decimal("0"))
    class_name: str
    admission_no: int | None = None
    roll_no: str | None = None


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    name: str | None = None
    father: str | None = None
    mother: str | None = None
    dob: date | None = None
    gender: str | None = None
    village: str | None = None
    phone: str | None = None
    aadhar: str | None = None
    alt_phone: str | None = None
    religion: str | None = None
    prev_school: str | None = None
    bank_name: str | None = None
    bank_acc: str | None = None
    bank_ifsc: str | None = None
    annual_fee: Decimal | None = None
    class_name: str | None = None
    admission_no: int | None = None
    roll_no: str | None = None


class StudentOut(StudentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    admission_id: str | None = None  # derived KIS/{year}/{admission_no:04d}
    created_at: datetime
    added_by: str
    updated_at: datetime
    updated_by: str
    has_photo: bool = False
    has_dob_cert: bool = False
    has_aadhar: bool = False
    # Soft-delete workflow fields (see backend/app/models/record_status.py).
    status: str = "active"
    delete_requested_at: datetime | None = None
    delete_requested_by: str | None = None
    delete_reason: str | None = None
    deleted_at: datetime | None = None
    deleted_by: str | None = None


class StudentPage(BaseModel):
    """Paginated envelope returned by GET /students."""
    items: list[StudentOut]
    total: int
    page: int
    page_size: int


class DeleteRequestBody(BaseModel):
    """Optional `{reason: "..."}` body accepted on DELETE /students/{id} and /staff/{id}."""
    reason: str | None = None
