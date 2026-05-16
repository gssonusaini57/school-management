"""Cache-aware render: lookup → render-on-miss → store → return PdfCache row.

Public API:
  result = render_or_cache(db, kind, template, student_id, force=False, actor="")

`result` shape mirrors what the API returns to the frontend:
  {"student_id": int, "status": "cached"|"rendered"|"error", "pdf_id": int|None, "error": str|None}
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import ValidationError

from ..models.pdf_template import PdfTemplate, PdfStudentData, PdfCache, TemplateKind
from ..models.student import Student
from ..models.marks import Marks
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


def _build_full_payload(
    db: Session,
    template: PdfTemplate,
    student: Student,
) -> dict[str, Any]:
    """Build + validate the full render payload as a JSON-ready dict."""
    student_data = _load_student_data(
        db, template.kind, student.id, template.session, template.term
    )

    if template.kind == TemplateKind.report_card:
        marks_rows = list(db.scalars(
            select(Marks).where(
                Marks.student_id == student.id,
                Marks.class_name == template.class_name,
                Marks.exam_type == (template.term or template.session),
            )
        ))
        model = build_report_card_payload(
            template_data=template.data,
            student=student,
            student_data=student_data,
            session=template.session,
            term=template.term,
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

    return model.model_dump(by_alias=True, mode="json")


def render_or_cache(
    db: Session,
    *,
    template: PdfTemplate,
    student_id: int,
    force: bool = False,
    actor: str = "",
) -> dict[str, Any]:
    """Look up cache → render fresh on miss → return result dict."""
    # 1) cache lookup (only if not force)
    if not force:
        hit = db.scalar(
            select(PdfCache).where(
                PdfCache.kind == template.kind,
                PdfCache.student_id == student_id,
                PdfCache.template_id == template.id,
                PdfCache.template_version == template.version,
            )
        )
        if hit:
            return {"student_id": student_id, "status": "cached", "pdf_id": hit.id, "error": None}

    # 2) render fresh
    student = db.get(Student, student_id)
    if not student:
        return {"student_id": student_id, "status": "error", "pdf_id": None,
                "error": f"student {student_id} not found"}
    if student.class_name != template.class_name:
        return {"student_id": student_id, "status": "error", "pdf_id": None,
                "error": f"student is in class {student.class_name}, not {template.class_name}"}

    try:
        payload = _build_full_payload(db, template, student)
    except (ValidationError, ValueError) as e:
        log.warning("payload build failed", extra={"student_id": student_id, "err": str(e)})
        return {"student_id": student_id, "status": "error", "pdf_id": None, "error": str(e)}

    try:
        pdf_bytes = render_pdf(template.kind.value, payload)
    except Exception as e:
        log.exception("weasyprint render failed", extra={"student_id": student_id})
        return {"student_id": student_id, "status": "error", "pdf_id": None, "error": str(e)}

    # 3) persist (replace any stale row at the same unique key — happens when
    # `force=True` re-renders an existing version, or on a rare race).
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
        db.flush()
        cache_row = existing
    else:
        cache_row = PdfCache(
            kind=template.kind,
            student_id=student_id,
            template_id=template.id,
            template_version=template.version,
            mime_type="application/pdf",
            byte_size=len(pdf_bytes),
            data=pdf_bytes,
            created_by=actor,
        )
        db.add(cache_row)
        db.flush()
    db.commit()

    return {"student_id": student_id, "status": "rendered", "pdf_id": cache_row.id, "error": None}
