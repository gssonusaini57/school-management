"""Backend fixes from the final review of the Results module: card state across
template versions, admit cards without a date of birth, unscoped legacy
templates, the render-run start lock, printed percentages and Punjabi on the
card, rows the previous release can read, and the session-defaults endpoint."""
from datetime import date, datetime, timedelta

import pytest
from pydantic import BaseModel
from sqlalchemy import event, select

from app.models.pdf_render_job import PdfRenderJob, RenderJobStatus
from app.models.pdf_template import PdfStudentData, PdfTemplate
from app.pdf.format import format_pct
from app.pdf.render_or_cache import report_card_payload
from app.services import render_jobs
from app.services.report_cards import gather_class_inputs

from .conftest import auth
from .factories import academic_session, cached_pdf, report_card_template
from .test_render_jobs import inline_runner  # noqa: F401  (runs jobs in-process, fake renderer)
from .test_report_cards import eighth  # noqa: F401  (shared class fixture)

PSEB_DATA = {"schoolCode": "0098351", "centre": {"code": "1", "schoolCode": "2", "district": "Patiala", "set": "A",
                                                 "name": {"en": "Centre", "pa": "ਕੇਂਦਰ"}},
             "examTime": {"en": "10:00", "pa": "10:00"},
             "dateSheet": [{"subCode": "001", "subject": {"en": "Punjabi", "pa": "ਪੰਜਾਬੀ"},
                            "theoryDate": "01-03-2027", "practical": "No"}]}


def _roster(client, template_id):
    body = client.get(f"/api/pdf/templates/{template_id}/roster", headers=auth("admin")).json()
    return {r["id"]: r for r in body["students"]}


def _render(client, template_id, sid):
    r = client.post(f"/api/pdf/templates/{template_id}/render", json={"student_ids": [sid]}, headers=auth("admin"))
    assert r.status_code == 200, r.text
    return r.json()["results"][0]


@pytest.fixture()
def fake_pdf(monkeypatch):
    monkeypatch.setattr("app.pdf.render_or_cache.render_pdf", lambda kind, payload: b"%PDF-1.4 fake")


# ── F33: a new template version doesn't hide the cards already made ─────
def test_cards_of_an_earlier_template_version_read_needs_update_and_stay_downloadable(client, db, eighth, fake_pdf):
    t, s1 = eighth["t"], eighth["s1"]
    first = _render(client, t.id, s1.id)
    assert first["status"] == "rendered" and _roster(client, t.id)[s1.id]["cached_pdf_id"] == first["pdf_id"]
    # Fixing the principal's name saves a new version of the card settings.
    r = client.patch(f"/api/pdf/templates/{t.id}", json={"data": {"signatures": {"principal": "Dr. New Name"}}},
                     headers=auth("admin"))
    assert r.status_code == 200 and r.json()["version"] == 2
    row = _roster(client, t.id)[s1.id]
    assert row["cached_pdf_id"] is None and row["stale_pdf_id"] == first["pdf_id"]
    assert client.get(f"/api/pdf/cache/{first['pdf_id']}", headers=auth("admin")).status_code == 200
    again = _render(client, t.id, s1.id)
    assert again["status"] == "rendered" and again["pdf_id"] != first["pdf_id"]
    row = _roster(client, t.id)[s1.id]
    assert row["cached_pdf_id"] == again["pdf_id"] and row["stale_pdf_id"] is None


# ── F34: an admit card from before the DOB check is never handed out ─────
def test_an_admit_card_that_printed_an_invented_date_of_birth_is_never_offered(client, db, eighth):
    s2 = eighth["s2"]                                            # no date of birth on record
    r = client.post("/api/pdf/templates", json={"kind": "pseb-admit-card", "class_name": "8th",
                                                "session": "2026-27", "data": PSEB_DATA}, headers=auth("admin"))
    tid = r.json()["id"]
    assert client.put(f"/api/pdf/templates/{tid}/student-data", headers=auth("admin"), json={
        "entries": [{"student_id": s2.id, "data": {"rollNo": "102", "regNo": "R2"}}]}).status_code == 200
    old = cached_pdf(db, db.get(PdfTemplate, tid), s2.id)        # made by the release that printed 2010-01-01
    db.commit()
    row = _roster(client, tid)[s2.id]
    assert "date of birth" in row["error"] and row["stale_pdf_id"] is None and row["cached_pdf_id"] is None
    r = client.get(f"/api/pdf/cache/{old.id}", headers=auth("admin"))
    assert r.status_code == 409 and "date of birth" in r.json()["detail"]
    # Once the date of birth is on record, that card is just out of date.
    s2.dob = date(2013, 1, 15)
    db.commit()
    assert _roster(client, tid)[s2.id]["stale_pdf_id"] == old.id
    assert client.get(f"/api/pdf/cache/{old.id}", headers=auth("admin")).status_code == 200


# ── F35: a legacy template with an unknown term label gets its scope first ──
def test_a_template_whose_scope_cant_be_told_is_scoped_before_another_is_created(client, db):
    academic_session(db, "2026-27")
    legacy = report_card_template(db, "9th", term="Half Yearly")
    db.commit()
    new = {"kind": "report-card", "class_name": "9th", "session": "2026-27", "scope": "term1", "data": {}}
    r = client.post("/api/pdf/templates", json=new, headers=auth("admin"))
    assert r.status_code == 409 and '"Half Yearly"' in r.json()["detail"] and "Set its scope" in r.json()["detail"]
    bulk = {"kind": "report-card", "session": "2026-27", "scope": "term2", "class_names": ["9th", "10th"]}
    body = client.post("/api/pdf/templates/bulk-create", json=bulk, headers=auth("admin")).json()
    assert [c["class_name"] for c in body["created"]] == ["10th"]
    assert body["skipped"] == [{"class_name": "9th", "reason": 'set the scope of "Half Yearly" instead'}]
    assert client.patch(f"/api/pdf/templates/{legacy.id}", json={"scope": "term1"},
                        headers=auth("admin")).status_code == 200
    assert client.post("/api/pdf/templates", json={**new, "scope": "term2"}, headers=auth("admin")).status_code == 201


# ── F36: the start lock opens its transaction (MySQL REPEATABLE READ) ─────
def test_a_run_starts_under_a_lock_taken_first_in_a_fresh_transaction(client, db, engine, eighth, inline_runner):
    t = eighth["t"]
    stale = PdfRenderJob(template_id=t.id, template_version=t.version, requested_by="x",
                         status=RenderJobStatus.running, student_ids=[1], total=1,
                         heartbeat_at=datetime.utcnow() - timedelta(minutes=5))
    db.add(stale)
    db.commit()
    seen: list[tuple[str, str]] = []

    def on_begin(conn):
        seen.append(("BEGIN", ""))

    def on_commit(conn):
        seen.append(("COMMIT", ""))

    def on_rollback(conn):
        seen.append(("ROLLBACK", ""))

    def on_execute(conn, cursor, statement, parameters, context, executemany):
        stmt = getattr(getattr(context, "compiled", None), "statement", None)
        locked = getattr(stmt, "_for_update_arg", None) is not None   # SQLite drops FOR UPDATE from the SQL
        seen.append(("LOCK" if locked else statement.split(None, 1)[0].upper(), statement))

    hooks = [("begin", on_begin), ("commit", on_commit), ("rollback", on_rollback),
             ("before_cursor_execute", on_execute)]
    for name, fn in hooks:
        event.listen(engine, name, fn)
    try:
        r = client.post(f"/api/pdf/templates/{t.id}/render-jobs", json={}, headers=auth("admin"))
    finally:
        for name, fn in hooks:
            event.remove(engine, name, fn)
    assert r.status_code == 202, r.text
    kinds = [k for k, _ in seen]
    i = kinds.index("LOCK")
    assert kinds[i - 1] == "BEGIN"                     # nothing read before the lock in its transaction
    j = kinds.index("COMMIT", i)
    under_lock = seen[i + 1:j]
    assert not any(k in ("BEGIN", "ROLLBACK") for k, _ in under_lock)        # no sweep commit drops the lock
    assert any(k == "INSERT" and "pdf_render_jobs" in s for k, s in under_lock)   # the new run is written under it
    db.expire_all()
    assert db.get(PdfRenderJob, stale.id).status == RenderJobStatus.failed     # swept before the lock


def test_lock_holders_check_runs_without_writing(db, eighth):
    t = eighth["t"]
    stale = PdfRenderJob(template_id=t.id, template_version=t.version, requested_by="x",
                         status=RenderJobStatus.queued, student_ids=[1], total=1,
                         created_at=datetime.utcnow() - timedelta(minutes=5))
    other = report_card_template(db, "9th")                       # another class, its run still going
    live = PdfRenderJob(template_id=other.id, template_version=1, requested_by="y",
                        status=RenderJobStatus.running, student_ids=[1], total=1, heartbeat_at=datetime.utcnow())
    db.add_all([stale, live])
    db.commit()
    assert render_jobs.active_job(db, t.id, sweep=False) is None
    assert render_jobs.active_job_count(db, sweep=False) == 1
    db.expire_all()
    assert db.get(PdfRenderJob, stale.id).status == RenderJobStatus.queued     # left for the sweep
    render_jobs.sweep_active(db)
    db.expire_all()
    assert db.get(PdfRenderJob, stale.id).status == RenderJobStatus.failed
    assert db.get(PdfRenderJob, live.id).status == RenderJobStatus.running


# ── F48 + F49: what the card prints ──────────────────────────────────────
@pytest.mark.parametrize("value,places,printed", [
    (80, 2, "80%"), (66.666, 2, "66.67%"), (87.5, 2, "87.5%"), (100.0, 1, "100%"), (75.04, 1, "75%"),
    (37.5, 1, "37.5%"), (0, 2, "0%"), (50, 0, "50%"), (None, 2, "—"),
])
def test_percentages_print_without_trailing_zeros(value, places, printed):
    assert format_pct(value, places) == printed


def test_the_card_prints_whole_percentages_and_its_punjabi(client, db, eighth):
    t, s1 = eighth["t"], eighth["s1"]          # rank 1 of 3; 1.5 of 2 working days = 75 %
    r = client.get(f"/api/pdf/templates/{t.id}/preview", params={"student_id": s1.id, "format": "html"},
                   headers=auth("admin"))
    assert r.status_code == 200, r.text
    html = r.text
    assert "75%" in html and "75.0%" not in html
    assert '<span class="gurmukhi" lang="pa">ਸਾਲ</span>' in html
    assert '<span class="pa" lang="pa">3 ਵਿੱਚੋਂ 1</span>' in html
    assert "2 ਕੰਮਕਾਜੀ ਦਿਨਾਂ ਵਿੱਚੋਂ 1.5</span>" in html
    assert "ਵਿਦਿਆਰਥੀ ਦੀ ਫੋਟੋ</span>" in html                         # the photo placeholder, no photo on file
    assert 'below 41 / <span class="gurmukhi" lang="pa">41 ਤੋਂ ਘੱਟ</span>' in html


# ── F53: rows the previous release (54db9cd) can still read ──────────────
def test_an_english_only_remark_is_stored_so_the_previous_release_can_read_it(client, db, eighth):
    t, s1 = eighth["t"], eighth["s1"]
    r = client.put(f"/api/pdf/templates/{t.id}/student-data", headers=auth("staff", ["8th"]),
                   json={"entries": [{"student_id": s1.id, "data": {"remarks": {"en": "Very good"}}}]})
    assert r.status_code == 200 and r.json()[0]["data"]["remarks"] == {"en": "Very good", "pa": ""}
    stored = db.scalar(select(PdfStudentData).where(PdfStudentData.student_id == s1.id)).data

    class Bilingual(BaseModel):                # app/pdf/schemas.py at 54db9cd
        en: str
        pa: str

    Bilingual(**stored["remarks"])
    db.expire_all()
    summary = report_card_payload(gather_class_inputs(db, db.get(PdfTemplate, t.id)), s1.id)[0]["summary"]
    assert summary["remarks"] == {"en": "Very good", "pa": None}    # "" reads back as no Punjabi line


# ── K6: the Sessions page asks the server for the default calendar ───────
def test_session_defaults_come_from_the_server(client):
    url = "/api/sessions/defaults"
    r = client.get(url, params={"session": " 2027-28 "}, headers=auth("super_admin"))
    assert r.status_code == 200, r.text
    assert r.json() == {"session": "2027-28", "starts_on": "2027-04-01", "ends_on": "2028-03-31",
                        "term1_start": "2027-04-01", "term1_end": "2027-09-30",
                        "term2_start": "2027-10-01", "term2_end": "2028-03-31"}
    bad = client.get(url, params={"session": "2027-29"}, headers=auth("super_admin"))
    assert bad.status_code == 422 and "2026-27" in bad.json()["detail"]
    assert client.get(url, params={"session": "2027-28"}, headers=auth("admin")).status_code == 403
    assert client.get(url, headers=auth("super_admin")).status_code == 422          # session is required
