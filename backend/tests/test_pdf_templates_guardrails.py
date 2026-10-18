"""Cached PDFs are class-scoped; template rosters hide archived students."""
from app.models.record_status import RecordStatus

from .conftest import auth, make_token
from .factories import academic_session, cached_pdf, report_card_template, student


def _setup(db):
    s = student(db, class_name="8th")
    t = report_card_template(db, class_name="8th")
    c = cached_pdf(db, t, s.id)
    db.commit()
    return s, t, c


def test_cache_download_is_class_scoped(client, db):
    _, _, c = _setup(db)
    assert client.get(f"/api/pdf/cache/{c.id}", headers=auth("staff", ["5th"])).status_code == 403
    r = client.get(f"/api/pdf/cache/{c.id}", headers=auth("staff", ["8th"]))
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert client.get(f"/api/pdf/cache/{c.id}", headers=auth("admin")).status_code == 200


def test_inline_cache_download_is_class_scoped(client, db):
    _, _, c = _setup(db)
    url = f"/api/pdf/cache/{c.id}/inline"
    assert client.get(url, params={"token": make_token("staff", ["5th"])}).status_code == 403
    assert client.get(url, params={"token": make_token("staff", ["8th"])}).status_code == 200


def test_roster_hides_archived_students(client, db):
    s, t, _ = _setup(db)
    student(db, name="Archived Child", class_name="8th", roll_no="2", status=RecordStatus.deleted)
    db.commit()
    r = client.get(f"/api/pdf/templates/{t.id}/students", headers=auth("admin"))
    assert [row["id"] for row in r.json()] == [s.id]


def test_template_class_is_validated(client, db):
    academic_session(db, "2026-27")
    db.commit()
    body = {"kind": "report-card", "class_name": "lkg", "session": "2026-27", "term": "Term I", "data": {}}
    r = client.post("/api/pdf/templates", json=body, headers=auth("admin"))
    assert r.status_code == 201, r.text
    assert r.json()["class_name"] == "L.K.G"
    body["class_name"] = "Prep"
    assert client.post("/api/pdf/templates", json=body, headers=auth("admin")).status_code == 422
