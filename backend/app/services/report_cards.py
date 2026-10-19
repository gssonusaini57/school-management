"""Report cards: gather a class's render inputs once, then build each card.

A card mixes per-student numbers (marks, attendance, remarks) with
class-relative ones (rank, class size), so the inputs are collected for the
whole class in one pass and every card in a bulk render reuses them.

Caching follows Gotcha #20 ("a cache key must cover every input"): instead of
hashing a hand-picked list of tables, the cache hash is taken over the final
payload the template receives (plus the template revision and the photo's
identity). Anything that changes what a card would print therefore changes
its hash, including a classmate's marks moving this student's rank.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models.academic_session import AcademicSession
from ..models.class_subject import ClassSubject
from ..models.document import DocumentKind, StudentDocument
from ..models.marks import Marks
from ..models.pdf_template import PdfStudentData, PdfTemplate, TemplateKind
from ..models.student import Student
from .attendance_summary import AttendanceSummary, attendance_summary
from .enrollments import optional_takers
from .marks_batches import batch_status_map
from .results import (
    CONDITIONAL_MAX_FAILS_DEFAULT, PASS_PCT_DEFAULT, RESULTS_ENGINE_VERSION,
    ClassResults, StudentResult, aggregate_class_results, scope_from_term,
)
from .roster import active_roster
from .sessions import get_session, scope_dates

# Bump when report-card.html.j2 or the payload shape changes, so cached cards re-render.
REPORT_CARD_TEMPLATE_REVISION = 4

SCOPE_LABELS = {"term1": "Term I", "term2": "Term II", "annual": "Annual"}


def term_key(term: str | None) -> str:
    """Unique-index-safe form of a template term (NULL becomes "")."""
    return term or ""


def template_scope(template: PdfTemplate) -> str | None:
    """The results scope a report-card template prints; None if it can't be told."""
    return template.scope or scope_from_term(template.term)


def template_settings(template: PdfTemplate) -> dict[str, Any]:
    """Class-level settings with defaults filled in (tolerates v1-shaped rows)."""
    from ..pdf.schemas import ReportCardTemplateData  # local: pdf.schemas is heavier
    return ReportCardTemplateData.model_validate(template.data or {}).model_dump()


@dataclass
class PhotoMeta:
    doc_id: int
    byte_size: int
    mime_type: str
    uploaded_at: datetime | None


@dataclass
class ClassRenderInputs:
    template: PdfTemplate
    scope: str
    include_drafts: bool
    settings: dict[str, Any]
    roster: list[Student]
    students: dict[int, Student]
    class_results: ClassResults
    results_by_student: dict[int, StudentResult]
    student_data: dict[int, dict]           # rows for this template's session + term
    houses: dict[int, str]                  # house from any term's row in the session
    attendance: dict[int, AttendanceSummary]
    session_row: AcademicSession | None
    photos: dict[int, PhotoMeta]
    warnings: list[str] = field(default_factory=list)


def gather_class_inputs(
    db: Session, template: PdfTemplate, *, include_drafts: bool | None = None,
) -> ClassRenderInputs:
    """Everything the class's report cards are built from, in one pass."""
    scope = template_scope(template)
    if scope is None:
        raise ValueError(f"template term {template.term!r} is not Term I, Term II or Annual; set the scope")
    settings = template_settings(template)
    drafts = settings["includeDrafts"] if include_drafts is None else include_drafts
    rule = settings.get("promotionRule") or {}

    roster = active_roster(db, template.class_name)
    ids = [s.id for s in roster]
    class_subjects = list(db.scalars(
        select(ClassSubject)
        .where(ClassSubject.class_name == template.class_name)
        .options(selectinload(ClassSubject.components))
    ))
    marks_rows = list(db.scalars(
        select(Marks).where(Marks.class_name == template.class_name, Marks.session == template.session)
    ))
    results = aggregate_class_results(
        class_name=template.class_name, session=template.session, scope=scope,
        class_subjects=class_subjects, marks_rows=marks_rows, student_ids=ids,
        batch_status_by_key=batch_status_map(db, template.class_name, template.session),
        include_drafts=drafts,
        pass_pct=float(rule.get("passPct", PASS_PCT_DEFAULT)),
        conditional_max_fails=int(rule.get("conditionalMaxFails", CONDITIONAL_MAX_FAILS_DEFAULT)),
        enrolled=optional_takers(db, template.class_name),
    )

    warnings = list(results.warnings)
    session_row = get_session(db, template.session)
    attendance: dict[int, AttendanceSummary] = {}
    if session_row is None:
        warnings.append(f"Session {template.session} is not configured, so attendance can't be computed.")
    elif ids:
        start, end = scope_dates(session_row, scope)
        attendance = attendance_summary(db, student_ids=ids, start=start, end=end)

    student_data: dict[int, dict] = {}
    houses: dict[int, str] = {}
    if ids:
        rows = db.scalars(
            select(PdfStudentData).where(
                PdfStudentData.kind == template.kind,
                PdfStudentData.session == template.session,
                PdfStudentData.student_id.in_(ids),
            )
        ).all()
        tk = term_key(template.term)
        for r in rows:
            if r.term_key == tk:
                student_data[r.student_id] = dict(r.data or {})
            house = (r.data or {}).get("house")
            if house and (r.term_key == tk or r.student_id not in houses):
                houses[r.student_id] = house

    photos: dict[int, PhotoMeta] = {}
    if ids and settings.get("showPhoto", True):
        for doc_id, sid, size, mime, uploaded in db.execute(
            select(StudentDocument.id, StudentDocument.student_id, StudentDocument.byte_size,
                   StudentDocument.mime_type, StudentDocument.uploaded_at)
            .where(StudentDocument.kind == DocumentKind.photo, StudentDocument.student_id.in_(ids))
        ).all():
            photos[sid] = PhotoMeta(doc_id, int(size or 0), mime, uploaded)

    return ClassRenderInputs(
        template=template, scope=scope, include_drafts=drafts, settings=settings,
        roster=roster, students={s.id: s for s in roster},
        class_results=results, results_by_student={r.student_id: r for r in results.students},
        student_data=student_data, houses=houses, attendance=attendance,
        session_row=session_row, photos=photos, warnings=warnings,
    )


def payload_hash(payload: dict[str, Any], photo: PhotoMeta | None = None) -> str:
    """Hash of everything a card prints. `generatedOn` is excluded (it changes daily)."""
    body = {k: v for k, v in payload.items() if k != "generatedOn"}
    photo_id = f"{photo.doc_id}:{photo.byte_size}:{photo.uploaded_at}" if photo else ""
    raw = (
        f"report-card rev{REPORT_CARD_TEMPLATE_REVISION} engine{RESULTS_ENGINE_VERSION}\n"
        f"photo {photo_id}\n" + json.dumps(body, sort_keys=True, default=str)
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


PHOTO_MAX_PX = 360          # the card's photo box is 74 x 92 px; this stays sharp in print
SAFE_PHOTO_FORMATS = ("JPEG", "PNG", "WEBP")


def safe_photo_jpeg(data: bytes, max_px: int = PHOTO_MAX_PX) -> bytes | None:
    """Decode an uploaded photo as a real raster image and re-encode it as a small JPEG.

    Anything that isn't a JPEG/PNG/WebP picture (an SVG, an HTML file renamed
    to .jpg, a corrupt upload) returns None, so only pixels we produced
    ourselves ever reach the PDF renderer. Shrinking also keeps cards small
    when phones upload multi-megabyte camera photos.
    """
    try:
        from PIL import Image, ImageOps  # Pillow ships with WeasyPrint
        with Image.open(io.BytesIO(data)) as im:
            if im.format not in SAFE_PHOTO_FORMATS:
                return None
            im = ImageOps.exif_transpose(im)
            im.thumbnail((max_px, max_px))
            out = io.BytesIO()
            im.convert("RGB").save(out, "JPEG", quality=85, optimize=True)
            return out.getvalue()
    except Exception:
        return None


def photo_data_uri(db: Session, doc_id: int) -> str | None:
    doc = db.get(StudentDocument, doc_id)
    if not doc or not doc.data:
        return None
    jpeg = safe_photo_jpeg(doc.data)
    if jpeg is None:
        return None
    return f"data:image/jpeg;base64,{base64.b64encode(jpeg).decode('ascii')}"


def resolve_template(
    db: Session, *, class_name: str, session: str, scope: str,
    kind: TemplateKind = TemplateKind.report_card,
) -> PdfTemplate | None:
    """The report-card template for a class, session and scope, if one exists."""
    rows = db.scalars(
        select(PdfTemplate).where(
            PdfTemplate.kind == kind,
            PdfTemplate.class_name == class_name,
            PdfTemplate.session == session,
        ).order_by(PdfTemplate.updated_at.desc())
    ).all()
    for t in rows:
        if template_scope(t) == scope:
            return t
    return None
