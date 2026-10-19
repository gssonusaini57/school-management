"""Server fixes from the backend review of report cards: per-student data saves,
who may choose drafts / force a re-render, and ZIPs of outdated cards."""
import io
import zipfile
from datetime import date

from app.models.pdf_render_job import PdfRenderJob
from app.models.pdf_template import PdfStudentData

from .conftest import auth
from .factories import attendance_day
from .test_render_jobs import inline_runner  # noqa: F401  (runs jobs in-process, fake renderer)
from .test_report_cards import eighth  # noqa: F401  (shared class fixture)

STAFF = auth("staff", ["8th"])


def _put(client, t, entries, headers=None):
    body = {"entries": [{"student_id": sid, "data": data} for sid, data in entries]}
    return client.put(f"/api/pdf/templates/{t.id}/student-data", json=body, headers=headers or auth("admin"))


def _roster(client, t):
    body = client.get(f"/api/pdf/templates/{t.id}/roster", headers=auth("admin")).json()
    return {r["id"]: r for r in body["students"]}


def _render(client, t, sid, headers, **extra):
    r = client.post(f"/api/pdf/templates/{t.id}/render", json={"student_ids": [sid], **extra}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["results"][0]


def _zip(client, job_id):
    z = client.get(f"/api/pdf/render-jobs/{job_id}/zip", headers=auth("admin"))
    assert z.status_code == 200, z.text
    return z, zipfile.ZipFile(io.BytesIO(z.content))


# ── PUT student-data ─────────────────────────────────────────────────────
def test_a_day_override_that_fell_behind_attendance_never_blocks_a_remark(client, db, eighth):
    """Mid-term an admin overrides working days; days marked later push the computed
    days present past it. Teachers' remark saves must still go through."""
    t, s1, s2 = eighth["t"], eighth["s1"], eighth["s2"]
    assert _put(client, t, [(s1.id, {"workingDays": 2})]).status_code == 200      # 1.5 present: valid
    attendance_day(db, "8th", date(2026, 5, 6), {s1.id: "P", s2.id: "P"})         # now 2.5 present
    db.commit()
    remarks = [(sid, {"remarks": {"en": "Good work"}}) for sid in (s1.id, s2.id)]
    assert _put(client, t, remarks, headers=STAFF).status_code == 200
    assert _put(client, t, [(s1.id, {"remarks": {"en": "Very good"}})]).status_code == 200
    # Changing the day counts is still held to the computed ones, and names the student.
    r = _put(client, t, [(s1.id, {"workingDays": 2})])
    assert r.status_code == 422 and r.json()["detail"].startswith("Asha Kaur: ")
    assert _put(client, t, [(s1.id, {"workingDays": None})]).status_code == 200    # clearing it is fine
    db.expire_all()
    stored = db.query(PdfStudentData).filter(PdfStudentData.student_id == s1.id).one().data
    assert stored["workingDays"] is None and stored["remarks"]["en"] == "Very good"


def test_a_row_that_fails_validation_is_named(client, db, eighth):
    """One bad stored row refuses the whole save, so the error says whose row it is."""
    t, s1, s2 = eighth["t"], eighth["s1"], eighth["s2"]
    db.add(PdfStudentData(kind=t.kind, student_id=s1.id, session=t.session, term=t.term,
                          term_key=t.term or "", data={"house": "Guru Nanak"}, updated_by="t"))
    db.commit()
    remarks = [(sid, {"remarks": {"en": "Good work"}}) for sid in (s2.id, s1.id)]
    r = _put(client, t, remarks, headers=STAFF)
    assert r.status_code == 422 and r.json()["detail"].startswith("Asha Kaur: house must be one of")
    assert db.query(PdfStudentData).filter(PdfStudentData.student_id == s2.id).count() == 0   # nothing saved
    r = _put(client, t, [(s2.id, {"rank": 0})])
    assert r.json()["detail"] == "Ravi Kumar: rank: Input should be greater than or equal to 1"


# ── who chooses drafts and forces a re-render ────────────────────────────
def test_only_the_super_admin_can_leave_drafts_out(client, db, eighth, inline_runner):
    """On a template that prints drafts, include_drafts=false from anyone else is
    ignored: it can't replace the super-admin's card with one without the drafts."""
    t, s1 = eighth["t"], eighth["s1"]
    t.data = {**t.data, "includeDrafts": True}
    db.commit()
    first = _render(client, t, s1.id, auth("super_admin"))
    assert first["status"] == "rendered"
    for headers in (STAFF, auth("admin")):
        assert _render(client, t, s1.id, headers, include_drafts=False) == {**first, "status": "cached"}
    row = _roster(client, t)[s1.id]
    assert (row["cached_pdf_id"], row["stale_pdf_id"]) == (first["pdf_id"], None)
    job = client.post(f"/api/pdf/templates/{t.id}/render-jobs", json={"include_drafts": False}, headers=auth("admin"))
    assert job.status_code == 202
    assert db.get(PdfRenderJob, job.json()["id"]).include_drafts is None
    assert _render(client, t, s1.id, auth("super_admin"), include_drafts=False)["status"] == "rendered"


def test_force_re_render_is_admin_only(client, db, eighth, inline_runner):
    t, s1 = eighth["t"], eighth["s1"]
    assert _render(client, t, s1.id, STAFF)["status"] == "rendered"
    assert _render(client, t, s1.id, STAFF, force=True)["status"] == "cached"
    assert _render(client, t, s1.id, auth("admin"), force=True)["status"] == "rendered"
    r = client.post(f"/api/pdf/templates/{t.id}/render-jobs", json={"force": True}, headers=STAFF)
    assert r.status_code == 202
    assert db.get(PdfRenderJob, r.json()["id"]).force is False
    job = client.get(f"/api/pdf/render-jobs/{r.json()['id']}", headers=STAFF).json()
    assert [x["status"] for x in job["results"]] == ["cached", "rendered", "error"]


# ── ZIP of a finished run ────────────────────────────────────────────────
def test_the_zip_leaves_out_cards_that_changed_after_the_run(client, db, eighth, inline_runner):
    t, s1 = eighth["t"], eighth["s1"]
    job = client.post(f"/api/pdf/templates/{t.id}/render-jobs", json={}, headers=auth("admin")).json()
    z, zf = _zip(client, job["id"])
    assert sorted(zf.namelist()) == ["report-card_8th_1_Asha-Kaur.pdf", "report-card_8th_2_Ravi-Kumar.pdf"]
    assert (z.headers["x-cards-included"], z.headers["x-cards-outdated"]) == ("2", "0")
    # A remark fixed after the run: Asha's card from the run is out of date.
    assert _put(client, t, [(s1.id, {"remarks": {"en": "Fixed remark"}})], headers=STAFF).status_code == 200
    z, zf = _zip(client, job["id"])
    assert sorted(zf.namelist()) == ["CARDS_NOT_INCLUDED.txt", "report-card_8th_2_Ravi-Kumar.pdf"]
    assert (z.headers["x-cards-included"], z.headers["x-cards-outdated"]) == ("1", "1")
    assert "- Asha Kaur (roll 1)" in zf.read("CARDS_NOT_INCLUDED.txt").decode()


def test_the_zip_never_holds_a_later_render_or_an_older_template_version(client, db, eighth, inline_runner):
    t, s1 = eighth["t"], eighth["s1"]
    started = client.post(f"/api/pdf/templates/{t.id}/render-jobs", json={}, headers=auth("admin")).json()
    # The start returns the run as queued; its results come from polling.
    job = client.get(f"/api/pdf/render-jobs/{started['id']}", headers=auth("admin")).json()
    # The super-admin's render with drafts overwrites Asha's cache row from the run.
    with_drafts = _render(client, t, s1.id, auth("super_admin"), include_drafts=True)
    assert with_drafts["status"] == "rendered" and with_drafts["pdf_id"] == job["results"][0]["pdf_id"]
    z, zf = _zip(client, job["id"])
    assert sorted(zf.namelist()) == ["CARDS_NOT_INCLUDED.txt", "report-card_8th_2_Ravi-Kumar.pdf"]
    # Editing the template re-renders every card: nothing from the run is current.
    assert client.patch(f"/api/pdf/templates/{t.id}", json={"layout": "summary"},
                        headers=auth("admin")).status_code == 200
    z, zf = _zip(client, job["id"])
    assert zf.namelist() == ["CARDS_NOT_INCLUDED.txt"]
    assert (z.headers["x-cards-included"], z.headers["x-cards-outdated"]) == ("0", "2")
