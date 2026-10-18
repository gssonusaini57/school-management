"""Background bulk rendering.

`create_job` records a request; `start_job` launches a detached runner
process (`python -m app.jobs.render_job <id>`) that calls `run_job`, which
renders one student at a time through render_students and records progress
after each. Clients poll the job row. A runner that stops reporting for
STALE_AFTER seconds (killed by a deploy, say) is marked failed on the next
poll; re-running is cheap because finished cards come back from the cache.
"""
from __future__ import annotations

import io
import logging
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import SessionLocal
from ..models.pdf_render_job import PdfRenderJob, RenderJobStatus
from ..models.pdf_template import PdfCache, PdfTemplate
from ..models.student import Student

log = logging.getLogger(__name__)

STALE_AFTER = timedelta(seconds=120)
ACTIVE = (RenderJobStatus.queued, RenderJobStatus.running)
BACKEND_DIR = Path(__file__).resolve().parents[2]   # holds the `app` package


class JobCancelled(Exception):
    pass


def _now() -> datetime:
    return datetime.utcnow()


def sweep_stale(db: Session, job: PdfRenderJob) -> PdfRenderJob:
    """Mark a job failed when its runner stopped reporting (or never started)."""
    now = _now()
    if job.status == RenderJobStatus.running and job.heartbeat_at and now - job.heartbeat_at > STALE_AFTER:
        job.status = RenderJobStatus.failed
        job.error = "The render process stopped (for example during a deploy). Run it again; finished cards are reused."
        job.finished_at = now
        db.commit()
    elif job.status == RenderJobStatus.queued and job.created_at and now - job.created_at > STALE_AFTER:
        job.status = RenderJobStatus.failed
        job.error = "The render process did not start. Try again."
        job.finished_at = now
        db.commit()
    return job


def active_job(db: Session, template_id: int) -> PdfRenderJob | None:
    for job in db.scalars(
        select(PdfRenderJob).where(PdfRenderJob.template_id == template_id, PdfRenderJob.status.in_(ACTIVE))
    ):
        if sweep_stale(db, job).status in ACTIVE:
            return job
    return None


def create_job(
    db: Session, template: PdfTemplate, student_ids: list[int], *,
    include_drafts: bool | None, force: bool, actor: str,
) -> PdfRenderJob:
    job = PdfRenderJob(
        template_id=template.id, template_version=template.version, requested_by=actor,
        status=RenderJobStatus.queued, include_drafts=include_drafts, force=force,
        student_ids=list(student_ids), total=len(student_ids), done_count=0, error_count=0, results=[],
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def start_job(job_id: int) -> None:
    """Launch the detached runner. It inherits the service environment (.env)
    and survives the request; output goes to LOG_DIR/render-jobs.log."""
    log_dir = Path(settings.LOG_DIR)
    if not log_dir.is_absolute():
        log_dir = BACKEND_DIR / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "render-jobs.log", "ab") as out:
        subprocess.Popen(
            [sys.executable, "-m", "app.jobs.render_job", str(job_id)],
            cwd=str(BACKEND_DIR), stdout=out, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, start_new_session=True, env=os.environ.copy(),
        )


def run_job(job_id: int, session_factory: Callable[[], Session] = SessionLocal) -> None:
    """Render every student of a job, recording progress after each one."""
    from ..pdf.render_or_cache import render_students  # heavy import, runner only

    db = session_factory()
    try:
        job = db.get(PdfRenderJob, job_id)
        if job is None or job.status != RenderJobStatus.queued:
            return
        job.status = RenderJobStatus.running
        job.started_at = job.heartbeat_at = _now()
        job.worker_pid = os.getpid()
        db.commit()
        template = db.get(PdfTemplate, job.template_id)
        results: list[dict[str, Any]] = list(job.results or [])

        def on_result(r: dict[str, Any]) -> None:
            results.append(r)
            db.refresh(job)
            job.results = list(results)          # new list: JSON columns need reassignment
            job.done_count = len(results)
            job.error_count = sum(1 for x in results if x["status"] == "error")
            job.heartbeat_at = _now()
            cancelled = job.status == RenderJobStatus.cancelled
            db.commit()
            if cancelled:
                raise JobCancelled()

        try:
            render_students(
                db, template=template, student_ids=list(job.student_ids), force=job.force,
                actor=job.requested_by, include_drafts=job.include_drafts, on_result=on_result,
            )
            db.refresh(job)
            if job.status == RenderJobStatus.running:
                job.status = RenderJobStatus.done
        except JobCancelled:
            db.refresh(job)
        job.finished_at = _now()
        db.commit()
    except Exception as e:
        log.exception("render job failed", extra={"job_id": job_id})
        db.rollback()
        job = db.get(PdfRenderJob, job_id)
        if job is not None:
            job.status = RenderJobStatus.failed
            job.error = str(e)[:2000]
            job.finished_at = _now()
            db.commit()
    finally:
        db.close()


def zip_bytes(db: Session, job: PdfRenderJob, filename_for: Callable[[str, Student | None, int], str]) -> bytes:
    """A ZIP of every card the job produced (rendered or reused from cache)."""
    ids = [r["pdf_id"] for r in (job.results or []) if r.get("pdf_id") and r["status"] in ("rendered", "cached")]
    buf = io.BytesIO()
    used: set[str] = set()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for row in db.scalars(select(PdfCache).where(PdfCache.id.in_(ids))) if ids else []:
            student = db.get(Student, row.student_id)
            name = filename_for(row.kind.value, student, row.student_id)
            if name in used:
                name = name.replace(".pdf", f"_{row.student_id}.pdf")
            used.add(name)
            zf.writestr(name, row.data)
    return buf.getvalue()
