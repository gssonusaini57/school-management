from pydantic import BaseModel
from datetime import date


class AttendanceSave(BaseModel):
    class_name: str
    date: date
    records: dict[int, str]  # student_id -> 'P'|'A'|'L'


class AttendanceOut(BaseModel):
    class_name: str
    date: date
    records: dict[int, str]


class AttendanceSummary(BaseModel):
    date: date
    total: int
    present: int
    absent: int
    leave: int
    percent: float


class MarkedDatesOut(BaseModel):
    """Dates in a range that have an attendance record for a given class.
    Powers the mobile coverage calendar (marked vs missed)."""
    dates: list[date]
