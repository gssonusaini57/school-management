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
