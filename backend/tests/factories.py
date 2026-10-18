"""Tiny row builders for tests. Each returns the flushed ORM object."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.academic_session import AcademicSession
from app.models.attendance import Attendance, AttendanceRecord, AttendanceStatus
from app.models.class_subject import ClassSubject, SubjectCategory, SubjectExamComponent
from app.models.marks import Marks
from app.models.marks_batch import MarksBatch, MarksBatchStatus
from app.models.pdf_template import PdfCache, PdfTemplate, TemplateKind
from app.models.record_status import RecordStatus
from app.models.student import Student
from app.services.sessions import default_dates


def academic_session(db: Session, name: str = "2026-27", is_current: bool = True, **dates) -> AcademicSession:
    row = AcademicSession(session=name, is_current=is_current, updated_by="t", **{**default_dates(name), **dates})
    db.add(row)
    db.flush()
    return row


def student(db: Session, name: str = "Asha Kaur", class_name: str = "8th", roll_no: str | None = "1",
            status: RecordStatus = RecordStatus.active, **kw) -> Student:
    s = Student(
        name=name, father=kw.pop("father", "Father " + name), mother=kw.pop("mother", "Mother " + name),
        class_name=class_name, roll_no=roll_no, status=status, **kw,
    )
    db.add(s)
    db.flush()
    return s


def subject(db: Session, class_name: str, subject_name: str, components: list[tuple[str, int, int | None]],
            category: SubjectCategory = SubjectCategory.academic, order_index: int = 0,
            subject_name_pa: str | None = None) -> ClassSubject:
    """components: [(component_name, max_marks, term)]"""
    cs = ClassSubject(class_name=class_name, subject_name=subject_name, subject_name_pa=subject_name_pa,
                      category=category, order_index=order_index)
    db.add(cs)
    db.flush()
    for i, (cname, mx, term) in enumerate(components):
        db.add(SubjectExamComponent(class_subject_id=cs.id, component_name=cname, max_marks=mx,
                                    order_index=i, term=term))
    db.flush()
    db.refresh(cs)
    return cs


def batch(db: Session, class_name: str, subject_name: str, exam_type: str, session: str = "2026-27",
          max_marks: int = 35, status: MarksBatchStatus = MarksBatchStatus.draft,
          marks: dict[int, int] | None = None) -> MarksBatch:
    b = MarksBatch(class_name=class_name, subject=subject_name, exam_type=exam_type, session=session,
                   max_marks=max_marks, status=status, created_by="t")
    db.add(b)
    db.flush()
    for sid, v in (marks or {}).items():
        db.add(Marks(student_id=sid, batch_id=b.id, class_name=class_name, exam_type=exam_type,
                     subject=subject_name, marks=v, max_marks=max_marks, session=session, saved_by="t"))
    db.flush()
    return b


def attendance_day(db: Session, class_name: str, day: date, statuses: dict[int, str] | None = None,
                   is_holiday: bool = False) -> Attendance:
    a = Attendance(class_name=class_name, date=day, is_holiday=is_holiday, updated_by="t")
    db.add(a)
    db.flush()
    for sid, st in (statuses or {}).items():
        db.add(AttendanceRecord(attendance_id=a.id, student_id=sid, status=AttendanceStatus(st)))
    db.flush()
    return a


def report_card_template(db: Session, class_name: str = "8th", session: str = "2026-27",
                         term: str | None = "Term I", data: dict | None = None) -> PdfTemplate:
    t = PdfTemplate(kind=TemplateKind.report_card, class_name=class_name, session=session, term=term,
                    term_key=term or "", version=1, data=data or {}, created_by="t", updated_by="t")
    db.add(t)
    db.flush()
    return t


def cached_pdf(db: Session, template: PdfTemplate, student_id: int, payload: bytes = b"%PDF-1.4 test") -> PdfCache:
    c = PdfCache(kind=template.kind, student_id=student_id, template_id=template.id,
                 template_version=template.version, mime_type="application/pdf",
                 byte_size=len(payload), data=payload, created_by="t")
    db.add(c)
    db.flush()
    return c
