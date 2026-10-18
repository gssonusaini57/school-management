"""Background bulk rendering with progress and a ZIP download.

  POST /pdf/templates/{id}/render-jobs    start a job (202), one active job per template
  GET  /pdf/render-jobs?template_id=      recent jobs for a template
  GET  /pdf/render-jobs/{id}              progress + per-student results
  POST /pdf/render-jobs/{id}/cancel       stop after the current student
  GET  /pdf/render-jobs/{id}/zip          every finished card in one ZIP (+ /zip/inline?token=)
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import CurrentUser, assert_class_allowed, current_user, current_user_sse, db_dep
from ..models.pdf_render_job import PdfRenderJob, RenderJobStatus
from ..models.pdf_template import PdfTemplate
from ..services import render_jobs
from ..services.roster import active_roster
from .pdf_templates import ADMIN_ROLES, _safe, pdf_filename

router = APIRouter(prefix="/pdf", tags=["pdf-render-jobs"])


class RenderJobCreate(BaseModel):
    student_ids: list[int] | None = None   # None = every active student in the class
    force: bool = False
    include_drafts: bool | None = None     # super-admin only


class RenderJobResult(BaseModel):
    student_id: int
    status: str
    pdf_id: int | None = None
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)


class RenderJobOut(BaseModel):
    id: int
    template_id: int
    status: str
    total: int
    done_count: int
    error_count: int
    requested_by: str
    error: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    results: list[RenderJobResult] = Field(default_factory=list)


def _out(job: PdfRenderJob) -> RenderJobOut:
    return RenderJobOut(
        id=job.id, template_id=job.template_id, status=job.status.value, total=job.total,
        done_count=job.done_count, error_count=job.error_count, requested_by=job.requested_by,
        error=job.error, created_at=job.created_at, started_at=job.started_at, finished_at=job.finished_at,
        results=[RenderJobResult(**r) for r in (job.results or [])],
    )


def _template(db: Session, user: CurrentUser, template_id: int) -> PdfTemplate:
    t = db.get(PdfTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    assert_class_allowed(user, t.class_name)
    return t


def _job(db: Session, user: CurrentUser, job_id: int) -> tuple[PdfRenderJob, PdfTemplate]:
    job = db.get(PdfRenderJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return render_jobs.sweep_stale(db, job), _template(db, user, job.template_id)


@router.post("/templates/{template_id}/render-jobs", response_model=RenderJobOut, status_code=202)
def create_render_job(
    template_id: int,
    body: RenderJobCreate,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    t = _template(db, user, template_id)
    if body.include_drafts is not None and user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only super-admin can choose whether draft marks print.")
    if render_jobs.active_job(db, t.id):
        raise HTTPException(status_code=409, detail="Cards for this class are already being generated. Wait for that run to finish.")
    roster_ids = [s.id for s in active_roster(db, t.class_name)]
    ids = roster_ids if body.student_ids is None else [i for i in body.student_ids if i in set(roster_ids)]
    if not ids:
        raise HTTPException(status_code=422, detail="No active students selected in this class.")
    job = render_jobs.create_job(db, t, ids, include_drafts=body.include_drafts, force=body.force, actor=user.name)
    render_jobs.start_job(job.id)
    return _out(job)


@router.get("/render-jobs", response_model=list[RenderJobOut])
def list_render_jobs(
    template_id: int = Query(),
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    _template(db, user, template_id)
    jobs = db.scalars(
        select(PdfRenderJob).where(PdfRenderJob.template_id == template_id)
        .order_by(PdfRenderJob.created_at.desc(), PdfRenderJob.id.desc()).limit(10)
    ).all()
    return [_out(render_jobs.sweep_stale(db, j)) for j in jobs]


@router.get("/render-jobs/{job_id}", response_model=RenderJobOut)
def get_render_job(job_id: int, user: CurrentUser = Depends(current_user), db: Session = Depends(db_dep)):
    job, _ = _job(db, user, job_id)
    return _out(job)


@router.post("/render-jobs/{job_id}/cancel", response_model=RenderJobOut)
def cancel_render_job(job_id: int, user: CurrentUser = Depends(current_user), db: Session = Depends(db_dep)):
    job, _ = _job(db, user, job_id)
    if user.role not in ADMIN_ROLES and job.requested_by != user.name:
        raise HTTPException(status_code=403, detail="Only the person who started this run, or an admin, can cancel it.")
    if job.status in render_jobs.ACTIVE:
        job.status = RenderJobStatus.cancelled
        job.finished_at = datetime.utcnow()
        db.commit()
    return _out(job)


def _zip_response(db: Session, user: CurrentUser, job_id: int) -> Response:
    job, t = _job(db, user, job_id)
    if job.status in render_jobs.ACTIVE:
        raise HTTPException(status_code=409, detail="This run is still in progress.")
    data = render_jobs.zip_bytes(db, job, pdf_filename)
    name = f"{t.kind.value}s_{_safe(t.class_name)}_{_safe(t.term or t.session)}.zip"
    return Response(content=data, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/render-jobs/{job_id}/zip")
def render_job_zip(job_id: int, user: CurrentUser = Depends(current_user), db: Session = Depends(db_dep)):
    return _zip_response(db, user, job_id)


@router.get("/render-jobs/{job_id}/zip/inline")
def render_job_zip_inline(job_id: int, user: CurrentUser = Depends(current_user_sse), db: Session = Depends(db_dep)):
    return _zip_response(db, user, job_id)
