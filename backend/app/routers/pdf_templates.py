"""Class-templated PDF generation flow with server-side cache.

Flow per the plan:
  1. Admin creates a Template scoped to (kind, class, session, term).
  2. Admin upserts per-student data for the same scope.
  3. Admin POSTs /render with student_ids → cache hit returns immediately;
     cache miss renders fresh and stores the LONGBLOB.
  4. Editing a Template increments `version` → next /render re-renders.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import db_dep, current_user, current_user_sse, require_admin, CurrentUser
from ..models.pdf_template import PdfTemplate, PdfStudentData, PdfCache, TemplateKind
from ..models.student import Student
from ..pdf.render_or_cache import render_or_cache
from ..pdf.schemas import TEMPLATE_SCHEMA_BY_KIND, STUDENT_DATA_SCHEMA_BY_KIND

log = logging.getLogger(__name__)
router = APIRouter(prefix="/pdf/templates", tags=["pdf-templates"])


# ── Request / response shapes ────────────────────────────────────────────


class TemplateCreate(BaseModel):
    kind: str
    class_name: str = Field(min_length=1, max_length=32)
    session: str = Field(min_length=1, max_length=16)
    term: str | None = Field(default=None, max_length=32)
    data: dict


class TemplateUpdate(BaseModel):
    data: dict


class TemplateOut(BaseModel):
    id: int
    kind: str
    class_name: str
    session: str
    term: str | None
    version: int
    data: dict
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


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
    has_data: bool
    cached_pdf_id: int | None


class RenderRequest(BaseModel):
    student_ids: list[int] = Field(min_length=1)
    force: bool = False


class RenderResultRow(BaseModel):
    student_id: int
    status: str   # "cached" | "rendered" | "error"
    pdf_id: int | None = None
    error: str | None = None


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


def _term_key(term: str | None) -> str:
    return term or ""


def _serialize_template(t: PdfTemplate) -> TemplateOut:
    return TemplateOut(
        id=t.id, kind=t.kind.value, class_name=t.class_name,
        session=t.session, term=t.term, version=t.version, data=t.data,
        created_at=t.created_at, created_by=t.created_by,
        updated_at=t.updated_at, updated_by=t.updated_by,
    )


def _get_template_or_404(db: Session, template_id: int) -> PdfTemplate:
    t = db.get(PdfTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


# ── Templates CRUD (admin only) ──────────────────────────────────────────


@router.get("", response_model=list[TemplateOut])
def list_templates(
    kind: str | None = Query(default=None),
    class_name: str | None = Query(default=None),
    session: str | None = Query(default=None),
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    stmt = select(PdfTemplate).order_by(PdfTemplate.updated_at.desc())
    if kind:
        stmt = stmt.where(PdfTemplate.kind == _kind_or_404(kind))
    if class_name:
        stmt = stmt.where(PdfTemplate.class_name == class_name)
    if session:
        stmt = stmt.where(PdfTemplate.session == session)
    return [_serialize_template(t) for t in db.scalars(stmt)]


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(
    template_id: int,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    return _serialize_template(_get_template_or_404(db, template_id))


@router.post("", response_model=TemplateOut, status_code=201)
def create_template(
    body: TemplateCreate,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    kind = _kind_or_404(body.kind)
    validated = _validate_template_data(kind, body.data)

    # Reject duplicate scope.
    existing = db.scalar(
        select(PdfTemplate).where(
            PdfTemplate.kind == kind,
            PdfTemplate.class_name == body.class_name,
            PdfTemplate.session == body.session,
            PdfTemplate.term_key == _term_key(body.term),
        )
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Template already exists for ({body.kind}, {body.class_name}, "
                   f"{body.session}, {body.term or '—'}). Edit it instead.",
        )

    t = PdfTemplate(
        kind=kind,
        class_name=body.class_name,
        session=body.session,
        term=body.term,
        term_key=_term_key(body.term),
        version=1,
        data=validated,
        created_by=user.name,
        updated_by=user.name,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _serialize_template(t)


@router.patch("/{template_id}", response_model=TemplateOut)
def update_template(
    template_id: int,
    body: TemplateUpdate,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    t = _get_template_or_404(db, template_id)
    t.data = _validate_template_data(t.kind, body.data)
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


@router.get("/{template_id}/student-data", response_model=list[StudentDataOut])
def list_student_data(
    template_id: int,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    t = _get_template_or_404(db, template_id)
    rows = db.scalars(
        select(PdfStudentData).where(
            PdfStudentData.kind == t.kind,
            PdfStudentData.session == t.session,
            PdfStudentData.term_key == _term_key(t.term),
            PdfStudentData.student_id.in_(
                select(Student.id).where(Student.class_name == t.class_name)
            ),
        )
    )
    return [
        StudentDataOut(
            student_id=r.student_id, data=r.data,
            updated_at=r.updated_at, updated_by=r.updated_by,
        )
        for r in rows
    ]


@router.put("/{template_id}/student-data", response_model=list[StudentDataOut])
def upsert_student_data_bulk(
    template_id: int,
    body: StudentDataBulkUpsert,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    t = _get_template_or_404(db, template_id)

    # Bound the upsert to students actually in the template's class.
    valid_student_ids = set(db.scalars(
        select(Student.id).where(Student.class_name == t.class_name)
    ))

    saved: list[StudentDataOut] = []
    for entry in body.entries:
        if entry.student_id not in valid_student_ids:
            raise HTTPException(
                status_code=422,
                detail=f"student {entry.student_id} is not in class {t.class_name}",
            )
        validated = _validate_student_data(t.kind, entry.data)

        existing = db.scalar(
            select(PdfStudentData).where(
                PdfStudentData.kind == t.kind,
                PdfStudentData.student_id == entry.student_id,
                PdfStudentData.session == t.session,
                PdfStudentData.term_key == _term_key(t.term),
            )
        )
        if existing:
            existing.data = validated
            existing.updated_by = user.name
            db.flush()
            row = existing
        else:
            row = PdfStudentData(
                kind=t.kind,
                student_id=entry.student_id,
                session=t.session,
                term=t.term,
                term_key=_term_key(t.term),
                data=validated,
                updated_by=user.name,
            )
            db.add(row)
            db.flush()
        saved.append(StudentDataOut(
            student_id=row.student_id, data=row.data,
            updated_at=row.updated_at, updated_by=row.updated_by,
        ))
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
            PdfStudentData.term_key == _term_key(t.term),
        )
    )
    if row:
        db.delete(row)
        db.commit()
    return Response(status_code=204)


# ── Roster + cache state for the bulk-render UI ──────────────────────────


@router.get("/{template_id}/students", response_model=list[StudentRosterRow])
def template_roster(
    template_id: int,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    t = _get_template_or_404(db, template_id)

    students = list(db.scalars(
        select(Student).where(Student.class_name == t.class_name).order_by(Student.name)
    ))
    student_ids = [s.id for s in students]
    if not student_ids:
        return []

    filled_ids = set(db.scalars(
        select(PdfStudentData.student_id).where(
            PdfStudentData.kind == t.kind,
            PdfStudentData.session == t.session,
            PdfStudentData.term_key == _term_key(t.term),
            PdfStudentData.student_id.in_(student_ids),
        )
    ))

    cache_rows = list(db.scalars(
        select(PdfCache).where(
            PdfCache.kind == t.kind,
            PdfCache.template_id == t.id,
            PdfCache.template_version == t.version,
            PdfCache.student_id.in_(student_ids),
        )
    ))
    cache_map = {c.student_id: c.id for c in cache_rows}

    return [
        StudentRosterRow(
            id=s.id, name=s.name,
            has_data=s.id in filled_ids,
            cached_pdf_id=cache_map.get(s.id),
        )
        for s in students
    ]


# ── Bulk render ──────────────────────────────────────────────────────────


@router.post("/{template_id}/render", response_model=RenderResponse)
def render_bulk(
    template_id: int,
    body: RenderRequest,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    t = _get_template_or_404(db, template_id)
    results: list[RenderResultRow] = []
    for sid in body.student_ids:
        r = render_or_cache(
            db, template=t, student_id=sid, force=body.force, actor=user.name,
        )
        results.append(RenderResultRow(**r))
    return RenderResponse(results=results)


# ── Serve cached PDF blob ────────────────────────────────────────────────


def _serve_cache_row(db: Session, pdf_id: int) -> Response:
    row = db.get(PdfCache, pdf_id)
    if not row:
        raise HTTPException(status_code=404, detail="PDF not found")
    return Response(
        content=row.data,
        media_type=row.mime_type,
        headers={"Content-Disposition": f'inline; filename="{row.kind.value}-{row.student_id}.pdf"'},
    )


# Exported as a separate router so the URL is /api/pdf/cache/{id}, not under /templates/.
cache_router = APIRouter(prefix="/pdf/cache", tags=["pdf-templates"])


@cache_router.get("/{pdf_id}")
def get_cached_pdf(
    pdf_id: int,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    return _serve_cache_row(db, pdf_id)


@cache_router.get("/{pdf_id}/inline")
def get_cached_pdf_query_token(
    pdf_id: int,
    user: CurrentUser = Depends(current_user_sse),
    db: Session = Depends(db_dep),
):
    return _serve_cache_row(db, pdf_id)
