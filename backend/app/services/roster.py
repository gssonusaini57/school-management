"""Class rosters in the order teachers expect."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.record_status import RecordStatus
from ..models.student import Student


def roll_sort_key(roll_no: str | None, name: str) -> tuple:
    """Natural roll order: 1, 2, 10 (not 1, 10, 2); non-numeric after; blank last."""
    r = (roll_no or "").strip()
    if not r:
        return (2, 0, "", (name or "").lower())
    if r.isdigit():
        return (0, int(r), "", (name or "").lower())
    return (1, 0, r.lower(), (name or "").lower())


def active_roster(db: Session, class_name: str) -> list[Student]:
    """Students of a class who are not archived, in roll order."""
    rows = db.scalars(
        select(Student).where(Student.class_name == class_name, Student.status != RecordStatus.deleted)
    ).all()
    return sorted(rows, key=lambda s: roll_sort_key(s.roll_no, s.name))
