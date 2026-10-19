"""Class rosters in the order teachers expect."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..constants import fold_name
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


def active_class_sizes(db: Session, class_names: list[str]) -> dict[str, int]:
    """{class: students not archived} for each requested class (0 when it has
    none), from one grouped query. Pending-delete students still count, as on
    the roster."""
    sizes = dict.fromkeys(class_names, 0)
    if not class_names:
        return sizes
    requested = {fold_name(c): c for c in class_names}
    rows = db.execute(
        select(Student.class_name, func.count(Student.id))
        .where(Student.class_name.in_(class_names), Student.status != RecordStatus.deleted)
        .group_by(Student.class_name)
    ).all()
    for name, n in rows:
        cls = requested.get(fold_name(name))
        if cls is not None:
            sizes[cls] += int(n)
    return sizes
