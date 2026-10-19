"""Shared write path for marks batches.

Two callers write marks: the Marks Entry form (`POST /marks/batches`, one
batch at a time, sends the full on-screen set) and the CSV import
(`POST /marks/bulk-import`, many batches, often a partial sheet). Both go
through here so every mark row belongs to a `marks_batches` row and obeys the
draft → submitted lock. Callers check the lock and commit; this module only
stages changes on the session.
"""
from __future__ import annotations

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from ..constants import CLASSES, fold_name
from ..models.class_subject import ClassSubject, SubjectExamComponent
from ..models.marks import Marks
from ..models.marks_batch import MarksBatch, MarksBatchStatus, MarksEditRequest, MarksEditRequestStatus
from ..models.record_status import RecordStatus
from ..models.student import Student
from ..models.subject_enrollment import SubjectEnrollment
from .enrollments import roster_enrollments
from .roster import active_class_sizes


def component_max(db: Session, class_name: str, subject: str, component: str) -> int | None:
    """Max marks of an exam component in the class-subjects master; None if it doesn't exist."""
    return db.scalar(
        select(SubjectExamComponent.max_marks)
        .join(ClassSubject, ClassSubject.id == SubjectExamComponent.class_subject_id)
        .where(
            ClassSubject.class_name == class_name,
            ClassSubject.subject_name == subject,
            SubjectExamComponent.component_name == component,
        )
    )


def batch_status_map(db: Session, class_name: str, session: str) -> dict[tuple[str, str], str]:
    """(subject, component) -> "draft" | "submitted" for one class and session."""
    rows = db.execute(
        select(MarksBatch.subject, MarksBatch.exam_type, MarksBatch.status)
        .where(MarksBatch.class_name == class_name, MarksBatch.session == session)
    ).all()
    return {(r.subject, r.exam_type): getattr(r.status, "value", r.status) for r in rows}


def _fold(*names: str) -> tuple[str, ...]:
    return tuple(fold_name(n) for n in names)


def batch_summary(db: Session, session: str, class_names: list[str]) -> list[dict]:
    """Marks progress for a session: one row per exam component of every class
    subject in `class_names` (graded components, max 0, included), ordered by
    CLASSES, then subject order, then component order.

    `status` is the batch's ("draft" | "submitted"), or "none" when no marks are
    saved for that exam yet. `class_size` is the class's students who are not
    archived (for an optional subject, those of them who take it) and `entered`
    counts how many of those students have a mark, or a grade for a graded
    exam, so entered never exceeds class_size. Batches of exams no longer in
    Class Subjects (a deleted exam's marks are archived under another name) are
    not listed. A fixed handful of queries, whatever the number of classes.
    """
    rank = {c: i for i, c in enumerate(CLASSES)}
    ordered = sorted(dict.fromkeys(class_names), key=lambda c: (rank.get(c, len(CLASSES)), c))
    if not ordered:
        return []
    subjects = db.scalars(
        select(ClassSubject)
        .where(ClassSubject.class_name.in_(ordered))
        .options(selectinload(ClassSubject.components))
    ).all()
    pending = (
        select(MarksEditRequest.id)
        .where(MarksEditRequest.batch_id == MarksBatch.id,
               MarksEditRequest.status == MarksEditRequestStatus.pending)
        .exists()
    )
    batches = {
        _fold(b.class_name, b.subject, b.exam_type): b
        for b in db.execute(
            select(MarksBatch.id, MarksBatch.class_name, MarksBatch.subject, MarksBatch.exam_type,
                   MarksBatch.status, MarksBatch.updated_at, MarksBatch.revision,
                   pending.label("pending_edit_request"))
            .where(MarksBatch.session == session, MarksBatch.class_name.in_(ordered))
        ).all()
    }
    entered: dict[int, int] = {
        batch_id: int(n)
        for batch_id, n in db.execute(
            select(Marks.batch_id, func.count(Marks.id))
            .select_from(Marks)
            .join(MarksBatch, MarksBatch.id == Marks.batch_id)
            .join(Student, Student.id == Marks.student_id)
            .outerjoin(ClassSubject, and_(ClassSubject.class_name == MarksBatch.class_name,
                                          ClassSubject.subject_name == MarksBatch.subject))
            .outerjoin(SubjectEnrollment, and_(SubjectEnrollment.class_subject_id == ClassSubject.id,
                                               SubjectEnrollment.student_id == Marks.student_id))
            .where(
                MarksBatch.session == session,
                MarksBatch.class_name.in_(ordered),
                # Only the students class_size counts: still in the class, not
                # archived and, for an optional subject, taking it.
                Student.class_name == MarksBatch.class_name,
                Student.status != RecordStatus.deleted,
                or_(ClassSubject.id.is_(None), ClassSubject.is_optional.is_(False),
                    SubjectEnrollment.id.is_not(None)),
                # A graded exam's entry is its letter; any other row holds a mark.
                or_(MarksBatch.max_marks > 0, and_(Marks.grade.is_not(None), Marks.grade != "")),
            )
            .group_by(Marks.batch_id)
        ).all()
    }
    sizes = active_class_sizes(db, ordered)
    takers = roster_enrollments(db, [cs.id for cs in subjects if cs.is_optional])

    by_class: dict[str, list[ClassSubject]] = {c: [] for c in ordered}
    requested = {_fold(c): c for c in ordered}
    for cs in subjects:
        cls = requested.get(_fold(cs.class_name))
        if cls is not None:
            by_class[cls].append(cs)

    items: list[dict] = []
    for cls in ordered:
        for cs in sorted(by_class[cls], key=lambda x: (x.order_index, x.subject_name)):
            size = len(takers.get(cs.id, [])) if cs.is_optional else sizes.get(cls, 0)
            for comp in sorted(cs.components, key=lambda x: (x.order_index, x.component_name)):
                b = batches.get(_fold(cls, cs.subject_name, comp.component_name))
                items.append({
                    "class_name": cls,
                    "subject": cs.subject_name,
                    "exam_type": comp.component_name,
                    "term": comp.term,
                    "status": getattr(b.status, "value", b.status) if b else "none",
                    "entered": entered.get(b.id, 0) if b else 0,
                    "class_size": size,
                    "updated_at": b.updated_at if b else None,
                    "revision": (b.revision or 0) if b else 0,
                    "pending_edit_request": bool(b.pending_edit_request) if b else False,
                })
    return items


def find_batch(
    db: Session, class_name: str, subject: str, exam_type: str, session: str,
) -> MarksBatch | None:
    """The batch for the (class, subject, exam component, session) quadruple, if any."""
    return db.execute(
        select(MarksBatch).where(
            MarksBatch.class_name == class_name,
            MarksBatch.subject == subject,
            MarksBatch.exam_type == exam_type,
            MarksBatch.session == session,
        )
    ).scalar_one_or_none()


def bump_revision(batch: MarksBatch) -> None:
    """Record a change to the batch's marks or status, so a screen that loaded
    the earlier revision can't save over it (BatchSaveBody.base_revision)."""
    batch.revision = (batch.revision or 0) + 1


def upsert_batch_marks(
    db: Session,
    *,
    class_name: str,
    subject: str,
    exam_type: str,
    session: str,
    max_marks: int,
    marks_by_student: dict[int, int],
    actor: str,
    prune_missing: bool,
    batch: MarksBatch | None = None,
    grades_by_student: dict[int, str] | None = None,
    prune_only: set[int] | None = None,
) -> MarksBatch:
    """Create the draft batch if it doesn't exist, then upsert one Marks row per student.

    `prune_missing=True` deletes rows for students absent from
    `marks_by_student`, because the form always sends the complete on-screen
    set. The CSV import passes False so a partial sheet never wipes marks it
    doesn't mention. Rows are matched on (batch_id, student_id), which is
    UNIQUE, so re-saving never duplicates. `prune_only`, when given, limits
    pruning to those students: an optional subject's form lists only the
    students who take it, so other students' saved rows are left alone.

    Grading components (max 0) pass `grades_by_student` with a letter per
    student; their `marks` stay 0. Every call bumps the batch's revision.
    """
    if batch is None:
        batch = find_batch(db, class_name, subject, exam_type, session)
    if batch is None:
        batch = MarksBatch(
            class_name=class_name,
            subject=subject,
            exam_type=exam_type,
            session=session,
            max_marks=max_marks,
            status=MarksBatchStatus.draft,
            created_by=actor,
            revision=0,
        )
        db.add(batch)
        db.flush()  # need batch.id for the FK below

    # Keep the batch in step with the master if super-admin changed max marks.
    batch.max_marks = max_marks
    bump_revision(batch)

    existing = {
        m.student_id: m
        for m in db.execute(select(Marks).where(Marks.batch_id == batch.id)).scalars().all()
    }
    if prune_missing:
        for sid, m in existing.items():
            if sid not in marks_by_student and (prune_only is None or sid in prune_only):
                db.delete(m)

    for sid, value in marks_by_student.items():
        grade = grades_by_student.get(sid) if grades_by_student is not None else None
        m = existing.get(sid)
        if m is None:
            db.add(Marks(
                student_id=sid,
                batch_id=batch.id,
                class_name=batch.class_name,
                exam_type=batch.exam_type,
                subject=batch.subject,
                marks=value,
                grade=grade,
                max_marks=batch.max_marks,
                session=batch.session,
                saved_by=actor,
            ))
        else:
            m.marks = value
            m.grade = grade
            m.max_marks = batch.max_marks
            m.saved_by = actor
    return batch


# ── Keeping marks attached when the class-subjects master changes ─────────
# Marks reference their subject and exam component by name, so a rename in the
# master must rename the marks and batches in the same transaction. Each one
# bumps the batches' revision, so a screen loaded before it can't save.

def rename_subject_marks(db: Session, class_name: str, old: str, new: str) -> None:
    db.execute(update(Marks).where(Marks.class_name == class_name, Marks.subject == old).values(subject=new))
    db.execute(update(MarksBatch).where(MarksBatch.class_name == class_name, MarksBatch.subject == old)
               .values(subject=new, revision=MarksBatch.revision + 1))


def rename_component_marks(db: Session, class_name: str, subject: str, old: str, new: str) -> None:
    db.execute(update(Marks).where(Marks.class_name == class_name, Marks.subject == subject,
                                   Marks.exam_type == old).values(exam_type=new))
    db.execute(update(MarksBatch).where(MarksBatch.class_name == class_name, MarksBatch.subject == subject,
                                        MarksBatch.exam_type == old)
               .values(exam_type=new, revision=MarksBatch.revision + 1))


def component_mark_stats(db: Session, class_name: str, subject: str, component: str) -> tuple[int, int | None]:
    """(number of mark rows, highest mark) recorded against an exam component."""
    count, top = db.execute(
        select(func.count(Marks.id), func.max(Marks.marks))
        .where(Marks.class_name == class_name, Marks.subject == subject, Marks.exam_type == component)
    ).one()
    return int(count or 0), (int(top) if top is not None else None)


def sync_component_max(db: Session, class_name: str, subject: str, component: str, new_max: int) -> None:
    db.execute(update(Marks).where(Marks.class_name == class_name, Marks.subject == subject,
                                   Marks.exam_type == component).values(max_marks=new_max))
    db.execute(update(MarksBatch).where(MarksBatch.class_name == class_name, MarksBatch.subject == subject,
                                        MarksBatch.exam_type == component)
               .values(max_marks=new_max, revision=MarksBatch.revision + 1))
