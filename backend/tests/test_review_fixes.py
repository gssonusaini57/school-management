"""Fixes from the adversarial review of the Results-module backend."""
import io
from datetime import date, datetime, timedelta
from types import SimpleNamespace as NS

import pytest
from PIL import Image
from sqlalchemy.exc import IntegrityError

from app.models.class_subject import SubjectCategory
from app.models.document import DocumentKind, StudentDocument
from app.models.marks import Marks
from app.models.marks_batch import MarksBatch, MarksBatchStatus
from app.models.pdf_render_job import PdfRenderJob, RenderJobStatus
from app.models.pdf_template import PdfCache, PdfTemplate, TemplateKind
from app.pdf import render_or_cache as roc
from app.pdf.render_or_cache import render_students, report_card_payload
from app.services import render_jobs
from app.services.report_cards import gather_class_inputs, photo_data_uri, safe_photo_jpeg
from app.services.results import aggregate_class_results

from .conftest import auth
from .factories import academic_session, batch, report_card_template, student, subject
from .test_class_subject_renames import maths  # noqa: F401
from .test_report_cards import eighth  # noqa: F401

SVG = (b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
       b'<image href="file:///etc/passwd" width="10" height="10"/></svg>')


def _png(w=900, h=1200):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (200, 30, 30)).save(buf, "PNG")
    return buf.getvalue()


def _payload(db, t, sid):
    return report_card_payload(gather_class_inputs(db, t), sid)[0]


# ── photos and the PDF renderer ──────────────────────────────────────────
def test_photo_upload_accepts_only_real_pictures(client, eighth):
    s1 = eighth["s1"]
    url = f"/api/students/{s1.id}/documents/photo"
    r = client.post(url, files={"file": ("x.svg", SVG, "image/svg+xml")}, headers=auth("staff", ["8th"]))
    assert r.status_code == 415
    r = client.post(url, files={"file": ("x.jpg", SVG, "image/jpeg")}, headers=auth("staff", ["8th"]))
    assert r.status_code == 415                                   # the content decides, not the label
    assert client.post(url, files={"file": ("p.png", _png(), "image/png")},
                       headers=auth("staff", ["8th"])).status_code == 204


def test_embedded_photo_is_a_small_reencoded_jpeg(db, eighth):
    s1 = eighth["s1"]
    jpeg = safe_photo_jpeg(_png())
    assert jpeg[:3] == b"\xff\xd8\xff"
    assert max(Image.open(io.BytesIO(jpeg)).size) <= 360
    assert safe_photo_jpeg(SVG) is None
    doc = StudentDocument(student_id=s1.id, kind=DocumentKind.photo, mime_type="image/svg+xml",
                          byte_size=len(SVG), data=SVG)
    db.add(doc)
    db.commit()
    assert photo_data_uri(db, doc.id) is None                    # an SVG never reaches the renderer


def test_url_fetcher_refuses_files_and_hosts_outside_the_allow_list():
    from app.pdf.render import safe_url_fetcher
    for url in ("file:///etc/passwd", "file:///opt/school-management/.env", "http://169.254.169.254/latest",
                "https://example.com/x.css", "ftp://fonts.googleapis.com/x"):
        with pytest.raises(ValueError):
            safe_url_fetcher(url)


def test_url_fetcher_allows_assets_and_data_when_weasyprint_is_available():
    try:
        import weasyprint  # noqa: F401
    except Exception:
        pytest.skip("WeasyPrint needs Pango (set DYLD_FALLBACK_LIBRARY_PATH on macOS)")
    from app.pdf.render import PDF_DIR, safe_url_fetcher
    res = safe_url_fetcher((PDF_DIR / "assets" / "crest-512.png").as_uri())
    assert res
    res = safe_url_fetcher("data:text/plain;base64,aGk=")
    assert (res.get("string") or res["file_obj"].read()) == b"hi"


# ── per-student data hygiene ─────────────────────────────────────────────
def test_attendance_overrides_never_contradict_each_other(client, db, eighth):
    t, s1 = eighth["t"], eighth["s1"]
    url = f"/api/pdf/templates/{t.id}/student-data"
    put = lambda data: client.put(url, json={"entries": [{"student_id": s1.id, "data": data}]}, headers=auth("admin"))
    assert put({"workingDays": 100, "daysPresent": 60}).status_code == 200
    db.expire_all()
    s = _payload(db, db.get(PdfTemplate, t.id), s1.id)["summary"]
    assert (s["attendancePct"], s["workingDays"], s["daysPresent"]) == (60.0, 100, 60)
    assert put({"workingDays": None, "daysPresent": None, "attendancePct": 95}).status_code == 200
    db.expire_all()
    s = _payload(db, db.get(PdfTemplate, t.id), s1.id)["summary"]
    assert (s["attendancePct"], s["workingDays"], s["daysPresent"]) == (95, None, None)
    assert put({"workingDays": 10, "daysPresent": 12}).status_code == 422


def test_blank_inputs_mean_not_set_and_house_is_one_of_four(client, db, eighth):
    t, s1 = eighth["t"], eighth["s1"]
    t.data = {**(t.data or {}), "remarksDefault": {"en": "Keep it up", "pa": None}}
    db.commit()
    url = f"/api/pdf/templates/{t.id}/student-data"
    put = lambda data, role="staff": client.put(url, json={"entries": [{"student_id": s1.id, "data": data}]},
                                                headers=auth(role, ["8th"]))
    assert put({"remarks": {"en": " ", "pa": ""}, "house": ""}).status_code == 200
    db.expire_all()
    p = _payload(db, db.get(PdfTemplate, t.id), s1.id)
    assert p["summary"]["remarks"] == {"en": "Keep it up", "pa": None}   # the default, not an empty block
    assert put({"remarks": {"en": "", "pa": "ਸਿਰਫ਼ ਪੰਜਾਬੀ"}}).status_code == 422
    assert put({"remarks": {"en": "x" * 601}}).status_code == 422
    assert put({"house": "tagore"}).json()[0]["data"]["house"] == "Tagore"
    assert put({"house": "Mars"}).status_code == 422
    assert put({"promotion": "", "admissionNo": "  "}, role="admin").json()[0]["data"]["promotion"] is None


def test_rank_is_marked_provisional_until_the_class_is_complete(db, eighth):
    t, s1 = eighth["t"], eighth["s1"]
    s = _payload(db, t, s1.id)["summary"]
    assert s["rank"] == 1 and s["rankProvisional"] is True              # classmates' marks are still missing


# ── one promotion rule for screen and card ───────────────────────────────
@pytest.fixture()
def ninth_annual(db):
    academic_session(db, "2026-27")
    a = student(db, name="Annual Kid", class_name="9th", roll_no="1")
    subject(db, "9th", "Hindi", [("P.T. First", 50, 1), ("P.T. Third", 50, 2)])
    for exam in ("P.T. First", "P.T. Third"):
        batch(db, "9th", "Hindi", exam, max_marks=50, status=MarksBatchStatus.submitted, marks={a.id: 30})  # 60 %
    db.commit()
    return a


def test_templates_store_no_rule_by_default_and_results_follow_the_template_rule(client, db, ninth_annual):
    q = {"class": "9th", "session": "2026-27", "scope": "annual"}
    assert client.get("/api/marks/results", params=q, headers=auth("admin")).json()["students"][0]["promotion"] == "Promoted"
    r = client.post("/api/pdf/templates", json={"kind": "report-card", "class_name": "9th", "session": "2026-27",
                                                "scope": "annual", "data": {}}, headers=auth("admin"))
    assert r.json()["data"]["promotionRule"] is None                     # school default, not a frozen copy
    tid = r.json()["id"]
    client.patch(f"/api/pdf/templates/{tid}", json={"data": {"promotionRule": {"passPct": 90, "conditionalMaxFails": 0}}},
                 headers=auth("admin"))
    body = client.get("/api/marks/results", params=q, headers=auth("admin")).json()
    assert body["students"][0]["promotion"] == "Detained"
    db.expire_all()
    p = _payload(db, db.get(PdfTemplate, tid), ninth_annual.id)
    assert p["summary"]["promotion"] == "Detained"                       # the card agrees with the screen


# ── render robustness ────────────────────────────────────────────────────
def test_store_recovers_from_a_concurrent_insert(db, eighth, session_factory, monkeypatch):
    t, s1 = eighth["t"], eighth["s1"]
    other = session_factory()
    other.add(PdfCache(kind=t.kind, student_id=s1.id, template_id=t.id, template_version=t.version,
                       mime_type="application/pdf", byte_size=1, data=b"x", created_by="other"))
    other.commit()
    other.close()
    real_scalar = db.scalar
    calls = {"n": 0}

    def first_lookup_misses(stmt, *a, **k):
        calls["n"] += 1
        return None if calls["n"] == 1 else real_scalar(stmt, *a, **k)

    monkeypatch.setattr(db, "scalar", first_lookup_misses)
    row = roc._store(db, t, s1.id, b"%PDF-new", "hash", "me")
    db.commit()
    db.expire_all()
    rows = db.query(PdfCache).all()
    assert len(rows) == 1 and rows[0].created_by == "me" and rows[0].data == b"%PDF-new"


def test_one_failing_student_does_not_abort_the_batch(db, eighth, monkeypatch):
    monkeypatch.setattr("app.pdf.render_or_cache.render_pdf", lambda kind, payload: b"%PDF-1.4 fake")
    t, s1, s2 = eighth["t"], eighth["s1"], eighth["s2"]
    original = roc._render_report_card

    def boom(db_, inputs, sid, **kw):
        if sid == s1.id:
            raise RuntimeError("kaboom")
        return original(db_, inputs, sid, **kw)

    monkeypatch.setattr(roc, "_render_report_card", boom)
    results = render_students(db, template=t, student_ids=[s1.id, s2.id], actor="t")
    assert results[0]["status"] == "error" and "kaboom" in results[0]["error"]
    assert results[1]["status"] == "rendered"


def test_render_jobs_are_capped_across_classes_and_timestamped_in_utc(client, db, eighth, monkeypatch):
    monkeypatch.setattr(render_jobs, "start_job", lambda job_id: None)
    now = datetime.utcnow()
    for cls in ("5th", "6th"):
        other = report_card_template(db, cls, term="Term I")
        db.add(PdfRenderJob(template_id=other.id, template_version=1, requested_by="x",
                            status=RenderJobStatus.running, student_ids=[1], total=1,
                            heartbeat_at=now, created_at=now))
    db.commit()
    t = eighth["t"]
    assert client.post(f"/api/pdf/templates/{t.id}/render-jobs", json={}, headers=auth("admin")).status_code == 429
    db.query(PdfRenderJob).delete()
    db.commit()
    job = render_jobs.create_job(db, t, [eighth["s1"].id], include_drafts=None, force=False, actor="x")
    assert abs((job.created_at - datetime.utcnow()).total_seconds()) < 5


# ── class-subjects edge cases ────────────────────────────────────────────
def test_exam_cannot_switch_between_grades_and_marks_once_entered(client, db, maths):
    _, comps, _ = maths
    r = client.patch(f"/api/class-subjects/components/{comps['PT First'].id}", json={"max_marks": 0},
                     headers=auth("super_admin"))
    assert r.status_code == 409


def test_force_deleted_exam_marks_are_archived_not_revived(client, db, maths):
    cs, comps, _ = maths
    cid = comps["PT First"].id
    assert client.delete(f"/api/class-subjects/components/{cid}?force=true", headers=auth("super_admin")).status_code in (200, 204)
    client.post(f"/api/class-subjects/{cs.id}/components", json={"component_name": "PT First", "max_marks": 35, "term": 1},
                headers=auth("super_admin"))
    db.expire_all()
    names = {b.exam_type for b in db.query(MarksBatch)}
    assert "PT First" not in names and f"[deleted #{cid}] PT First" in names


def test_rename_collision_is_a_409_even_when_only_case_differs(client, db, maths):
    _, comps, _ = maths
    r = client.patch(f"/api/class-subjects/components/{comps['PT First'].id}", json={"component_name": "p.t. second"},
                     headers=auth("super_admin"))
    assert r.status_code == 409


# ── engine: annual cards always add up ───────────────────────────────────
def test_annual_components_layout_has_a_both_terms_column():
    comps = [NS(component_name="P.T. First", max_marks=35, term=1, order_index=0),
             NS(component_name="Oral", max_marks=20, term=None, order_index=1),
             NS(component_name="P.T. Third", max_marks=35, term=2, order_index=2)]
    hindi = NS(subject_name="Hindi", subject_name_pa=None, category="academic", order_index=0, components=comps)
    rows = [NS(student_id=1, subject="Hindi", exam_type=e, marks=v, grade=None)
            for e, v in (("P.T. First", 30), ("Oral", 18), ("P.T. Third", 25))]
    res = aggregate_class_results(class_name="9th", session="s", scope="annual", class_subjects=[hindi],
                                  marks_rows=rows, student_ids=[1])
    assert [g.key for g in res.groups] == ["Term 1", "Term 2", "Both terms"]
    cells = res.students[0].subjects[0].cells
    assert sum(c.obtained for c in cells) == res.students[0].subjects[0].obtained == 73


# ── PSEB admit cards get the same fresh/stale tracking ───────────────────
def test_pseb_roster_reports_stale_cards(client, db, eighth, monkeypatch):
    monkeypatch.setattr("app.pdf.render_or_cache.render_pdf", lambda kind, payload: b"%PDF-1.4 fake")
    s1 = eighth["s1"]
    data = {"schoolCode": "0098351", "centre": {"code": "1", "schoolCode": "2", "district": "Patiala", "set": "A",
                                                "name": {"en": "Centre", "pa": "ਕੇਂਦਰ"}},
            "examTime": {"en": "10:00", "pa": "10:00"},
            "dateSheet": [{"subCode": "001", "subject": {"en": "Punjabi", "pa": "ਪੰਜਾਬੀ"}, "theoryDate": "01-03-2027",
                           "practical": "No"}]}
    r = client.post("/api/pdf/templates", json={"kind": "pseb-admit-card", "class_name": "8th", "session": "2026-27",
                                                "data": data}, headers=auth("admin"))
    tid = r.json()["id"]
    client.put(f"/api/pdf/templates/{tid}/student-data",
               json={"entries": [{"student_id": s1.id, "data": {"rollNo": "101", "regNo": "R1"}}]}, headers=auth("admin"))
    client.post(f"/api/pdf/templates/{tid}/render", json={"student_ids": [s1.id]}, headers=auth("admin"))
    row = lambda: next(x for x in client.get(f"/api/pdf/templates/{tid}/roster", headers=auth("admin")).json()["students"]
                       if x["id"] == s1.id)
    assert row()["cached_pdf_id"] and not row()["stale_pdf_id"]
    client.put(f"/api/pdf/templates/{tid}/student-data",
               json={"entries": [{"student_id": s1.id, "data": {"regNo": "R2"}}]}, headers=auth("admin"))
    assert row()["cached_pdf_id"] is None and row()["stale_pdf_id"]
