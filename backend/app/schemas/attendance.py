from pydantic import BaseModel
from datetime import date


class AttendanceSave(BaseModel):
    class_name: str
    date: date
    records: dict[int, str] = {}  # student_id -> 'P'|'A'|'L'|'H' (empty when is_holiday)
    is_holiday: bool = False       # day-level holiday: stored with no records


class AttendanceOut(BaseModel):
    class_name: str
    date: date
    records: dict[int, str]
    is_holiday: bool = False


class AttendanceSummary(BaseModel):
    date: date
    total: int
    present: int
    absent: int
    leave: int
    half_day: int = 0
    percent: float


class MarkedDatesOut(BaseModel):
    """For a class in a date range: dates with student attendance records, and
    (separately) dates flagged as holidays. Powers the mobile coverage calendar
    (marked vs missed vs holiday)."""
    dates: list[date]
    holidays: list[date] = []
