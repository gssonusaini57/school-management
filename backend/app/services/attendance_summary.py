"""Per-student attendance totals over a date range (a term or a whole session).

Rule (an assumption the school can change here):
  - only non-holiday days count;
  - a working day is a day the student has an attendance record, so a student
    admitted mid-term is not marked absent for days before admission;
  - Present = 1, Half day = 0.5, Absent and Leave = 0.
The range is clipped to today so a term in progress isn't diluted by future days.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.attendance import Attendance, AttendanceRecord, AttendanceStatus

HALF_DAY_WEIGHT = 0.5


@dataclass
class AttendanceSummary:
    working_days: int = 0
    days_present: float = 0.0
    pct: float | None = None
    counts: dict[str, int] = field(default_factory=dict)


def summarize_counts(counts: dict[str, int]) -> AttendanceSummary:
    working = sum(counts.values())
    present = counts.get("P", 0) + HALF_DAY_WEIGHT * counts.get("H", 0)
    pct = round(present / working * 100, 1) if working else None
    return AttendanceSummary(working_days=working, days_present=present, pct=pct, counts=dict(counts))


def attendance_summary(
    db: Session,
    *,
    student_ids: list[int],
    start: date,
    end: date,
    today: date | None = None,
) -> dict[int, AttendanceSummary]:
    """{student_id: AttendanceSummary} for every requested student (zeros when none)."""
    out = {sid: AttendanceSummary() for sid in student_ids}
    end = min(end, today or date.today())
    if not student_ids or end < start:
        return out
    rows = db.execute(
        select(AttendanceRecord.student_id, AttendanceRecord.status, func.count())
        .join(Attendance, Attendance.id == AttendanceRecord.attendance_id)
        .where(
            AttendanceRecord.student_id.in_(student_ids),
            Attendance.date >= start,
            Attendance.date <= end,
            Attendance.is_holiday.is_(False),
        )
        .group_by(AttendanceRecord.student_id, AttendanceRecord.status)
    ).all()
    counts: dict[int, dict[str, int]] = {sid: {} for sid in student_ids}
    for sid, status, n in rows:
        key = status.value if isinstance(status, AttendanceStatus) else str(status)
        counts[sid][key] = counts[sid].get(key, 0) + int(n)
    return {sid: summarize_counts(c) for sid, c in counts.items()}
