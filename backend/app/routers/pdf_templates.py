"""Class-templated PDF generation (report cards, PSEB admit cards) with a server-side cache.

Flow:
  1. Admin creates a template per (kind, class, session, term). Report cards
     also pick a results scope (term1 | term2 | annual) and a layout
     (summary | components). `bulk-create` makes one per class in one go.
  2. Per-student data: class teachers fill remarks and house; admins may also
     override computed values (rank, attendance, promotion, …).
  3. POST /render returns a cached PDF when nothing it prints has changed,
     otherwise renders a fresh one (see app/pdf/render_or_cache.py).
  4. Editing a template bumps `version`, which re-renders every card.

Access: template configuration is admin-only. Staff may read templates,
rosters and cards, write remarks/house, and render, for their own classes.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..constants import CLASSES, canonical_class
from ..deps import (
    CurrentUser, assert_class_allowed, current_user, current_user_sse, db_dep, require_admin,
)
from ..models.pdf_template import PdfCache, PdfStudentData, PdfTemplate, TemplateKind
from ..models.record_status import RecordStatus
from ..models.student import Student
from ..pdf.render import render_html, render_pdf
from ..pdf.render_or_cache import render_students, report_card_payload
from ..pdf.schemas import STUDENT_DATA_SCHEMA_BY_KIND, TEMPLATE_SCHEMA_BY_KIND
from ..services.report_cards import (
    SCOPE_LABELS, gather_class_inputs, photo_data_uri, resolve_template, template_scope, term_key,
)
from ..services.results import scope_from_term
from ..services.sessions import get_session

log = logging.getLogger(__name__)
router = APIRouter(prefix="/pdf/templates", tags=["pdf-templates"])

ScopeT = Literal["term1", "term2", "annual"]
LayoutT = Literal["summary", "components"]
ADMIN_ROLES = ("admin", "super_admin")
# Bigger batches go through background render jobs (routers/pdf_render_jobs.py)
# so a request never outlives gunicorn's 120 s timeout.
MAX_SYNC_RENDER = 40
# What a class teacher may write on a card; everything else is admin-only.
STAFF_STUDENT_FIELDS = {"remarks", "house"}


# ── Request / response shapes ────────────────────────────────────────────


def _canonical_class_or_error(v: str) -> str:
    canon = canonical_class(v)
    if canon is None:
        raise ValueError(f"unknown class {v!r}; expected one of: {', '.join(CLASSES)}")
    return canon


class TemplateCreate(BaseModel):
    kind: str
    class_name: str = Field(min_length=1, max_length=32)
    session: str = Field(min_length=1, max_length=16)
    term: str | None = Field(default=None, max_length=32)
    scope: ScopeT | None = None          # report cards: required (or derivable from term)
    layout: LayoutT = "summary"
    data: dict = Field(default_factory=dict)

    @field_validator("class_name")
    @classmethod
    def _class_name(cls, v: str) -> str:
        return _canonical_class_or_error(v)


class TemplateBulkCreate(BaseModel):
    kind: str = "report-card"
    session: str = Field(min_length=1, max_length=16)
    scope: ScopeT
    layout: LayoutT = "summary"
    term: str | None = Field(default=None, max_length=32)
    class_names: list[str] | None = None   # None = every class
    data: dict = Field(default_factory=dict)


class TemplateUpdate(BaseModel):
    data: dict | None = None
    layout: LayoutT | None = None


class TemplateOut(BaseModel):
    id: int
    kind: str
    class_name: str
    session: str
    term: str | None
    scope: str | None = None
    layout: str = "summary"
    version: int
    data: dict
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


class SkippedClass(BaseModel):
    class_name: str
    reason: str


class BulkCreateOut(BaseModel):
    created: list[TemplateOut]
    skipped: list[SkippedClass]


class StudentDataEntry(BaseModel):
    student_id: int
    data: dict


class StudentDataBulkUpsert(BaseModel):
    entries: list[StudentDataEntry]


class StudentDataOut(BaseModel):
    student_id: int
    data: dict
    updated_at: datetime
    updated_by: str


class StudentRosterRow(BaseModel):
    id: int
    name: str
    roll_no: str | None = None
    has_data: bool
    cached_pdf_id: int | None           # a PDF that matches what the card would print now
    stale_pdf_id: int | None = None     # a PDF exists but marks/remarks/settings changed since
    # Report cards only:
    has_marks: bool = False
    draft_marks: int = 0                 # marks left out because their batch is still a draft
    provisional: bool = False            # some marks missing or still drafts
    missing_dob: bool = False
    has_photo: bool = False
    has_remarks: bool = False
    house: str | None = None
    rank: int | None = None
    total: float | None = None
    max: float | None = None
    percentage: float | None = None
    attendance_pct: float | None = None
    error: str | None = None             # why a card can't be produced yet


class RosterOut(BaseModel):
    template_id: int
    scope: str | None
    class_size: int
    warnings: list[str] = Field(default_factory=list)
    students: list[StudentRosterRow]


class RenderRequest(BaseModel):
    student_ids: list[int] = Field(min_length=1)
    force: bool = False
    include_drafts: bool | None = None   # super-admin only; default = template setting


class RenderResultRow(BaseModel):
    student_id: int
    status: str   # "cached" | "rendered" | "error"
    pdf_id: int | None = None
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)


class RenderResponse(BaseModel):
    results: list[RenderResultRow]


# ── Helpers ──────────────────────────────────────────────────────────────


def _kind_or_404(kind: str) -> TemplateKind:
    try:
        return TemplateKind(kind)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"unknown template kind: {kind!r}")


def _validate_template_data(kind: TemplateKind, data: dict) -> dict:
    schema_cls = TEMPLATE_SCHEMA_BY_KIND.get(kind.value)
    if not schema_cls:
        raise HTTPException(status_code=500, detail=f"no template schema for {kind.value}")
    try:
        return schema_cls.model_validate(data).model_dump(mode="json")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())


def _validate_student_data(kind: TemplateKind, data: dict) -> dict:
    schema_cls = STUDENT_DATA_SCHEMA_BY_KIND.get(kind.value)
    if not schema_cls:
        raise HTTPException(status_code=500, detail=f"no student-data schema for {kind.value}")
    try:
        return schema_cls.model_validate(data).model_dump(mode="json")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())


def _serialize_template(t: PdfTemplate) -> TemplateOut:
    return TemplateOut(
        id=t.id, kind=t.kind.value, class_name=t.class_name,
        session=t.session, term=t.term, scope=t.scope, layout=t.layout or "summary",
        version=t.version, data=t.data,
        created_at=t.created_at, created_by=t.created_by,
        updated_at=t.updated_at, updated_by=t.updated_by,
    )


def _get_template_or_404(db: Session, template_id: int) -> PdfTemplate:
    t = db.get(PdfTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


def _template_for(db: Session, user: CurrentUser, template_id: int) -> PdfTemplate:
    """The template, if the caller may see its class (staff: own classes only)."""
    t = _get_template_or_404(db, template_id)
    assert_class_allowed(user, t.class_name)
    return t


def _require_session(db: Session, session: str) -> None:
    if get_session(db, session) is None:
        raise HTTPException(
            status_code=422,
            detail=f"Session {session!r} is not an academic session yet (add it on the Sessions page).",
        )


def _scope_taken(db: Session, kind: TemplateKind, class_name: str, session: str, scope: str | None,
                 term: str | None) -> bool:
    """A template already covers this class + session + scope (or the same term label)."""
    rows = db.scalars(
        select(PdfTemplate).where(
            PdfTemplate.kind == kind, PdfTemplate.class_name == class_name, PdfTemplate.session == session,
        )
    ).all()
    for t in rows:
        if t.term_key == term_key(term):
            return True
        if kind == TemplateKind.report_card and scope and template_scope(t) == scope:
            return True
    return False


def _new_template(kind: TemplateKind, class_name: str, session: str, term: str | None, scope: str | None,
                  layout: str, data: dict, actor: str) -> PdfTemplate:
    return PdfTemplate(
        kind=kind, class_name=class_name, session=session, term=term, term_key=term_key(term),
        scope=scope, layout=layout, version=1, data=data, created_by=actor, updated_by=actor,
    )


# ── Templates ────────────────────────────────────────────────────────────


@router.get("", response_model=list[TemplateOut])
def list_templates(
    kind: str | None = Query(default=None),
    class_name: str | None = Query(default=None),
    session: str | None = Query(default=None),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    stmt = select(PdfTemplate).order_by(PdfTemplate.updated_at.desc())
    if kind:
        stmt = stmt.where(PdfTemplate.kind == _kind_or_404(kind))
    if class_name:
        stmt = stmt.where(PdfTemplate.class_name == class_name)
    if session:
        stmt = stmt.where(PdfTemplate.session == session)
    if user.role not in ADMIN_ROLES:
        stmt = stmt.where(PdfTemplate.class_name.in_(user.allowed_classes or []))
    return [_serialize_template(t) for t in db.scalars(stmt)]


# Registered before "/{template_id}" so "resolve" isn't parsed as an id.
@router.get("/resolve", response_model=TemplateOut | None)
def resolve(
    class_name: str = Query(alias="class"),
    session: str = Query(),
    scope: ScopeT = Query(),
    kind: str = Query(default="report-card"),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """The template for a class, session and scope, or null when none exists yet."""
    assert_class_allowed(user, class_name)
    t = resolve_template(db, class_name=class_name, session=session, scope=scope, kind=_kind_or_404(kind))
    return _serialize_template(t) if t else None


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(
    template_id: int,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    return _serialize_template(_template_for(db, user, template_id))


@router.post("", response_model=TemplateOut, status_code=201)
def create_template(
    body: TemplateCreate,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    kind = _kind_or_404(body.kind)
    validated = _validate_template_data(kind, body.data)
    _require_session(db, body.session)

    scope: str | None = None
    term = body.term
    if kind == TemplateKind.report_card:
        scope = body.scope or scope_from_term(term)
        if scope is None:
            raise HTTPException(status_code=422, detail="Pick the result scope: Term 1, Term 2 or Annual.")
        term = term or SCOPE_LABELS[scope]

    if _scope_taken(db, kind, body.class_name, body.session, scope, term):
        raise HTTPException(
            status_code=409,
            detail=f"A {body.kind} template already exists for {body.class_name}, {body.session}, "
                   f"{term or scope or '—'}. Edit it instead.",
        )
    t = _new_template(kind, body.class_name, body.session, term, scope, body.layout, validated, user.name)
    db.add(t)
    db.commit()
    db.refresh(t)
    return _serialize_template(t)


@router.post("/bulk-create", response_model=BulkCreateOut, status_code=201)
def bulk_create(
    body: TemplateBulkCreate,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    """One report-card template per class (all classes by default); existing ones are skipped."""
    kind = _kind_or_404(body.kind)
    if kind != TemplateKind.report_card:
        raise HTTPException(status_code=422, detail="Bulk create is for report cards only.")
    validated = _validate_template_data(kind, body.data)
    _require_session(db, body.session)
    term = body.term or SCOPE_LABELS[body.scope]

    classes: list[str] = []
    for raw in body.class_names or CLASSES:
        canon = canonical_class(raw)
        if canon is None:
            raise HTTPException(status_code=422, detail=f"unknown class {raw!r}")
        if canon not in classes:
            classes.append(canon)

    created: list[PdfTemplate] = []
    skipped: list[SkippedClass] = []
    for cls in classes:
        if _scope_taken(db, kind, cls, body.session, body.scope, term):
            skipped.append(SkippedClass(class_name=cls, reason="a template for this term already exists"))
            continue
        t = _new_template(kind, cls, body.session, term, body.scope, body.layout, validated, user.name)
        db.add(t)
        created.append(t)
    db.commit()
    for t in created:
        db.refresh(t)
    log.info("templates bulk created", extra={
        # Never `created`/`name`/… here: reserved LogRecord attributes (Gotcha #12).
        "event": "pdf_templates_bulk_created", "created_count": len(created), "skipped_count": len(skipped),
        "session": body.session, "scope": body.scope, "actor": user.name,
    })
    return BulkCreateOut(created=[_serialize_template(t) for t in created], skipped=skipped)


@router.patch("/{template_id}", response_model=TemplateOut)
def update_template(
    template_id: int,
    body: TemplateUpdate,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    """Edit settings and/or layout; class, session, term and scope are fixed at creation."""
    t = _get_template_or_404(db, template_id)
    changed = False
    if body.data is not None:
        t.data = _validate_template_data(t.kind, body.data)
        changed = True
    if body.layout is not None and body.layout != (t.layout or "summary"):
        t.layout = body.layout
        changed = True
    if changed:
        t.version += 1
        t.updated_by = user.name
        db.commit()
        db.refresh(t)
    return _serialize_template(t)


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: int,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    t = _get_template_or_404(db, template_id)
    db.delete(t)  # CASCADE wipes pdf_cache rows
    db.commit()
    return Response(status_code=204)


# ── Per-student data ─────────────────────────────────────────────────────


def _active_ids(db: Session, class_name: str) -> set[int]:
    return set(db.scalars(
        select(Student.id).where(Student.class_name == class_name, Student.status != RecordStatus.deleted)
    ))


@router.get("/{template_id}/student-data", response_model=list[StudentDataOut])
def list_student_data(
    template_id: int,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    t = _template_for(db, user, template_id)
    ids = _active_ids(db, t.class_name)
    if not ids:
        return []
    rows = db.scalars(
        select(PdfStudentData).where(
            PdfStudentData.kind == t.kind,
            PdfStudentData.session == t.session,
            PdfStudentData.term_key == term_key(t.term),
            PdfStudentData.student_id.in_(ids),
        )
    )
    return [
        StudentDataOut(student_id=r.student_id, data=r.data, updated_at=r.updated_at, updated_by=r.updated_by)
        for r in rows
    ]


@router.put("/{template_id}/student-data", response_model=list[StudentDataOut])
def upsert_student_data_bulk(
    template_id: int,
    body: StudentDataBulkUpsert,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Merge each entry into the student's stored data (a key sent as null clears it).
    Staff may only write remarks and house; admins may also override computed values."""
    t = _template_for(db, user, template_id)
    is_admin = user.role in ADMIN_ROLES
    valid_ids = _active_ids(db, t.class_name)

    saved: list[StudentDataOut] = []
    for entry in body.entries:
        if entry.student_id not in valid_ids:
            raise HTTPException(status_code=422, detail=f"student {entry.student_id} is not in class {t.class_name}")
        if not is_admin:
            extra = set(entry.data) - STAFF_STUDENT_FIELDS
            if extra:
                raise HTTPException(
                    status_code=422,
                    detail=f"Class teachers can set {', '.join(sorted(STAFF_STUDENT_FIELDS))} only, not {', '.join(sorted(extra))}.",
                )
        existing = db.scalar(
            select(PdfStudentData).where(
                PdfStudentData.kind == t.kind,
                PdfStudentData.student_id == entry.student_id,
                PdfStudentData.session == t.session,
                PdfStudentData.term_key == term_key(t.term),
            )
        )
        merged = {**((existing.data or {}) if existing else {}), **entry.data}
        validated = _validate_student_data(t.kind, merged)
        if existing:
            existing.data = validated
            existing.updated_by = user.name
            row = existing
        else:
            row = PdfStudentData(
                kind=t.kind, student_id=entry.student_id, session=t.session,
                term=t.term, term_key=term_key(t.term), data=validated, updated_by=user.name,
            )
            db.add(row)
        db.flush()
        saved.append(StudentDataOut(student_id=row.student_id, data=row.data,
                                    updated_at=row.updated_at, updated_by=row.updated_by))
    db.commit()
    return saved


@router.delete("/{template_id}/student-data/{student_id}", status_code=204)
def delete_student_data(
    template_id: int,
    student_id: int,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    t = _get_template_or_404(db, template_id)
    row = db.scalar(
        select(PdfStudentData).where(
            PdfStudentData.kind == t.kind,
            PdfStudentData.student_id == student_id,
            PdfStudentData.session == t.session,
            PdfStudentData.term_key == term_key(t.term),
        )
    )
    if row:
        db.delete(row)
        db.commit()
    return Response(status_code=204)


# ── Roster + card state for the render screen ────────────────────────────


@router.get("/{template_id}/roster", response_model=RosterOut)
def template_roster_v2(
    template_id: int,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Every active student with what their card would show and whether the
    stored PDF still matches it (fresh) or predates a change (stale)."""
    t = _template_for(db, user, template_id)
    cache_rows = {
        c.student_id: c for c in db.scalars(
            select(PdfCache).where(
                PdfCache.kind == t.kind, PdfCache.template_id == t.id, PdfCache.template_version == t.version,
            )
        )
    }
    if t.kind != TemplateKind.report_card:
        roster = sorted(
            db.scalars(select(Student).where(Student.class_name == t.class_name,
                                             Student.status != RecordStatus.deleted)).all(),
            key=lambda s: s.name.lower(),
        )
        filled = set(db.scalars(select(PdfStudentData.student_id).where(
            PdfStudentData.kind == t.kind, PdfStudentData.session == t.session,
            PdfStudentData.term_key == term_key(t.term),
        )))
        return RosterOut(template_id=t.id, scope=None, class_size=len(roster), students=[
            StudentRosterRow(id=s.id, name=s.name, roll_no=s.roll_no, has_data=s.id in filled,
                             cached_pdf_id=cache_rows[s.id].id if s.id in cache_rows else None,
                             missing_dob=s.dob is None)
            for s in roster
        ])

    try:
        inputs = gather_class_inputs(db, t)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    rows: list[StudentRosterRow] = []
    for s in inputs.roster:
        res = inputs.results_by_student[s.id]
        sd = inputs.student_data.get(s.id) or {}
        att = inputs.attendance.get(s.id)
        row = StudentRosterRow(
            id=s.id, name=s.name, roll_no=s.roll_no, has_data=s.id in inputs.student_data,
            cached_pdf_id=None, has_marks=res.has_marks, draft_marks=res.draft_components,
            missing_dob=s.dob is None, has_photo=s.id in inputs.photos,
            has_remarks=bool((sd.get("remarks") or {}).get("en")),
            house=sd.get("house") or inputs.houses.get(s.id),
            rank=sd.get("rank") if sd.get("rank") is not None else res.rank,
            total=res.total_obtained, max=res.total_max, percentage=res.percentage,
            attendance_pct=sd.get("attendancePct") if sd.get("attendancePct") is not None
            else (att.pct if att else None),
        )
        cached = cache_rows.get(s.id)
        try:
            payload, source_hash = report_card_payload(inputs, s.id)
            row.provisional = bool(payload["summary"]["incomplete"] or payload["summary"]["hasDrafts"])
            if cached and cached.source_hash == source_hash:
                row.cached_pdf_id = cached.id
            elif cached:
                row.stale_pdf_id = cached.id
        except (ValueError, ValidationError) as e:
            row.error = str(e)
            row.stale_pdf_id = cached.id if cached else None
        rows.append(row)
    return RosterOut(template_id=t.id, scope=inputs.scope, class_size=len(inputs.roster),
                     warnings=inputs.warnings, students=rows)


@router.get("/{template_id}/students", response_model=list[StudentRosterRow])
def template_roster(
    template_id: int,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Older roster shape (a bare list), kept for clients that predate /roster."""
    return template_roster_v2(template_id, user, db).students


# ── Render + preview ─────────────────────────────────────────────────────


@router.post("/{template_id}/render", response_model=RenderResponse)
def render_bulk(
    template_id: int,
    body: RenderRequest,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    t = _template_for(db, user, template_id)
    if body.include_drafts is not None and user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only super-admin can choose whether draft marks print.")
    if len(body.student_ids) > MAX_SYNC_RENDER:
        raise HTTPException(
            status_code=413,
            detail=f"More than {MAX_SYNC_RENDER} cards at once: start a background run (POST /pdf/templates/{t.id}/render-jobs).",
        )
    results = render_students(
        db, template=t, student_ids=body.student_ids, force=body.force, actor=user.name,
        include_drafts=body.include_drafts,
    )
    return RenderResponse(results=[RenderResultRow(**r) for r in results])


@router.get("/{template_id}/preview")
def preview(
    template_id: int,
    student_id: int = Query(),
    format: Literal["pdf", "html"] = Query(default="pdf"),
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    """Render one report card without touching the cache (admins check a layout here)."""
    t = _get_template_or_404(db, template_id)
    if t.kind != TemplateKind.report_card:
        raise HTTPException(status_code=422, detail="Preview is available for report cards.")
    try:
        inputs = gather_class_inputs(db, t)
        payload, _ = report_card_payload(inputs, student_id)
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    photo = inputs.photos.get(student_id)
    if photo and inputs.settings.get("showPhoto", True):
        payload["student"]["photoUrl"] = photo_data_uri(db, photo.doc_id)
    if format == "html":
        return HTMLResponse(render_html(t.kind.value, payload))
    try:
        pdf = render_pdf(t.kind.value, payload)
    except Exception as e:
        log.exception("preview render failed", extra={"template_id": t.id, "student_id": student_id})
        raise HTTPException(status_code=500, detail=f"Render failed: {e}")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="preview.pdf"'})


# ── Serve cached PDF blob ────────────────────────────────────────────────


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9.-]+", "-", text or "").strip("-") or "x"


def pdf_filename(kind: str, student: Student | None, student_id: int) -> str:
    if student is None:
        return f"{kind}-{student_id}.pdf"
    roll = f"_{_safe(student.roll_no)}" if student.roll_no else ""
    return f"{kind}_{_safe(student.class_name)}{roll}_{_safe(student.name)}.pdf"


def _serve_cache_row(db: Session, user: CurrentUser, pdf_id: int) -> Response:
    row = db.get(PdfCache, pdf_id)
    if not row:
        raise HTTPException(status_code=404, detail="PDF not found")
    # Class scope: staff may only download documents for their own classes
    # (admins pass straight through). PdfCache.student_id cascades on delete,
    # so the student row always exists here.
    student = db.get(Student, row.student_id)
    assert_class_allowed(user, student.class_name if student else "")
    return Response(
        content=row.data,
        media_type=row.mime_type,
        headers={"Content-Disposition": f'inline; filename="{pdf_filename(row.kind.value, student, row.student_id)}"'},
    )


# Exported as a separate router so the URL is /api/pdf/cache/{id}, not under /templates/.
cache_router = APIRouter(prefix="/pdf/cache", tags=["pdf-templates"])


@cache_router.get("/{pdf_id}")
def get_cached_pdf(
    pdf_id: int,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    return _serve_cache_row(db, user, pdf_id)


@cache_router.get("/{pdf_id}/inline")
def get_cached_pdf_query_token(
    pdf_id: int,
    user: CurrentUser = Depends(current_user_sse),
    db: Session = Depends(db_dep),
):
    return _serve_cache_row(db, user, pdf_id)
