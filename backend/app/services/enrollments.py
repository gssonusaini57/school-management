"""Optional subjects and the students who take them (migration 0020).

Most subjects are taken by the whole class. A subject marked `is_optional`
(11th/12th Mathematics as an additional subject) is taken only by the students
in `subject_enrollments`; everyone else has nothing for it: no marks, no result
and nothing on their report card. The results engine gets the enrolment as
data (`optional_takers`), so it stays free of database access.
"""
from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.class_subject import ClassSubject
from ..models.record_status import RecordStatus
from ..models.student import Student
from ..models.subject_enrollment import SubjectEnrollment
from .roster import roll_sort_key


def roster_enrollments(db: Session, subject_ids: Iterable[int]) -> dict[int, list[int]]:
    """class_subject_id -> sorted ids of the students who take it, limited to
    students still in that subject's class and not archived. A row left behind
    by a student who moved class or was archived is not listed, and the next
    PUT of the subject's enrolments drops it."""
    ids = list(dict.fromkeys(subject_ids))
    out: dict[int, list[int]] = {i: [] for i in ids}
    if not ids:
        return out
    rows = db.execute(
        select(SubjectEnrollment.class_subject_id, SubjectEnrollment.student_id)
        .join(ClassSubject, ClassSubject.id == SubjectEnrollment.class_subject_id)
        .join(Student, Student.id == SubjectEnrollment.student_id)
        .where(
            SubjectEnrollment.class_subject_id.in_(ids),
            Student.class_name == ClassSubject.class_name,
            Student.status != RecordStatus.deleted,
        )
    ).all()
    for subject_id, student_id in rows:
        out[subject_id].append(student_id)
    for v in out.values():
        v.sort()
    return out


def optional_takers(db: Session, class_name: str) -> dict[int, set[int]]:
    """{class_subject_id: ids of the students who take it} for every optional
    subject of a class (empty set when nobody does yet). This is the results
    engine's `enrolled` input: one query per class."""
    rows = db.execute(
        select(ClassSubject.id, SubjectEnrollment.student_id)
        .outerjoin(SubjectEnrollment, SubjectEnrollment.class_subject_id == ClassSubject.id)
        .where(ClassSubject.class_name == class_name, ClassSubject.is_optional.is_(True))
    ).all()
    out: dict[int, set[int]] = {}
    for subject_id, student_id in rows:
        takers = out.setdefault(subject_id, set())
        if student_id is not None:
            takers.add(student_id)
    return out


def subject_takers(db: Session, class_name: str, subject_name: str) -> set[int] | None:
    """Who takes a subject: None when it isn't optional (the whole class takes
    it, or it isn't in Class Subjects), else the enrolled student ids."""
    row = db.execute(
        select(ClassSubject.id, ClassSubject.is_optional)
        .where(ClassSubject.class_name == class_name, ClassSubject.subject_name == subject_name)
    ).first()
    if row is None or not row.is_optional:
        return None
    return set(db.scalars(
        select(SubjectEnrollment.student_id).where(SubjectEnrollment.class_subject_id == row.id)
    ))


def name_list(names: list[str], limit: int = 8) -> str:
    """'A', 'A and B', 'A, B and C'; past `limit` names, 'A, B, … and 4 others'."""
    if len(names) > limit:
        rest = len(names) - limit
        names = names[:limit] + [f"{rest} other{'s' if rest != 1 else ''}"]
    if len(names) <= 1:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"


def student_names(db: Session, student_ids: Iterable[int]) -> list[str]:
    """Names for student ids in roll order; an unknown id reads 'student #<id>'."""
    ids = set(student_ids)
    if not ids:
        return []
    rows = db.execute(
        select(Student.id, Student.name, Student.roll_no).where(Student.id.in_(ids))
    ).all()
    names = [r.name for r in sorted(rows, key=lambda r: roll_sort_key(r.roll_no, r.name))]
    return names + [f"student #{i}" for i in sorted(ids - {r.id for r in rows})]


def not_taken_message(names: list[str], subject: str) -> str:
    """Why marks for students who don't take an optional subject are refused."""
    verb = "doesn't" if len(names) == 1 else "don't"
    return (f"{name_list(names)} {verb} take {subject} (an optional subject). "
            "Ask the super-admin to tick them on Class Subjects.")
