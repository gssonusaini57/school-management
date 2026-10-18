"""Shared write path for marks batches.

Two callers write marks: the Marks Entry form (`POST /marks/batches`, one
batch at a time, sends the full on-screen set) and the CSV import
(`POST /marks/bulk-import`, many batches, often a partial sheet). Both go
through here so every mark row belongs to a `marks_batches` row and obeys the
draft → submitted lock. Callers check the lock and commit; this module only
stages changes on the session.
"""
from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..models.class_subject import ClassSubject, SubjectExamComponent
from ..models.marks import Marks
from ..models.marks_batch import MarksBatch, MarksBatchStatus


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
) -> MarksBatch:
    """Create the draft batch if it doesn't exist, then upsert one Marks row per student.

    `prune_missing=True` deletes rows for students absent from
    `marks_by_student`, because the form always sends the complete on-screen
    set. The CSV import passes False so a partial sheet never wipes marks it
    doesn't mention. Rows are matched on (batch_id, student_id), which is
    UNIQUE, so re-saving never duplicates.

    Grading components (max 0) pass `grades_by_student` with a letter per
    student; their `marks` stay 0.
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
        )
        db.add(batch)
        db.flush()  # need batch.id for the FK below

    # Keep the batch in step with the master if super-admin changed max marks.
    batch.max_marks = max_marks

    existing = {
        m.student_id: m
        for m in db.execute(select(Marks).where(Marks.batch_id == batch.id)).scalars().all()
    }
    if prune_missing:
        for sid, m in existing.items():
            if sid not in marks_by_student:
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
# master must rename the marks and batches in the same transaction.

def rename_subject_marks(db: Session, class_name: str, old: str, new: str) -> None:
    db.execute(update(Marks).where(Marks.class_name == class_name, Marks.subject == old).values(subject=new))
    db.execute(update(MarksBatch).where(MarksBatch.class_name == class_name, MarksBatch.subject == old)
               .values(subject=new))


def rename_component_marks(db: Session, class_name: str, subject: str, old: str, new: str) -> None:
    db.execute(update(Marks).where(Marks.class_name == class_name, Marks.subject == subject,
                                   Marks.exam_type == old).values(exam_type=new))
    db.execute(update(MarksBatch).where(MarksBatch.class_name == class_name, MarksBatch.subject == subject,
                                        MarksBatch.exam_type == old).values(exam_type=new))


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
                                        MarksBatch.exam_type == component).values(max_marks=new_max))
