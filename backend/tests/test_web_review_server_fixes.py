"""Server-side fixes from the web review of the Results module."""
import pytest

from app.models.pdf_template import PdfStudentData, PdfTemplate
from app.pdf.render_or_cache import report_card_payload
from app.services.report_cards import gather_class_inputs

from .conftest import auth
from .test_report_cards import eighth  # noqa: F401
from .test_review_fixes import ninth_annual  # noqa: F401


def _put(client, t, sid, data, role="admin"):
    return client.put(f"/api/pdf/templates/{t.id}/student-data",
                      json={"entries": [{"student_id": sid, "data": data}]}, headers=auth(role, ["8th"]))


def _roster(client, t):
    body = client.get(f"/api/pdf/templates/{t.id}/roster", headers=auth("admin")).json()
    return {r["id"]: r for r in body["students"]}


def _summary(db, t, sid):
    return report_card_payload(gather_class_inputs(db, db.get(PdfTemplate, t.id)), sid)[0]["summary"]


def test_roster_attendance_is_what_the_card_prints(client, db, eighth):
    t, s1 = eighth["t"], eighth["s1"]          # computed: 1.5 present of 2 working days = 75 %
    assert _put(client, t, s1.id, {"workingDays": 3}).status_code == 200   # only the day count overridden
    row = _roster(client, t)[s1.id]
    assert row["attendance_pct"] == 50.0 and row["computed_attendance_pct"] == 75.0
    db.expire_all()
    s = _summary(db, t, s1.id)
    assert (s["attendancePct"], s["workingDays"], s["daysPresent"]) == (50.0, 3, 1.5)


def test_one_sided_day_overrides_are_checked_against_the_computed_days(client, db, eighth):
    t, s1 = eighth["t"], eighth["s1"]
    r = _put(client, t, s1.id, {"daysPresent": 5})            # computed working days: 2
    assert r.status_code == 422 and "Asha Kaur" in r.json()["detail"] and "working days" in r.json()["detail"]
    assert _put(client, t, s1.id, {"workingDays": 1}).status_code == 422     # computed days present: 1.5
    assert _put(client, t, s1.id, {"daysPresent": 2}).status_code == 200
    assert _put(client, t, s1.id, {"daysPresent": None, "workingDays": 2}).status_code == 200


def test_a_card_never_prints_more_days_present_than_working_days(client, db, eighth):
    """An override saved earlier can fall behind the computed count as attendance is marked."""
    t, s1 = eighth["t"], eighth["s1"]
    db.add(PdfStudentData(kind=t.kind, student_id=s1.id, session=t.session, term=t.term,
                          term_key=t.term or "", data={"workingDays": 1}, updated_by="t"))
    db.commit()
    with pytest.raises(ValueError, match="working days"):
        report_card_payload(gather_class_inputs(db, t), s1.id)
    row = _roster(client, t)[s1.id]
    assert "working days" in row["error"] and row["attendance_pct"] == 75.0


def test_only_the_super_admin_switches_draft_marks_on(client, db, eighth):
    new = {"kind": "report-card", "class_name": "9th", "session": "2026-27", "scope": "term1",
           "data": {"includeDrafts": True}}
    assert client.post("/api/pdf/templates", json=new, headers=auth("admin")).status_code == 403
    bulk = {"kind": "report-card", "session": "2026-27", "scope": "term2", "class_names": ["9th"],
            "data": {"includeDrafts": True}}
    assert client.post("/api/pdf/templates/bulk-create", json=bulk, headers=auth("admin")).status_code == 403
    url = f"/api/pdf/templates/{eighth['t'].id}"
    assert client.patch(url, json={"data": {"includeDrafts": True}}, headers=auth("admin")).status_code == 403
    assert client.patch(url, json={"data": {"includeDrafts": True}}, headers=auth("super_admin")).status_code == 200
    r = client.patch(url, json={"data": {"includeDrafts": True, "showRank": False}}, headers=auth("admin"))
    assert r.status_code == 200 and r.json()["data"]["includeDrafts"] is True    # admin keeps the choice
    assert client.patch(url, json={"data": {"showRank": True}}, headers=auth("admin")).status_code == 403
    assert client.post("/api/pdf/templates", json=new, headers=auth("super_admin")).status_code == 201


def test_results_report_the_pass_rule_they_used(client, db, ninth_annual):
    q = {"class": "9th", "session": "2026-27", "scope": "annual"}
    body = client.get("/api/marks/results", params=q, headers=auth("admin")).json()
    assert (body["pass_pct"], body["conditional_max_fails"]) == (33.0, 2)
    r = client.post("/api/pdf/templates", headers=auth("admin"), json={
        "kind": "report-card", "class_name": "9th", "session": "2026-27", "scope": "annual",
        "data": {"promotionRule": {"passPct": 40, "conditionalMaxFails": 1}}})
    assert r.status_code == 201
    body = client.get("/api/marks/results", params=q, headers=auth("admin")).json()
    assert (body["pass_pct"], body["conditional_max_fails"]) == (40.0, 1)


def test_a_legacy_template_cannot_take_a_scope_another_template_covers(client, db, eighth):
    from .factories import report_card_template
    legacy = report_card_template(db, "8th", term="First Term Exam")      # label the server can't map
    db.commit()
    url = f"/api/pdf/templates/{legacy.id}"
    r = client.patch(url, json={"scope": "term1"}, headers=auth("admin"))  # eighth["t"] already covers term1
    assert r.status_code == 409 and "already covers" in r.json()["detail"]
    r = client.patch(url, json={"scope": "term2"}, headers=auth("admin"))
    assert r.status_code == 200 and r.json()["scope"] == "term2"


def test_pseb_admit_card_never_prints_an_invented_date_of_birth(client, db, eighth, monkeypatch):
    monkeypatch.setattr("app.pdf.render_or_cache.render_pdf", lambda kind, payload: b"%PDF-1.4 fake")
    s1, s2 = eighth["s1"], eighth["s2"]                        # s1 has a DOB on record, s2 doesn't
    data = {"schoolCode": "0098351", "centre": {"code": "1", "schoolCode": "2", "district": "Patiala", "set": "A",
                                                "name": {"en": "Centre", "pa": "ਕੇਂਦਰ"}},
            "examTime": {"en": "10:00", "pa": "10:00"},
            "dateSheet": [{"subCode": "001", "subject": {"en": "Punjabi", "pa": "ਪੰਜਾਬੀ"}, "theoryDate": "01-03-2027",
                           "practical": "No"}]}
    r = client.post("/api/pdf/templates", json={"kind": "pseb-admit-card", "class_name": "8th", "session": "2026-27",
                                                "data": data}, headers=auth("admin"))
    tid = r.json()["id"]
    entries = [{"student_id": s.id, "data": {"rollNo": f"10{i}", "regNo": f"R{i}"}} for i, s in enumerate((s1, s2))]
    assert client.put(f"/api/pdf/templates/{tid}/student-data", json={"entries": entries},
                      headers=auth("admin")).status_code == 200
    out = client.post(f"/api/pdf/templates/{tid}/render", json={"student_ids": [s1.id, s2.id]},
                      headers=auth("admin")).json()["results"]
    by = {x["student_id"]: x for x in out}
    assert by[s1.id]["status"] == "rendered"
    assert by[s2.id]["status"] == "error" and "date of birth" in by[s2.id]["error"]
    rows = {x["id"]: x for x in client.get(f"/api/pdf/templates/{tid}/roster", headers=auth("admin")).json()["students"]}
    assert rows[s2.id]["missing_dob"] and "date of birth" in rows[s2.id]["error"]
