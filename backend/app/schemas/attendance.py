from pydantic import BaseModel, ConfigDict, Field
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


class ClassAttendanceRow(BaseModel):
    """One class over a date range (GET /attendance/class-summary). Counts cover
    non-holiday days only; a class nobody marked has zeros and percent None."""
    class_name: str
    class_size: int        # students not archived
    marked_days: int       # non-holiday days with attendance saved
    holiday_days: int      # days marked as a holiday
    present: int
    absent: int
    leave: int
    half_day: int
    records: int           # present + absent + leave + half_day
    percent: float | None  # (present + 0.5 * half_day) / records * 100, 1 dp; None with no records


class ClassAttendanceTotals(BaseModel):
    class_size: int
    present: int
    absent: int
    leave: int
    half_day: int
    records: int
    percent: float | None
    classes_marked: int    # classes with at least one marked day in the range
    classes_total: int     # classes in the caller's scope


class ClassAttendanceSummaryOut(BaseModel):
    # "from" is a Python keyword: the field is from_, sent and read as "from".
    model_config = ConfigDict(populate_by_name=True)

    from_: date = Field(alias="from")
    to: date               # never later than today
    classes: list[ClassAttendanceRow]
    totals: ClassAttendanceTotals
