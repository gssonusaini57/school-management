"""Background bulk rendering: lifecycle, ZIP, one run per class, stale runners, cancel, permissions."""
import io
import zipfile
from datetime import datetime, timedelta

import pytest

from app.models.pdf_render_job import PdfRenderJob, RenderJobStatus
from app.services import render_jobs

from .conftest import auth
from .test_report_cards import eighth  # noqa: F401  (shared class fixture)


@pytest.fixture()
def inline_runner(monkeypatch, session_factory):
    """Run jobs synchronously in-process instead of spawning a runner."""
    monkeypatch.setattr(render_jobs, "start_job", lambda job_id: render_jobs.run_job(job_id, session_factory))
    monkeypatch.setattr("app.pdf.render_or_cache.render_pdf", lambda kind, payload: b"%PDF-1.4 " + payload["student"]["name"]["en"].encode())


def test_job_renders_class_and_zips_cards(client, db, eighth, inline_runner):
    t = eighth["t"]
    r = client.post(f"/api/pdf/templates/{t.id}/render-jobs", json={}, headers=auth("staff", ["8th"]))
    assert r.status_code == 202, r.text
    job = client.get(f"/api/pdf/render-jobs/{r.json()['id']}", headers=auth("staff", ["8th"])).json()
    assert (job["status"], job["total"], job["done_count"], job["error_count"]) == ("done", 3, 3, 1)
    assert [x["status"] for x in job["results"]] == ["rendered", "rendered", "error"]
    z = client.get(f"/api/pdf/render-jobs/{job['id']}/zip", headers=auth("admin"))
    names = sorted(zipfile.ZipFile(io.BytesIO(z.content)).namelist())
    assert names == ["report-card_8th_1_Asha-Kaur.pdf", "report-card_8th_2_Ravi-Kumar.pdf"]
    assert 'filename="report-cards_8th_Term-I.zip"' in z.headers["content-disposition"]
    # A second run reuses every finished card from the cache.
    again = client.post(f"/api/pdf/templates/{t.id}/render-jobs", json={"student_ids": [eighth["s1"].id]},
                        headers=auth("admin")).json()
    assert client.get(f"/api/pdf/render-jobs/{again['id']}", headers=auth("admin")).json()["results"][0]["status"] == "cached"


def test_one_active_run_per_class(client, db, eighth, inline_runner):
    t = eighth["t"]
    db.add(PdfRenderJob(template_id=t.id, template_version=t.version, requested_by="x", status=RenderJobStatus.running,
                        student_ids=[1], total=1, heartbeat_at=datetime.utcnow()))
    db.commit()
    assert client.post(f"/api/pdf/templates/{t.id}/render-jobs", json={}, headers=auth("admin")).status_code == 409


def test_stopped_runner_is_marked_failed_and_a_new_run_is_allowed(client, db, eighth, inline_runner):
    t = eighth["t"]
    stale = PdfRenderJob(template_id=t.id, template_version=t.version, requested_by="x", status=RenderJobStatus.running,
                         student_ids=[1], total=1, heartbeat_at=datetime.utcnow() - timedelta(minutes=5))
    db.add(stale)
    db.commit()
    body = client.get(f"/api/pdf/render-jobs/{stale.id}", headers=auth("admin")).json()
    assert body["status"] == "failed" and "stopped" in body["error"]
    assert client.post(f"/api/pdf/templates/{t.id}/render-jobs", json={}, headers=auth("admin")).status_code == 202


def test_cancel_stops_after_the_current_student(db, eighth, session_factory, monkeypatch):
    t = eighth["t"]
    job = render_jobs.create_job(db, t, [eighth["s1"].id, eighth["s2"].id], include_drafts=None, force=False, actor="x")

    def render_then_cancel(kind, payload):
        s = session_factory()
        s.get(PdfRenderJob, job.id).status = RenderJobStatus.cancelled
        s.commit()
        s.close()
        return b"%PDF-1.4"

    monkeypatch.setattr("app.pdf.render_or_cache.render_pdf", render_then_cancel)
    render_jobs.run_job(job.id, session_factory)
    db.expire_all()
    done = db.get(PdfRenderJob, job.id)
    assert done.status == RenderJobStatus.cancelled and done.done_count == 1


def test_permissions_and_sync_limit(client, db, eighth, inline_runner):
    t = eighth["t"]
    url = f"/api/pdf/templates/{t.id}/render-jobs"
    assert client.post(url, json={}, headers=auth("staff", ["5th"])).status_code == 403
    assert client.post(url, json={"include_drafts": True}, headers=auth("admin")).status_code == 403
    job = client.post(url, json={}, headers=auth("admin")).json()
    assert client.get(f"/api/pdf/render-jobs/{job['id']}", headers=auth("staff", ["5th"])).status_code == 403
    r = client.post(f"/api/pdf/templates/{t.id}/render", json={"student_ids": list(range(1, 42))}, headers=auth("admin"))
    assert r.status_code == 413
