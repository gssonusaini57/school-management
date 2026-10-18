"""Report card v2: payload, overrides, cache freshness, permissions, bulk create, rendering."""
from datetime import date

import pytest

from app.models.class_subject import SubjectCategory
from app.models.marks import Marks
from app.models.marks_batch import MarksBatchStatus
from app.models.pdf_template import PdfCache, PdfTemplate
from app.pdf.render import render_html
from app.pdf.render_or_cache import render_students, report_card_payload
from app.services.report_cards import gather_class_inputs

from .conftest import auth
from .factories import academic_session, attendance_day, batch, report_card_template, student, subject


@pytest.fixture()
def eighth(db):
    academic_session(db, "2026-27")
    s1 = student(db, name="Asha Kaur", roll_no="1", dob=date(2013, 5, 2))
    s2 = student(db, name="Ravi Kumar", roll_no="2")
    s3 = student(db, name="New Child", roll_no="3")
    subject(db, "8th", "Mathematics", [
        ("P.T. First", 35, 1), ("P.T. Second", 35, 1),
        ("Semester First — Written", 70, 1), ("Semester First — Practical", 10, 1), ("P.T. Third", 35, 2),
    ], subject_name_pa="ਗਣਿਤ")
    subject(db, "8th", "English", [("P.T. First", 35, 1), ("Semester First", 80, 1)], order_index=1)
    subject(db, "8th", "Computer", [("Term 1 Grade", 0, 1), ("Term 2 Grade", 0, 2)],
            category=SubjectCategory.grading, order_index=10, subject_name_pa="ਕੰਪਿਊਟਰ")
    sub = MarksBatchStatus.submitted
    batch(db, "8th", "Mathematics", "P.T. First", status=sub, marks={s1.id: 30, s2.id: 20})
    batch(db, "8th", "English", "P.T. First", status=sub, marks={s1.id: 25, s2.id: 30})
    batch(db, "8th", "Mathematics", "P.T. Second", status=MarksBatchStatus.draft, marks={s1.id: 10})
    g = batch(db, "8th", "Computer", "Term 1 Grade", max_marks=0, status=sub, marks={s1.id: 0})
    db.query(Marks).filter(Marks.batch_id == g.id).update({"grade": "A1"})
    attendance_day(db, "8th", date(2026, 5, 4), {s1.id: "P", s2.id: "A"})
    attendance_day(db, "8th", date(2026, 5, 5), {s1.id: "H", s2.id: "P"})
    t = report_card_template(db, "8th", term="Term I",
                             data={"signatures": {"principal": "Principal Name", "classTeacher": "Ms Teacher"}})
    t.scope = "term1"
    t.layout = "components"
    db.commit()
    return {"t": t, "s1": s1, "s2": s2, "s3": s3}


def _payload(db, t, sid, **kw):
    return report_card_payload(gather_class_inputs(db, t, **kw), sid)


def test_payload_components_layout(db, eighth):
    t, s1 = eighth["t"], eighth["s1"]
    p, _ = _payload(db, t, s1.id)
    assert p["title"]["en"] == "Report Card · Term I" and p["title"]["pa"]
    assert [g["key"] for g in p["groups"]] == ["P.T. First", "P.T. Second", "Semester First"]
    maths = p["subjects"][0]
    assert maths["name"] == {"en": "Mathematics", "pa": "ਗਣਿਤ"}
    assert [c["status"] for c in maths["cells"]] == ["complete", "missing", "missing"]   # draft left out
    assert maths["marks"] == 30 and maths["max"] == 150 and maths["grade"] is None      # incomplete → no grade
    english = p["subjects"][1]
    assert [c["status"] for c in english["cells"]] == ["complete", "none", "missing"]
    assert p["coScholastic"] == [{"name": {"en": "Computer", "pa": "ਕੰਪਿਊਟਰ"}, "grade": "A1", "term1": "A1", "term2": None}]
    s = p["summary"]
    assert (s["total"], s["max"], s["rank"], s["classSize"]) == (55, 265, 1, 3)
    assert (s["attendancePct"], s["workingDays"], s["daysPresent"]) == (75.0, 2, 1.5)
    assert s["hasDrafts"] is True and s["incomplete"] is True
    assert s["remarks"] is None and s["promotion"] is None
    assert p["student"]["name"] == {"en": "Asha Kaur", "pa": None}       # no duplicated Punjabi line
    assert p["student"]["dob"] == "2013-05-02"


def test_dob_is_never_invented_and_no_marks_means_no_card(db, eighth):
    t = eighth["t"]
    p, _ = _payload(db, t, eighth["s2"].id)
    assert p["student"]["dob"] is None
    with pytest.raises(ValueError, match="no submitted marks"):
        _payload(db, t, eighth["s3"].id)


def test_drafts_print_only_when_asked(db, eighth):
    t, s1 = eighth["t"], eighth["s1"]
    p, _ = _payload(db, t, s1.id, include_drafts=True)
    assert p["subjects"][0]["marks"] == 40


def test_overrides_win_and_staff_may_only_write_remarks_and_house(client, db, eighth):
    t, s1 = eighth["t"], eighth["s1"]
    url = f"/api/pdf/templates/{t.id}/student-data"
    r = client.put(url, json={"entries": [{"student_id": s1.id, "data": {"rank": 5}}]},
                   headers=auth("staff", ["8th"]))
    assert r.status_code == 422
    r = client.put(url, json={"entries": [{"student_id": s1.id, "data": {
        "remarks": {"en": "Works hard", "pa": "ਮਿਹਨਤੀ"}, "house": "Tagore"}}]}, headers=auth("staff", ["8th"]))
    assert r.status_code == 200, r.text
    r = client.put(url, json={"entries": [{"student_id": s1.id, "data": {"rank": 5, "attendancePct": 90.5}}]},
                   headers=auth("admin"))
    assert r.status_code == 200
    db.expire_all()
    p, _ = _payload(db, db.get(PdfTemplate, t.id), s1.id)
    assert p["summary"]["rank"] == 5 and p["summary"]["attendancePct"] == 90.5
    assert p["summary"]["remarks"] == {"en": "Works hard", "pa": "ਮਿਹਨਤੀ"}   # kept by the merge
    assert p["student"]["house"] == "Tagore"
    assert client.put(url, json={"entries": []}, headers=auth("staff", ["5th"])).status_code == 403


def test_cache_hash_tracks_everything_the_card_prints(db, eighth):
    t, s1, s2 = eighth["t"], eighth["s1"], eighth["s2"]
    _, h0 = _payload(db, t, s1.id)
    _, h_same = _payload(db, t, s1.id)
    assert h0 == h_same
    # A classmate overtaking s1 changes s1's rank, so s1's card is stale too.
    db.query(Marks).filter(Marks.student_id == s2.id, Marks.subject == "Mathematics").update({"marks": 35})
    db.commit()
    p1, h1 = _payload(db, t, s1.id)
    assert p1["summary"]["rank"] == 2 and h1 != h0
    # Settings change → stale.
    t.data = {**t.data, "showRank": False}
    db.commit()
    assert _payload(db, t, s1.id)[1] != h1


def test_render_reuses_cache_until_something_changes(db, eighth, monkeypatch):
    calls = []
    monkeypatch.setattr("app.pdf.render_or_cache.render_pdf", lambda kind, payload: calls.append(payload) or b"%PDF-1.4 fake")
    t, s1, s3 = eighth["t"], eighth["s1"], eighth["s3"]
    first = render_students(db, template=t, student_ids=[s1.id, s3.id], actor="t")
    assert [r["status"] for r in first] == ["rendered", "error"]
    assert "provisional" in first[0]["warnings"][0]
    again = render_students(db, template=t, student_ids=[s1.id], actor="t")
    assert again[0]["status"] == "cached" and len(calls) == 1
    db.query(Marks).filter(Marks.student_id == s1.id, Marks.subject == "English").update({"marks": 26})
    db.commit()
    assert render_students(db, template=t, student_ids=[s1.id], actor="t")[0]["status"] == "rendered"
    assert db.query(PdfCache).count() == 1      # replaced in place, one row per student


def test_roster_reports_fresh_stale_and_errors(client, db, eighth, monkeypatch):
    monkeypatch.setattr("app.pdf.render_or_cache.render_pdf", lambda kind, payload: b"%PDF-1.4 fake")
    t, s1 = eighth["t"], eighth["s1"]
    render_students(db, template=t, student_ids=[s1.id], actor="t")
    body = client.get(f"/api/pdf/templates/{t.id}/roster", headers=auth("staff", ["8th"])).json()
    rows = {r["roll_no"]: r for r in body["students"]}
    assert rows["1"]["cached_pdf_id"] and not rows["1"]["stale_pdf_id"] and rows["1"]["provisional"]
    assert rows["3"]["error"] and rows["3"]["cached_pdf_id"] is None
    db.query(Marks).filter(Marks.student_id == s1.id, Marks.subject == "English").update({"marks": 20})
    db.commit()
    rows = {r["roll_no"]: r for r in client.get(f"/api/pdf/templates/{t.id}/roster", headers=auth("admin")).json()["students"]}
    assert rows["1"]["cached_pdf_id"] is None and rows["1"]["stale_pdf_id"]


def test_render_permissions(client, db, eighth, monkeypatch):
    monkeypatch.setattr("app.pdf.render_or_cache.render_pdf", lambda kind, payload: b"%PDF-1.4 fake")
    t, s1 = eighth["t"], eighth["s1"]
    url = f"/api/pdf/templates/{t.id}/render"
    assert client.post(url, json={"student_ids": [s1.id]}, headers=auth("staff", ["5th"])).status_code == 403
    assert client.post(url, json={"student_ids": [s1.id]}, headers=auth("staff", ["8th"])).status_code == 200
    assert client.post(url, json={"student_ids": [s1.id], "include_drafts": True},
                       headers=auth("admin")).status_code == 403
    r = client.post(url, json={"student_ids": [s1.id], "include_drafts": True}, headers=auth("super_admin"))
    assert r.status_code == 200
    assert client.patch(f"/api/pdf/templates/{t.id}", json={"layout": "summary"},
                        headers=auth("staff", ["8th"])).status_code == 403


def test_create_needs_a_scope_and_one_template_per_scope(client, db, eighth):
    base = {"kind": "report-card", "class_name": "9th", "session": "2026-27", "data": {}}
    assert client.post("/api/pdf/templates", json={**base, "term": "Half Yearly"},
                       headers=auth("admin")).status_code == 422
    r = client.post("/api/pdf/templates", json={**base, "term": "Term II"}, headers=auth("admin"))
    assert r.status_code == 201 and r.json()["scope"] == "term2"
    r = client.post("/api/pdf/templates", json={**base, "scope": "term2", "term": "Second Term"}, headers=auth("admin"))
    assert r.status_code == 409
    r = client.post("/api/pdf/templates", json={**base, "scope": "annual"}, headers=auth("admin"))
    assert r.status_code == 201 and r.json()["term"] == "Annual"


def test_bulk_create_skips_existing(client, eighth):
    body = {"session": "2026-27", "scope": "term1", "layout": "summary", "data": {"signatures": {"principal": "P"}}}
    r = client.post("/api/pdf/templates/bulk-create", json=body, headers=auth("admin"))
    assert r.status_code == 201, r.text
    out = r.json()
    assert len(out["created"]) == 14 and [s["class_name"] for s in out["skipped"]] == ["8th"]
    again = client.post("/api/pdf/templates/bulk-create", json=body, headers=auth("admin")).json()
    assert again["created"] == [] and len(again["skipped"]) == 15
    assert client.post("/api/pdf/templates/bulk-create", json=body, headers=auth("staff", ["8th"])).status_code == 403


def test_patch_layout_bumps_version_and_resolve_finds_by_scope(client, eighth):
    t = eighth["t"]
    r = client.patch(f"/api/pdf/templates/{t.id}", json={"layout": "summary"}, headers=auth("admin"))
    assert r.json()["version"] == 2 and r.json()["layout"] == "summary"
    q = {"class": "8th", "session": "2026-27", "scope": "term1"}
    assert client.get("/api/pdf/templates/resolve", params=q, headers=auth("staff", ["8th"])).json()["id"] == t.id
    assert client.get("/api/pdf/templates/resolve", params={**q, "scope": "annual"},
                      headers=auth("admin")).json() is None


def test_staff_list_only_shows_their_classes(client, db, eighth):
    report_card_template(db, "5th", term="Term I")
    db.commit()
    names = {t["class_name"] for t in client.get("/api/pdf/templates", headers=auth("staff", ["8th"])).json()}
    assert names == {"8th"}


@pytest.mark.parametrize("layout", ["summary", "components"])
def test_template_html_is_bilingual_and_prints_whole_numbers(db, eighth, layout):
    t, s1 = eighth["t"], eighth["s1"]
    t.layout = layout
    db.commit()
    p, _ = _payload(db, t, s1.id)
    html = render_html("report-card", p)
    assert "ਰਿਪੋਰਟ ਕਾਰਡ" in html and "ਵਿਸ਼ੇ" in html           # Punjabi title + "Subjects"
    assert ">55<" in html and "55.0" not in html
    assert "Excellent term" not in html                           # no invented remark
    assert ("P.T. First" in html) == (layout == "components")
    assert "Provisional" in html


def test_preview_html_for_admins(client, eighth):
    t, s1 = eighth["t"], eighth["s1"]
    r = client.get(f"/api/pdf/templates/{t.id}/preview", params={"student_id": s1.id, "format": "html"},
                   headers=auth("admin"))
    assert r.status_code == 200 and "Asha Kaur" in r.text
    assert client.get(f"/api/pdf/templates/{t.id}/preview", params={"student_id": s1.id},
                      headers=auth("staff", ["8th"])).status_code == 403
