from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from decimal import Decimal


class FeeCreate(BaseModel):
    student_id: int
    class_name: str
    month: str
    year: str
    amount: Decimal
    date: date
    receipt_no: str | None = None


class FeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    student_name: str
    class_name: str
    month: str
    year: str
    amount: Decimal
    date: date
    receipt_no: str
    created_at: datetime
