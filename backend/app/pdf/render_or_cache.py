"""Cache-aware render: lookup → render-on-miss → store → return PdfCache row.

Public API:
  result = render_or_cache(db, kind, template, student_id, force=False, actor="")

`result` shape mirrors what the API returns to the frontend:
  {"student_id": int, "status": "cached"|"rendered"|"error", "pdf_id": int|None, "error": str|None}

Report cards pull their marks from the component-based `marks` table and roll
them up via app.services.results. Because a marks (or per-student-data) change
does NOT bump template.version, the cache also keys on a `source_hash` of those
inputs so an edit auto-invalidates the cached PDF.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from pydantic import ValidationError

from ..models.pdf_template import PdfTemplate, PdfStudentData, PdfCache, TemplateKind
from ..models.student import Student
from ..models.marks import Marks
from ..models.class_subject import ClassSubject
from ..services.results import scope_from_term
from .render import render_pdf
from .builder import build_report_card_payload, build_pseb_admit_payload

log = logging.getLogger(__name__)


def _term_key(term: str | None) -> str:
    return term or ""


def _load_student_data(
    db: Session, kind: TemplateKind, student_id: int, session: str, term: str | None
) -> dict[str, Any] | None:
    row = db.scalar(
        select(PdfStudentData).where(
            PdfStudentData.kind == kind,
            PdfStudentData.student_id == student_id,
            PdfStudentData.session == session,
            PdfStudentData.term_key == _term_key(term),
        )
    )
    return row.data if row else None


def _report_card_source_hash(marks_rows: list[Any], student_data: dict[str, Any] | None) -> str:
    """Content hash of everything a report card is rendered from (marks +
    per-student data). Changes when any of them changes → cache invalidates."""
    marks_parts = sorted(
        f"{m.subject}|{m.exam_type}|{m.marks}|{m.max_marks}" for m in marks_rows
    )
    sd_json = json.dumps(student_data or {}, sort_keys=True, default=str)
    raw = "MARKS\n" + "\n".join(marks_parts) + "\nSD\n" + sd_json
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _cache_lookup(
    db: Session, *, kind: TemplateKind, student_id: int, template_id: int,
    version: int, source_hash: str | None,
) -> PdfCache | None:
    stmt = select(PdfCache).where(
        PdfCache.kind == kind,
        PdfCache.student_id == student_id,
        PdfCache.template_id == template_id,
        PdfCache.template_version == version,
    )
    if source_hash is None:
        stmt = stmt.where(PdfCache.source_hash.is_(None))
    else:
        stmt = stmt.where(PdfCache.source_hash == source_hash)
    return db.scalar(stmt)


def render_or_cache(
    db: Session,
    *,
    template: PdfTemplate,
    student_id: int,
    force: bool = False,
    actor: str = "",
) -> dict[str, Any]:
    """Look up cache → render fresh on miss → return result dict."""
    student = db.get(Student, student_id)
    if not student:
        return {"student_id": student_id, "status": "error", "pdf_id": None,
                "error": f"student {student_id} not found"}
    if student.class_name != template.class_name:
        return {"student_id": student_id, "status": "error", "pdf_id": None,
                "error": f"student is in class {student.class_name}, not {template.class_name}"}

    # Gather render inputs once — these also feed the marks-aware cache hash.
    student_data = _load_student_data(
        db, template.kind, student.id, template.session, template.term
    )
    marks_rows: list[Any] = []
    class_subjects: list[Any] = []
    scope = "annual"
    source_hash: str | None = None
    if template.kind == TemplateKind.report_card:
        marks_rows = list(db.scalars(
            select(Marks).where(
                Marks.student_id == student.id,
                Marks.class_name == template.class_name,
                Marks.session == template.session,
            )
        ))
        class_subjects = list(db.scalars(
            select(ClassSubject)
            .where(ClassSubject.class_name == template.class_name)
            .options(selectinload(ClassSubject.components))
        ))
        scope = scope_from_term(template.term)
        source_hash = _report_card_source_hash(marks_rows, student_data)

    # 1) cache lookup (only if not force)
    if not force:
        hit = _cache_lookup(
            db, kind=template.kind, student_id=student_id, template_id=template.id,
            version=template.version, source_hash=source_hash,
        )
        if hit:
            return {"student_id": student_id, "status": "cached", "pdf_id": hit.id, "error": None}

    # 2) build + validate payload
    try:
        if template.kind == TemplateKind.report_card:
            model = build_report_card_payload(
                template_data=template.data,
                student=student,
                student_data=student_data,
                session=template.session,
                term=template.term,
                scope=scope,
                class_subjects=class_subjects,
                marks_rows=marks_rows,
            )
        elif template.kind == TemplateKind.pseb_admit_card:
            # PSEB requires rollNo + regNo per-student; builder raises if missing.
            model = build_pseb_admit_payload(
                template_data=template.data,
                student=student,
                student_data=student_data or {},
                session=template.session,
            )
        else:
            raise ValueError(f"unsupported template kind: {template.kind!r}")
        payload = model.model_dump(by_alias=True, mode="json")
    except (ValidationError, ValueError) as e:
        log.warning("payload build failed", extra={"student_id": student_id, "err": str(e)})
        return {"student_id": student_id, "status": "error", "pdf_id": None, "error": str(e)}

    # 3) render
    try:
        pdf_bytes = render_pdf(template.kind.value, payload)
    except Exception as e:
        log.exception("weasyprint render failed", extra={"student_id": student_id})
        return {"student_id": student_id, "status": "error", "pdf_id": None, "error": str(e)}

    # 4) persist (replace any row at the unique key — happens when force=True
    # re-renders, when marks/source_hash change, or on a rare race).
    existing = db.scalar(
        select(PdfCache).where(
            PdfCache.kind == template.kind,
            PdfCache.student_id == student_id,
            PdfCache.template_id == template.id,
            PdfCache.template_version == template.version,
        )
    )
    if existing:
        existing.data = pdf_bytes
        existing.byte_size = len(pdf_bytes)
        existing.created_by = actor
        existing.source_hash = source_hash
        db.flush()
        cache_row = existing
    else:
        cache_row = PdfCache(
            kind=template.kind,
            student_id=student_id,
            template_id=template.id,
            template_version=template.version,
            source_hash=source_hash,
            mime_type="application/pdf",
            byte_size=len(pdf_bytes),
            data=pdf_bytes,
            created_by=actor,
        )
        db.add(cache_row)
        db.flush()
    db.commit()

    return {"student_id": student_id, "status": "rendered", "pdf_id": cache_row.id, "error": None}
