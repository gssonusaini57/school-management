"""Cache-aware rendering for templated PDFs (report cards, PSEB admit cards).

Public API:
  render_students(db, template=..., student_ids=[...], force=False, actor="",
                  include_drafts=None, on_result=None) -> list[result]
  render_or_cache(db, template=..., student_id=..., force=False, actor="") -> result

Each result mirrors what the API returns:
  {"student_id", "status": "cached"|"rendered"|"error", "pdf_id", "error", "warnings"}

The cache row is keyed on (kind, student, template, template version) and
stores a `source_hash` of the exact payload the template received, so any
change to what a card would print (marks, a classmate's marks moving the
rank, attendance, remarks, names, settings, template revision) re-renders it.
Report-card inputs are gathered once per class, not once per student.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Callable

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.pdf_template import PdfCache, PdfStudentData, PdfTemplate, TemplateKind
from ..models.record_status import RecordStatus
from ..models.student import Student
from ..services.report_cards import (
    ClassRenderInputs, gather_class_inputs, payload_hash, photo_data_uri, term_key,
)
from .builder import build_pseb_admit_payload, build_report_card_payload
from .render import render_pdf

log = logging.getLogger(__name__)

__all__ = ["render_students", "render_or_cache", "term_key", "cache_lookup"]


def _result(student_id: int, status: str, pdf_id: int | None = None, error: str | None = None,
            warnings: list[str] | None = None) -> dict[str, Any]:
    return {"student_id": student_id, "status": status, "pdf_id": pdf_id, "error": error,
            "warnings": warnings or []}


def cache_lookup(
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


def _store(db: Session, template: PdfTemplate, student_id: int, pdf_bytes: bytes,
           source_hash: str, actor: str) -> PdfCache:
    """Replace the row at the unique key (one PDF per student per template version).

    Two renders of the same student can race (a background run and a teacher's
    single-card render): if the other one inserts first, the INSERT here hits
    the unique key, so roll back and write over its row instead.
    """
    for attempt in (1, 2):
        row = db.scalar(
            select(PdfCache).where(
                PdfCache.kind == template.kind,
                PdfCache.student_id == student_id,
                PdfCache.template_id == template.id,
                PdfCache.template_version == template.version,
            )
        )
        if row is None:
            row = PdfCache(
                kind=template.kind, student_id=student_id, template_id=template.id,
                template_version=template.version, mime_type="application/pdf",
            )
            db.add(row)
        row.data = pdf_bytes
        row.byte_size = len(pdf_bytes)
        row.source_hash = source_hash
        row.created_by = actor
        try:
            db.flush()
            return row
        except IntegrityError:
            db.rollback()
            if attempt == 2:
                raise
    raise RuntimeError("unreachable")


# ── report cards ─────────────────────────────────────────────────────────
def report_card_payload(inputs: ClassRenderInputs, student_id: int) -> tuple[dict[str, Any], str]:
    """(payload without photo data, its cache hash). Raises ValueError when no card can be built."""
    model = build_report_card_payload(inputs, student_id)
    payload = model.model_dump(by_alias=True, mode="json")
    return payload, payload_hash(payload, inputs.photos.get(student_id))


def _render_report_card(db: Session, inputs: ClassRenderInputs, student_id: int, *,
                        force: bool, actor: str) -> dict[str, Any]:
    template = inputs.template
    try:
        payload, source_hash = report_card_payload(inputs, student_id)
    except (ValidationError, ValueError) as e:
        return _result(student_id, "error", error=str(e))
    warnings = []
    if payload["summary"]["incomplete"] or payload["summary"]["hasDrafts"]:
        warnings.append("provisional: some marks are missing or still drafts")

    if not force:
        hit = cache_lookup(db, kind=template.kind, student_id=student_id, template_id=template.id,
                           version=template.version, source_hash=source_hash)
        if hit:
            return _result(student_id, "cached", hit.id, warnings=warnings)

    photo = inputs.photos.get(student_id)
    if photo and inputs.settings.get("showPhoto", True):
        payload["student"]["photoUrl"] = photo_data_uri(db, photo.doc_id)
    try:
        pdf_bytes = render_pdf(template.kind.value, payload)
    except Exception as e:  # WeasyPrint/system-font failures surface per student
        log.exception("report card render failed", extra={"student_id": student_id})
        return _result(student_id, "error", error=str(e))
    row = _store(db, template, student_id, pdf_bytes, source_hash, actor)
    db.commit()
    return _result(student_id, "rendered", row.id, warnings=warnings)


# ── PSEB admit cards ─────────────────────────────────────────────────────
def pseb_payload(db: Session, template: PdfTemplate, student: Student) -> tuple[dict[str, Any], str]:
    """(admit-card payload, its cache hash). Raises ValueError when the card can't be built."""
    row = db.scalar(select(PdfStudentData).where(
        PdfStudentData.kind == template.kind, PdfStudentData.student_id == student.id,
        PdfStudentData.session == template.session, PdfStudentData.term_key == term_key(template.term),
    ))
    try:
        model = build_pseb_admit_payload(template_data=template.data, student=student,
                                         student_data=(row.data if row else None) or {},
                                         session=template.session)
    except (ValidationError, KeyError) as e:
        raise ValueError(str(e)) from e
    payload = model.model_dump(by_alias=True, mode="json")
    stable = {k: v for k, v in payload.items() if k != "printedOn"}   # printedOn changes daily
    source_hash = hashlib.sha1(("pseb\n" + json.dumps(stable, sort_keys=True, default=str)).encode()).hexdigest()
    return payload, source_hash


def _render_pseb(db: Session, template: PdfTemplate, student_id: int, *, force: bool, actor: str) -> dict[str, Any]:
    student = db.get(Student, student_id)
    if not student or student.status == RecordStatus.deleted:
        return _result(student_id, "error", error=f"student {student_id} not found or archived")
    if student.class_name != template.class_name:
        return _result(student_id, "error",
                       error=f"student is in class {student.class_name}, not {template.class_name}")
    try:
        payload, source_hash = pseb_payload(db, template, student)
    except ValueError as e:
        return _result(student_id, "error", error=str(e))
    if not force:
        hit = cache_lookup(db, kind=template.kind, student_id=student_id, template_id=template.id,
                           version=template.version, source_hash=source_hash)
        if hit:
            return _result(student_id, "cached", hit.id)
    try:
        pdf_bytes = render_pdf(template.kind.value, payload)
    except Exception as e:
        log.exception("pseb render failed", extra={"student_id": student_id})
        return _result(student_id, "error", error=str(e))
    cache_row = _store(db, template, student_id, pdf_bytes, source_hash, actor)
    db.commit()
    return _result(student_id, "rendered", cache_row.id)


# ── public API ───────────────────────────────────────────────────────────
def render_students(
    db: Session,
    *,
    template: PdfTemplate,
    student_ids: list[int],
    force: bool = False,
    actor: str = "",
    include_drafts: bool | None = None,
    on_result: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    """Render (or reuse) one PDF per student. Each student is committed on its
    own, so a failure or an interrupted bulk run keeps what already finished."""
    results: list[dict[str, Any]] = []
    inputs: ClassRenderInputs | None = None
    if template.kind == TemplateKind.report_card:
        try:
            inputs = gather_class_inputs(db, template, include_drafts=include_drafts)
        except ValueError as e:
            out = [_result(sid, "error", error=str(e)) for sid in student_ids]
            for r in out:
                if on_result:
                    on_result(r)
            return out
    for sid in student_ids:
        try:
            if inputs is not None:
                r = _render_report_card(db, inputs, sid, force=force, actor=actor)
            else:
                r = _render_pseb(db, template, sid, force=force, actor=actor)
        except Exception as e:  # one student's failure must not abort the request or the run
            log.exception("card render failed", extra={"student_id": sid, "template_id": template.id})
            db.rollback()
            r = _result(sid, "error", error=f"unexpected error: {str(e)[:300]}")
        results.append(r)
        if on_result:
            on_result(r)
    return results


def render_or_cache(
    db: Session, *, template: PdfTemplate, student_id: int, force: bool = False, actor: str = "",
) -> dict[str, Any]:
    """Single-student convenience wrapper over render_students."""
    return render_students(db, template=template, student_ids=[student_id], force=force, actor=actor)[0]
