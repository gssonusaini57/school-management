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
from sqlalchemy import false, select
from sqlalchemy.orm import Session

from ..constants import CLASSES, canonical_class
from ..deps import (
    CurrentUser, assert_class_allowed, assert_menu, current_user, current_user_sse, db_dep, has_menu,
    require_admin,
)
from ..models.pdf_template import PdfCache, PdfStudentData, PdfTemplate, TemplateKind
from ..models.record_status import RecordStatus
from ..models.student import Student
from ..pdf.builder import printed_attendance
from ..pdf.render import render_html, render_pdf
from ..pdf.render_or_cache import pseb_payload, render_students, report_card_payload
from ..pdf.schemas import ReportCardStudentData, STUDENT_DATA_SCHEMA_BY_KIND, TEMPLATE_SCHEMA_BY_KIND
from ..services.report_cards import (
    SCOPE_LABELS, gather_class_inputs, photo_data_uri, resolve_template, template_scope, term_key,
)
from ..services.attendance_summary import attendance_summary
from ..services.results import scope_from_term
from ..services.sessions import get_session, scope_dates

log = logging.getLogger(__name__)
router = APIRouter(prefix="/pdf/templates", tags=["pdf-templates"])

ScopeT = Literal["term1", "term2", "annual"]
LayoutT = Literal["summary", "components"]
ADMIN_ROLES = ("admin", "super_admin")
# Staff menu grant each template kind sits behind (admins bypass): report cards
# live under Marks Results, PSEB admit cards under PDF Templates.
KIND_MENU = {TemplateKind.report_card: ("marks-results", "report cards"),
             TemplateKind.pseb_admit_card: ("templates", "PSEB admit cards")}
# Bigger batches go through background render jobs (routers/pdf_render_jobs.py)
# so a request never outlives gunicorn's 120 s timeout.
MAX_SYNC_RENDER = 20
# What a class teacher may write on a card; everything else is admin-only.
STAFF_STUDENT_FIELDS = {"remarks", "house"}
# Attendance day-count overrides (admin-only), checked against the computed counts.
DAY_COUNT_FIELDS = {"workingDays", "daysPresent"}


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
    # Only to fill a missing scope on a legacy template; a set scope never changes.
    scope: ScopeT | None = None


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
    attendance_pct: float | None = None  # value the card prints (override, else computed)
    computed_rank: int | None = None      # what the system computes, shown beside an override
    computed_attendance_pct: float | None = None
    computed_working_days: int | None = None
    computed_days_present: float | None = None
    overrides: list[str] = Field(default_factory=list)   # per-student keys that replace a computed value
    error: str | None = None             # why a card can't be produced yet


class RosterOut(BaseModel):
    template_id: int
    scope: str | None
    class_size: int
    warnings: list[str] = Field(default_factory=list)
    students: list[StudentRosterRow]


class RenderRequest(BaseModel):
    student_ids: list[int] = Field(min_length=1)
    force: bool = False                  # admins only; ignored from staff
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


def _errors(e: ValidationError) -> list[dict]:
    """Pydantic errors as plain JSON (the raw ctx can hold exception objects)."""
    return [{"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
            for err in e.errors(include_url=False, include_context=False)]


def _validate_template_data(kind: TemplateKind, data: dict) -> dict:
    schema_cls = TEMPLATE_SCHEMA_BY_KIND.get(kind.value)
    if not schema_cls:
        raise HTTPException(status_code=500, detail=f"no template schema for {kind.value}")
    try:
        return schema_cls.model_validate(data).model_dump(mode="json")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=_errors(e))


def _student_name(db: Session, student_id: int) -> str:
    s = db.get(Student, student_id)
    return s.name if s else f"Student {student_id}"


def _readable(e: ValidationError) -> str:
    """Pydantic errors as one line ("rank: Input should be greater than or equal to 1; …")."""
    parts = []
    for err in e.errors(include_url=False, include_context=False):
        msg = err["msg"].removeprefix("Value error, ")
        loc = [str(p) for p in err["loc"]]
        parts.append(f"{'.'.join(loc)}: {msg}" if loc and not msg.startswith(loc[0]) else msg)
    return "; ".join(parts)


def _validate_student_data(db: Session, kind: TemplateKind, student_id: int, data: dict) -> dict:
    """One student's merged row, validated. One bad row refuses the whole save,
    so the 422 names the student whose row it is."""
    schema_cls = STUDENT_DATA_SCHEMA_BY_KIND.get(kind.value)
    if not schema_cls:
        raise HTTPException(status_code=500, detail=f"no student-data schema for {kind.value}")
    try:
        out = schema_cls.model_validate(data).model_dump(mode="json")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"{_student_name(db, student_id)}: {_readable(e)}")
    remarks = out.get("remarks") if kind == TemplateKind.report_card else None
    if remarks and remarks.get("pa") is None:
        # "" rather than null: the builder prod ran before v2 (54db9cd) reads a remark
        # as {en: str, pa: str}, and a code-only rollback keeps this database. Read
        # back here, "" means no Punjabi line.
        remarks["pa"] = ""
    return out


def render_options(user: CurrentUser, include_drafts: bool | None, force: bool) -> tuple[bool | None, bool]:
    """The (include_drafts, force) a render request may use.

    Only the super-admin decides whether cards print draft marks: `true` from
    anyone else is refused, and `false` is ignored (the template's setting
    applies), so a teacher's render can't replace the super-admin's card with
    one that leaves the drafts out. Force re-render is admin-only: from a
    teacher it is ignored, and the cache answers as usual.
    """
    if include_drafts and user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only super-admin can choose whether draft marks print.")
    return (include_drafts if user.role == "super_admin" else None), (force and user.role in ADMIN_ROLES)


def _guard_include_drafts(user: CurrentUser, new: dict, old: dict | None) -> None:
    """Only the super-admin decides whether report cards count draft marks."""
    if user.role == "super_admin":
        return
    if bool(new.get("includeDrafts", False)) != bool((old or {}).get("includeDrafts", False)):
        raise HTTPException(
            status_code=403,
            detail="Only the super-admin can change whether report cards include draft marks.",
        )


def _card_attendance(sd: dict, att) -> float | None:
    """The attendance % a student's card prints (override, else computed, recomputed
    from overridden day counts); falls back to the stored values if they don't validate."""
    try:
        return printed_attendance(ReportCardStudentData.model_validate(sd), att)[0]
    except ValueError:  # includes pydantic's ValidationError
        if sd.get("attendancePct") is not None:
            return sd.get("attendancePct")
        return att.pct if att else None


def _check_one_sided_attendance(db: Session, t: PdfTemplate, items: list[tuple[int, dict]]) -> None:
    """Days present may not exceed working days when only one of the two is
    overridden and the other is computed from attendance: the card's own rule.
    Called only for rows whose day counts the request changes."""
    one_sided = [(sid, d) for sid, d in items if (d.get("workingDays") is None) != (d.get("daysPresent") is None)]
    if not one_sided:
        return
    scope = template_scope(t)
    session_row = get_session(db, t.session)
    if scope is None or session_row is None:
        return
    start, end = scope_dates(session_row, scope)
    ids = [sid for sid, _ in one_sided]
    att = attendance_summary(db, student_ids=ids, start=start, end=end)
    names = dict(db.execute(select(Student.id, Student.name).where(Student.id.in_(ids))).all())
    for sid, d in one_sided:
        try:
            printed_attendance(ReportCardStudentData.model_validate(d), att.get(sid))
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"{names.get(sid, f'Student {sid}')}: {e}")


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


def assert_template_access(user: CurrentUser, t: PdfTemplate) -> None:
    """Staff: own classes only, and the menu grant for the template's kind."""
    assert_class_allowed(user, t.class_name)
    key, what = KIND_MENU.get(t.kind, ("templates", "PDF templates"))
    assert_menu(user, key, what)


def _template_for(db: Session, user: CurrentUser, template_id: int) -> PdfTemplate:
    """The template, if the caller may see it (see assert_template_access)."""
    t = _get_template_or_404(db, template_id)
    assert_template_access(user, t)
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


def _unscoped_template(db: Session, class_name: str, session: str) -> PdfTemplate | None:
    """A report-card template of this class + session whose scope can't be told
    (a legacy term label such as "Half Yearly"). Its remarks and overrides are
    keyed by that label, so a new template beside it would strand them: its
    scope gets set instead (PATCH scope)."""
    for t in db.scalars(select(PdfTemplate).where(
        PdfTemplate.kind == TemplateKind.report_card, PdfTemplate.class_name == class_name,
        PdfTemplate.session == session,
    )):
        if template_scope(t) is None:
            return t
    return None


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
        kinds = [k for k, (key, _) in KIND_MENU.items() if has_menu(user, key)]
        stmt = stmt.where(PdfTemplate.kind.in_(kinds)) if kinds else stmt.where(false())
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
    k = _kind_or_404(kind)
    key, what = KIND_MENU[k]
    assert_menu(user, key, what)
    t = resolve_template(db, class_name=class_name, session=session, scope=scope, kind=k)
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
    if kind == TemplateKind.report_card:
        _guard_include_drafts(user, validated, None)
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
    legacy = _unscoped_template(db, body.class_name, body.session) if kind == TemplateKind.report_card else None
    if legacy is not None:
        raise HTTPException(
            status_code=409,
            detail=f'The report-card template "{legacy.term}" for {legacy.class_name}, {legacy.session} has no '
                   "result scope yet. Set its scope (Term 1, Term 2 or Annual) instead of creating another "
                   "template, so its remarks and overrides carry over.",
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
    _guard_include_drafts(user, validated, None)
    _require_session(db, body.session)
    term = body.term or SCOPE_LABELS[body.scope]

    classes: list[str] = []
    requested = CLASSES if body.class_names is None else body.class_names
    if not requested:
        raise HTTPException(status_code=422, detail="Pick at least one class (or leave the list out for all classes).")
    for raw in requested:
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
        legacy = _unscoped_template(db, cls, body.session)
        if legacy is not None:
            skipped.append(SkippedClass(class_name=cls, reason=f'set the scope of "{legacy.term}" instead'))
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
    if body.scope is not None and body.scope != t.scope:
        if t.kind != TemplateKind.report_card or t.scope is not None:
            raise HTTPException(status_code=409, detail="A template's scope is fixed once set. Create a new template instead.")
        siblings = db.scalars(select(PdfTemplate).where(
            PdfTemplate.kind == t.kind, PdfTemplate.class_name == t.class_name,
            PdfTemplate.session == t.session, PdfTemplate.id != t.id,
        )).all()
        if any(template_scope(o) == body.scope for o in siblings):
            raise HTTPException(
                status_code=409,
                detail=f"Another report-card template already covers {t.class_name}, {t.session}, "
                       f"{SCOPE_LABELS[body.scope]}. Use that one, or delete one of them first.",
            )
        t.scope = body.scope
        changed = True
    if body.data is not None:
        validated = _validate_template_data(t.kind, body.data)
        if t.kind == TemplateKind.report_card:
            _guard_include_drafts(user, validated, t.data)
        t.data = validated
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

    pending: list[tuple[int, PdfStudentData | None, dict]] = []
    day_changes: list[tuple[int, dict]] = []
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
        validated = _validate_student_data(db, t.kind, entry.student_id, merged)
        pending.append((entry.student_id, existing, validated))
        # A stored day count can drift past the computed one as attendance is
        # marked; only a request that changes the counts is held to them, so
        # it never blocks a remark (the card itself refuses to print it).
        if DAY_COUNT_FIELDS & set(entry.data):
            day_changes.append((entry.student_id, validated))
    if t.kind == TemplateKind.report_card and day_changes:
        _check_one_sided_attendance(db, t, day_changes)

    saved: list[StudentDataOut] = []
    for student_id, existing, validated in pending:
        if existing:
            existing.data = validated
            existing.updated_by = user.name
            row = existing
        else:
            row = PdfStudentData(
                kind=t.kind, student_id=student_id, session=t.session,
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


def _set_card_state(row: StudentRosterRow, cached: PdfCache | None, t: PdfTemplate, source_hash: str) -> None:
    """Fresh when the stored card is this template version's and matches what
    would print now (the render's cache rule); any other stored card is stale."""
    if cached is None:
        return
    if cached.template_version == t.version and cached.source_hash == source_hash:
        row.cached_pdf_id = cached.id
    else:
        row.stale_pdf_id = cached.id


@router.get("/{template_id}/roster", response_model=RosterOut)
def template_roster_v2(
    template_id: int,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    """Every active student with what their card would show and whether the
    stored PDF still matches it (fresh) or predates a change (stale)."""
    t = _template_for(db, user, template_id)
    # Each student's newest card for this template, whatever its version: after a
    # settings change the earlier cards read "needs update" and stay downloadable,
    # instead of looking never generated. Ascending order, so the newest wins.
    cache_rows: dict[int, PdfCache] = {}
    for c in db.scalars(
        select(PdfCache).where(PdfCache.kind == t.kind, PdfCache.template_id == t.id)
        .order_by(PdfCache.template_version)
    ):
        cache_rows[c.student_id] = c
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
        rows_out: list[StudentRosterRow] = []
        for s in roster:
            cached = cache_rows.get(s.id)
            row = StudentRosterRow(id=s.id, name=s.name, roll_no=s.roll_no, has_data=s.id in filled,
                                   cached_pdf_id=None, missing_dob=s.dob is None)
            try:
                _, source_hash = pseb_payload(db, t, s)
                _set_card_state(row, cached, t, source_hash)
            except ValueError as e:
                row.error = str(e)
                # Admit cards made before the date-of-birth check printed an invented
                # date (2010-01-01): never offer one as the outdated card.
                row.stale_pdf_id = cached.id if cached and s.dob is not None else None
            rows_out.append(row)
        return RosterOut(template_id=t.id, scope=None, class_size=len(roster), students=rows_out)

    try:
        inputs = gather_class_inputs(db, t)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    rows: list[StudentRosterRow] = []
    for s in inputs.roster:
        res = inputs.results_by_student[s.id]
        sd = inputs.student_data.get(s.id) or {}
        att = inputs.attendance.get(s.id)
        overridden = [k for k in ("rank", "classSize", "attendancePct", "workingDays", "daysPresent", "promotion")
                      if sd.get(k) not in (None, "")]
        row = StudentRosterRow(
            id=s.id, name=s.name, roll_no=s.roll_no, has_data=s.id in inputs.student_data,
            cached_pdf_id=None, has_marks=res.has_marks, draft_marks=res.draft_components,
            missing_dob=s.dob is None, has_photo=s.id in inputs.photos,
            has_remarks=bool((sd.get("remarks") or {}).get("en")),
            house=sd.get("house") or inputs.houses.get(s.id),
            rank=sd.get("rank") if sd.get("rank") is not None else res.rank,
            total=res.total_obtained, max=res.total_max, percentage=res.percentage,
            attendance_pct=_card_attendance(sd, att),
            computed_rank=res.rank,
            computed_attendance_pct=att.pct if att else None,
            computed_working_days=att.working_days if att else None,
            computed_days_present=att.days_present if att else None,
            overrides=overridden,
        )
        cached = cache_rows.get(s.id)
        try:
            payload, source_hash = report_card_payload(inputs, s.id)
            summ = payload["summary"]
            row.provisional = bool(summ["incomplete"] or summ["hasDrafts"]
                                   or (summ["rankProvisional"] and inputs.settings.get("showRank", True)))
            _set_card_state(row, cached, t, source_hash)
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
    include_drafts, force = render_options(user, body.include_drafts, body.force)
    if len(body.student_ids) > MAX_SYNC_RENDER:
        raise HTTPException(
            status_code=413,
            detail=f"More than {MAX_SYNC_RENDER} cards at once: start a background run (POST /pdf/templates/{t.id}/render-jobs).",
        )
    results = render_students(
        db, template=t, student_ids=body.student_ids, force=force, actor=user.name,
        include_drafts=include_drafts,
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
    key, what = KIND_MENU.get(row.kind, ("templates", "PDF templates"))
    assert_menu(user, key, what)
    if row.kind == TemplateKind.pseb_admit_card and student is not None and student.dob is None:
        # Made before the date-of-birth check, so it printed an invented date.
        raise HTTPException(
            status_code=409,
            detail=f"{student.name} has no date of birth on record; add it and generate the admit card again.",
        )
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
