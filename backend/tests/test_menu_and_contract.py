"""Menu grants are enforced on the server; roster exposes computed values; small contract rules."""
from datetime import date

from app.models.fee import FeePayment
from app.models.pdf_template import PdfTemplate, TemplateKind

from .conftest import auth, make_token
from .factories import cached_pdf, student
from .test_report_cards import eighth  # noqa: F401  (shared class fixture)

NO_RESULTS = ["dashboard", "attendance", "marks-entry"]   # a staff account without Marks Results


def test_staff_without_marks_results_menu_is_refused_everywhere(client, db, eighth, monkeypatch):
    monkeypatch.setattr("app.pdf.render_or_cache.render_pdf", lambda kind, payload: b"%PDF-1.4 fake")
    t, s1 = eighth["t"], eighth["s1"]
    cache = cached_pdf(db, t, s1.id)
    db.commit()
    h = auth("staff", ["8th"], menus=NO_RESULTS)
    q = {"class": "8th", "session": "2026-27", "scope": "term1"}
    assert client.get("/api/marks/results", params=q, headers=h).status_code == 403
    assert client.get("/api/pdf/templates/resolve", params=q, headers=h).status_code == 403
    assert client.get(f"/api/pdf/templates/{t.id}/roster", headers=h).status_code == 403
    assert client.post(f"/api/pdf/templates/{t.id}/render", json={"student_ids": [s1.id]}, headers=h).status_code == 403
    assert client.post(f"/api/pdf/templates/{t.id}/render-jobs", json={}, headers=h).status_code == 403
    assert client.get(f"/api/pdf/cache/{cache.id}", headers=h).status_code == 403
    assert client.get(f"/api/pdf/cache/{cache.id}/inline",
                      params={"token": make_token("staff", ["8th"], menus=NO_RESULTS)}).status_code == 403
    assert client.get("/api/pdf/templates", headers=h).json() == []
    # The same teacher with the default menus (which include marks-results) gets in.
    assert client.get("/api/marks/results", params=q, headers=auth("staff", ["8th"])).status_code == 200


def test_pseb_templates_need_the_templates_menu(client, db, eighth):
    p = PdfTemplate(kind=TemplateKind.pseb_admit_card, class_name="8th", session="2026-27", term=None, term_key="",
                    version=1, data={}, created_by="t", updated_by="t")
    db.add(p)
    db.commit()
    default_staff = {t["kind"] for t in client.get("/api/pdf/templates", headers=auth("staff", ["8th"])).json()}
    assert default_staff == {"report-card"}
    assert client.get(f"/api/pdf/templates/{p.id}", headers=auth("staff", ["8th"])).status_code == 403
    with_menu = auth("staff", ["8th"], menus=["templates"])
    assert client.get(f"/api/pdf/templates/{p.id}", headers=with_menu).status_code == 200


def test_explicit_false_include_drafts_is_allowed(client, eighth, monkeypatch):
    monkeypatch.setattr("app.pdf.render_or_cache.render_pdf", lambda kind, payload: b"%PDF-1.4 fake")
    t, s1 = eighth["t"], eighth["s1"]
    r = client.post(f"/api/pdf/templates/{t.id}/render", json={"student_ids": [s1.id], "include_drafts": False},
                    headers=auth("staff", ["8th"]))
    assert r.status_code == 200


def test_bulk_create_with_an_empty_class_list_is_refused(client, eighth):
    body = {"session": "2026-27", "scope": "annual", "class_names": [], "data": {}}
    assert client.post("/api/pdf/templates/bulk-create", json=body, headers=auth("admin")).status_code == 422


def test_scope_can_be_filled_once_on_a_legacy_template(client, db, eighth):
    legacy = PdfTemplate(kind=TemplateKind.report_card, class_name="7th", session="2026-27", term="Half Yearly",
                         term_key="Half Yearly", scope=None, version=1, data={}, created_by="t", updated_by="t")
    db.add(legacy)
    db.commit()
    r = client.patch(f"/api/pdf/templates/{legacy.id}", json={"scope": "term1"}, headers=auth("admin"))
    assert r.status_code == 200 and r.json()["scope"] == "term1" and r.json()["version"] == 2
    assert client.patch(f"/api/pdf/templates/{legacy.id}", json={"scope": "annual"},
                        headers=auth("admin")).status_code == 409


def test_roster_reports_computed_values_beside_overrides(client, eighth):
    t, s1 = eighth["t"], eighth["s1"]
    client.put(f"/api/pdf/templates/{t.id}/student-data",
               json={"entries": [{"student_id": s1.id, "data": {"rank": 7}}]}, headers=auth("admin"))
    row = next(r for r in client.get(f"/api/pdf/templates/{t.id}/roster", headers=auth("admin")).json()["students"]
               if r["id"] == s1.id)
    assert (row["rank"], row["computed_rank"], row["overrides"]) == (7, 1, ["rank"])
    assert row["computed_attendance_pct"] == 75.0


def test_fees_of_every_class_are_for_admins_only(client, db):
    for cls, receipt in (("8th", "RC1"), ("9th", "RC2")):
        s = student(db, class_name=cls)
        db.add(FeePayment(student_id=s.id, student_name=s.name, class_name=cls, month="October", year="2026",
                          amount=500, date=date(2026, 10, 1), receipt_no=receipt, saved_by="t"))
    db.commit()
    teacher = auth("staff", ["8th"], menus=["dashboard", "fees"])
    r = client.get("/api/fees", headers=teacher)
    assert r.status_code == 403 and r.json()["detail"] == "Admin only"
    for role in ("admin", "super_admin"):
        r = client.get("/api/fees", headers=auth(role))
        assert r.status_code == 200 and sorted(f["receipt_no"] for f in r.json()) == ["RC1", "RC2"]
    # A teacher can still list one of their own classes, and only theirs.
    mine = client.get("/api/fees", params={"class": "8th"}, headers=teacher)
    assert mine.status_code == 200 and [f["receipt_no"] for f in mine.json()] == ["RC1"]
    assert client.get("/api/fees", params={"class": "9th"}, headers=teacher).status_code == 403
