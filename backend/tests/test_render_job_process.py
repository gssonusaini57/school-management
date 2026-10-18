"""The real detached runner: `start_job` spawns `python -m app.jobs.render_job`,
which reads the job from the database named by DATABASE_URL and finishes it."""
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models.pdf_render_job import PdfRenderJob, RenderJobStatus
from app.services import render_jobs

from .factories import academic_session, report_card_template, student


def test_spawned_runner_completes_a_job(tmp_path, monkeypatch):
    url = f"sqlite+pysqlite:///{tmp_path}/runner.db"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    S = sessionmaker(bind=engine, expire_on_commit=False)
    with S() as db:
        academic_session(db)
        s = student(db, name="Runner Child")
        t = report_card_template(db, term="Term I")
        t.scope = "term1"
        db.commit()
        job = render_jobs.create_job(db, t, [s.id], include_drafts=None, force=False, actor="test")
        job_id = job.id

    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    render_jobs.start_job(job_id)

    deadline = time.time() + 45
    status = None
    while time.time() < deadline:
        with S() as db:
            row = db.get(PdfRenderJob, job_id)
            status = row.status
            if status not in (RenderJobStatus.queued, RenderJobStatus.running):
                break
        time.sleep(0.3)
    log = (tmp_path / "render-jobs.log").read_text() if (tmp_path / "render-jobs.log").exists() else ""
    assert status == RenderJobStatus.done, log[-2000:]
    with S() as db:
        row = db.get(PdfRenderJob, job_id)
        # The student has no marks, so the card is an error, but the run itself completed.
        assert row.done_count == 1 and row.results[0]["status"] == "error"
        assert row.worker_pid and row.started_at and row.finished_at
