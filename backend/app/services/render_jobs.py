"""Background bulk rendering.

`create_job` records a request; `start_job` launches a detached runner
process (`python -m app.jobs.render_job <id>`) that calls `run_job`, which
renders one student at a time through render_students and records progress
after each. Clients poll the job row. A runner that stops reporting for
STALE_AFTER seconds (killed by a deploy, say) is marked failed on the next
poll; re-running is cheap because finished cards come back from the cache.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import threading
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import SessionLocal
from ..models.pdf_render_job import PdfRenderJob, RenderJobStatus
from ..models.pdf_template import PdfCache, PdfTemplate, TemplateKind
from ..models.record_status import RecordStatus
from ..models.student import Student

log = logging.getLogger(__name__)

STALE_AFTER = timedelta(seconds=120)
ACTIVE = (RenderJobStatus.queued, RenderJobStatus.running)
# Each runner is a full Python + WeasyPrint process; the prod box also runs
# MySQL, Tomcat and the TEST instance, so only a couple may render at once.
MAX_ACTIVE_JOBS = 2
BACKEND_DIR = Path(__file__).resolve().parents[2]   # holds the `app` package


class JobCancelled(Exception):
    pass


def _now() -> datetime:
    return datetime.utcnow()


def _stale_reason(job: PdfRenderJob, now: datetime) -> str | None:
    """Why a job's runner counts as gone (stopped reporting, or never started); None while it is alive."""
    if job.status == RenderJobStatus.running and job.heartbeat_at and now - job.heartbeat_at > STALE_AFTER:
        return "The render process stopped (for example during a deploy). Run it again; finished cards are reused."
    if job.status == RenderJobStatus.queued and job.created_at and now - job.created_at > STALE_AFTER:
        return "The render process did not start. Try again."
    return None


def sweep_stale(db: Session, job: PdfRenderJob) -> PdfRenderJob:
    """Mark a job failed when its runner stopped reporting (or never started)."""
    now = _now()
    reason = _stale_reason(job, now)
    if reason:
        job.status = RenderJobStatus.failed
        job.error = reason
        job.finished_at = now
        db.commit()
    return job


def _active_jobs(db: Session, template_id: int | None = None) -> list[PdfRenderJob]:
    stmt = select(PdfRenderJob).where(PdfRenderJob.status.in_(ACTIVE))
    if template_id is not None:
        stmt = stmt.where(PdfRenderJob.template_id == template_id)
    # Fresh column values even for jobs this session loaded earlier.
    return list(db.scalars(stmt.execution_options(populate_existing=True)))


def _alive(db: Session, job: PdfRenderJob, sweep: bool) -> bool:
    if sweep:
        return sweep_stale(db, job).status in ACTIVE
    return job.status in ACTIVE and _stale_reason(job, _now()) is None


def sweep_active(db: Session) -> None:
    """Mark every queued or running job whose runner is gone as failed (commits when it marks one)."""
    for job in _active_jobs(db):
        sweep_stale(db, job)


def active_job_count(db: Session, *, sweep: bool = True) -> int:
    """Runs in progress across every template. Stale ones are swept first, which
    commits; sweep=False only leaves them out, for a caller holding a row lock."""
    return sum(1 for j in _active_jobs(db) if _alive(db, j, sweep))


def active_job(db: Session, template_id: int, *, sweep: bool = True) -> PdfRenderJob | None:
    """The template's run in progress, if any (sweep as in active_job_count)."""
    for job in _active_jobs(db, template_id):
        if _alive(db, job, sweep):
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
        # Set here, not by MySQL's CURRENT_TIMESTAMP (session time zone): every job
        # timestamp must come from the same UTC clock as the stale-job sweep.
        created_at=_now(),
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
        proc = subprocess.Popen(
            [sys.executable, "-m", "app.jobs.render_job", str(job_id)],
            cwd=str(BACKEND_DIR), stdout=out, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, start_new_session=True, env=os.environ.copy(),
        )
    # Reap the child when it exits so it never lingers as a zombie under the worker.
    threading.Thread(target=proc.wait, name=f"render-job-{job_id}", daemon=True).start()


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


LEFT_OUT_NOTE = "CARDS_NOT_INCLUDED.txt"


@dataclass
class JobZip:
    spool: Any        # SpooledTemporaryFile positioned at the start
    included: int     # cards in the ZIP
    outdated: int     # cards the run made that no longer match what would print


def current_hashes(db: Session, template: PdfTemplate, student_ids: list[int],
                   include_drafts: bool | None) -> dict[int, str]:
    """student_id -> source hash of the card that would print now (with the
    run's draft setting). Students whose card can't be built now are absent."""
    from ..pdf.render_or_cache import pseb_payload, report_card_payload  # heavy: WeasyPrint
    from .report_cards import gather_class_inputs

    out: dict[int, str] = {}
    if template.kind == TemplateKind.report_card:
        try:
            inputs = gather_class_inputs(db, template, include_drafts=include_drafts)
        except ValueError:
            return out
        for sid in student_ids:
            try:
                out[sid] = report_card_payload(inputs, sid)[1]
            except ValueError:   # pydantic's ValidationError included
                pass
        return out
    for sid in student_ids:
        student = db.get(Student, sid)
        if student is None or student.status == RecordStatus.deleted or student.class_name != template.class_name:
            continue
        try:
            out[sid] = pseb_payload(db, template, student)[1]
        except ValueError:
            pass
    return out


def zip_file(db: Session, job: PdfRenderJob, filename_for: Callable[[str, Student | None, int], str]) -> JobZip:
    """A ZIP of the cards the job produced (rendered or reused from cache) that
    still match what they would print now, as a spooled temp file.

    A card goes stale when a mark, remark or setting changes after the run, and
    its cache row can be overwritten by a later render (one row per student and
    template version, e.g. the super-admin's render with drafts). Such cards
    are left out and listed in CARDS_NOT_INCLUDED.txt, so an outdated card is
    never handed out as final. Cards are read one at a time, so a large class
    never holds every PDF in memory at once.
    """
    ids = [r["pdf_id"] for r in (job.results or []) if r.get("pdf_id") and r["status"] in ("rendered", "cached")]
    template = db.get(PdfTemplate, job.template_id)
    meta = {row.id: row for row in db.execute(
        select(PdfCache.id, PdfCache.student_id, PdfCache.kind, PdfCache.template_version, PdfCache.source_hash)
        .where(PdfCache.id.in_(ids))
    ).all()} if ids else {}
    students = {s.id: s for s in db.scalars(
        select(Student).where(Student.id.in_(sorted({m.student_id for m in meta.values()})))
    )} if meta else {}
    fresh = current_hashes(db, template, sorted(students), job.include_drafts) if template and students else {}

    spool = tempfile.SpooledTemporaryFile(max_size=16 * 1024 * 1024)
    used: set[str] = set()
    left_out: list[str] = []
    with zipfile.ZipFile(spool, "w", zipfile.ZIP_DEFLATED) as zf:
        for pdf_id in ids:
            m = meta.get(pdf_id)
            if m is None:               # removed since the run (student or template deleted)
                continue
            student = students.get(m.student_id)
            if (template is None or m.template_version != template.version
                    or m.source_hash is None or fresh.get(m.student_id) != m.source_hash):
                who = student.name if student else f"Student {m.student_id}"
                left_out.append(f"{who} (roll {student.roll_no})" if student and student.roll_no else who)
                continue
            # Only this card's blob is loaded, and only for cards that go in.
            data = db.scalar(select(PdfCache.data).where(PdfCache.id == pdf_id))
            if data is None:
                continue
            name = filename_for(m.kind.value, student, m.student_id)
            if name in used:
                name = name.replace(".pdf", f"_{m.student_id}.pdf")
            used.add(name)
            zf.writestr(name, data)
        if left_out:
            zf.writestr(LEFT_OUT_NOTE, (
                "These cards changed after this run made them (marks, remarks, attendance or settings),\n"
                "so they are not in this ZIP. Generate them again, then download a new ZIP.\n\n"
                + "".join(f"- {who}\n" for who in left_out)
            ))
    spool.seek(0)
    return JobZip(spool=spool, included=len(used), outdated=len(left_out))
