"""Marks are only written through draft batches: Marks Entry form and CSV import."""
import pytest

from app.models.marks import Marks
from app.models.marks_batch import MarksBatch, MarksBatchStatus
from app.models.record_status import RecordStatus

from .conftest import auth
from .factories import academic_session, batch, student, subject
from app.models.class_subject import SubjectCategory


@pytest.fixture()
def eighth(db):
    academic_session(db, "2026-27")
    a = student(db, name="Asha Kaur", roll_no="1")
    b = student(db, name="Ravi Kumar", roll_no="2")
    gone = student(db, name="Archived", roll_no="3", status=RecordStatus.deleted)
    subject(db, "8th", "Mathematics", [("P.T. First", 35, 1), ("P.T. Second", 35, 1)])
    subject(db, "8th", "Computer", [("Term 1 Grade", 0, 1)], category=SubjectCategory.grading, order_index=10)
    db.commit()
    return a, b, gone


def _csv(*lines):
    return "class_name,subject,exam_type,session,student_id,marks\n" + "\n".join(lines) + "\n"


def _upload(client, body, role="admin"):
    return client.post("/api/marks/bulk-import", files={"file": ("m.csv", body, "text/csv")}, headers=auth(role))


def test_legacy_bulk_endpoint_is_gone(client):
    r = client.post("/api/marks/bulk", json={}, headers=auth("admin"))
    assert r.status_code == 410


def test_import_creates_one_draft_batch_and_upserts(client, db, eighth):
    a, b, _ = eighth
    r = _upload(client, _csv(f"8th,Mathematics,P.T. First,2026-27,{a.id},30",
                             f"8TH,Mathematics,P.T. First,2026-27,{b.id},12"))  # class spelling normalised
    assert r.json() == {"inserted": 2, "errors": [], "aborted": False}
    # Re-import one row with a new value: updated in place, the other kept.
    r = _upload(client, _csv(f"8th,Mathematics,P.T. First,2026-27,{a.id},33"))
    assert r.json()["inserted"] == 1
    db.expire_all()
    batches = db.query(MarksBatch).all()
    assert len(batches) == 1 and batches[0].status == MarksBatchStatus.draft and batches[0].max_marks == 35
    rows = {m.student_id: m.marks for m in db.query(Marks).all()}
    assert rows == {a.id: 33, b.id: 12}
    assert all(m.batch_id == batches[0].id for m in db.query(Marks).all())


@pytest.mark.parametrize("line,field", [
    ("8th,Mathematics,Final / Annual,2026-27,{a},30", "exam_type"),     # not a component
    ("8th,Computer,Term 1 Grade,2026-27,{a},3", "grade"),                # graded exam needs a letter
    ("8th,Mathematics,P.T. First,2026,{a},30", "session"),
    ("8th,Mathematics,P.T. First,2026-27,{a},36", "marks"),              # above max 35
    ("8th,Mathematics,P.T. First,2026-27,{gone},10", "student_id"),     # archived student
    ("Prep,Mathematics,P.T. First,2026-27,{a},10", "class_name"),
])
def test_import_rejects_bad_rows_atomically(client, db, eighth, line, field):
    a, _, gone = eighth
    good = f"8th,Mathematics,P.T. Second,2026-27,{a.id},20"
    r = _upload(client, _csv(good, line.format(a=a.id, gone=gone.id)))
    body = r.json()
    assert body["aborted"] is True and body["inserted"] == 0
    assert [(e["row"], e["field"]) for e in body["errors"]] == [(3, field)]
    assert db.query(Marks).count() == 0


def test_import_respects_the_submitted_lock(client, db, eighth):
    a, _, _ = eighth
    batch(db, "8th", "Mathematics", "P.T. First", status=MarksBatchStatus.submitted, marks={a.id: 10})
    db.commit()
    line = _csv(f"8th,Mathematics,P.T. First,2026-27,{a.id},30")
    r = _upload(client, line, role="admin")
    assert r.json()["aborted"] is True
    assert "locked" in r.json()["errors"][0]["reason"]
    r = _upload(client, line, role="super_admin")
    assert r.json()["inserted"] == 1
    db.expire_all()
    assert db.query(Marks).one().marks == 30


def test_import_is_admin_only(client, eighth):
    a, _, _ = eighth
    r = _upload(client, _csv(f"8th,Mathematics,P.T. First,2026-27,{a.id},30"), role="staff")
    assert r.status_code == 403


def test_form_save_prunes_students_cleared_on_screen(client, db, eighth):
    a, b, _ = eighth
    body = {"class_name": "8th", "subject": "Mathematics", "exam_type": "P.T. First", "session": "2026-27",
            "max_marks": 35, "items": [{"student_id": a.id, "marks": 30}, {"student_id": b.id, "marks": 20}]}
    assert client.post("/api/marks/batches", json=body, headers=auth("staff", ["8th"])).status_code == 200
    body["items"] = [{"student_id": a.id, "marks": 31}]
    r = client.post("/api/marks/batches", json=body, headers=auth("staff", ["8th"]))
    assert [(i["student_id"], i["marks"]) for i in r.json()["items"]] == [(a.id, 31)]


def test_submit_notifies_once_and_super_admin_resubmit_is_a_no_op(client, db, eighth, monkeypatch):
    a, _, _ = eighth
    calls = []
    monkeypatch.setattr("app.routers.marks_batches.notify_marks_submitted",
                        lambda db_, b, n: calls.append((b.id, n)))
    bt = batch(db, "8th", "Mathematics", "P.T. First", marks={a.id: 10})
    db.commit()
    assert client.post(f"/api/marks/batches/{bt.id}/submit", headers=auth("admin")).status_code == 200
    assert calls == [(bt.id, 1)]
    assert client.post(f"/api/marks/batches/{bt.id}/submit", headers=auth("admin")).status_code == 409
    r = client.post(f"/api/marks/batches/{bt.id}/submit", headers=auth("super_admin"))
    assert r.status_code == 200 and r.json()["status"] == "submitted"
    assert len(calls) == 1


def _form(a_id, **extra):
    return {"class_name": "8th", "subject": "Mathematics", "exam_type": "P.T. First", "session": "2026-27",
            "max_marks": 35, "items": [{"student_id": a_id, "marks": 30}], **extra}


@pytest.mark.parametrize("base", [None, 0])
def test_save_with_no_base_creates_the_batch_when_none_exists(client, db, eighth, base):
    a, _, _ = eighth
    r = client.post("/api/marks/batches", json=_form(a.id, base_batch_id=base), headers=auth("staff", ["8th"]))
    assert r.status_code == 200
    assert db.query(MarksBatch).count() == 1


@pytest.mark.parametrize("base", [None, 0, "other"])
def test_save_against_a_stale_or_failed_load_is_refused_and_keeps_the_marks(client, db, eighth, base):
    """The screen saw no batch (failed or unfinished load) or another test's batch,
    but marks are saved on the server: the save must not overwrite or prune them."""
    a, b, _ = eighth
    other = batch(db, "8th", "Mathematics", "P.T. Second", marks={a.id: 5})
    saved = batch(db, "8th", "Mathematics", "P.T. First", marks={a.id: 10, b.id: 20})
    db.commit()
    base_id = other.id if base == "other" else base
    r = client.post("/api/marks/batches", json=_form(a.id, base_batch_id=base_id), headers=auth("staff", ["8th"]))
    assert r.status_code == 409 and "Reload" in r.json()["detail"]
    db.expire_all()
    assert {m.student_id: m.marks for m in db.query(Marks).filter(Marks.batch_id == saved.id)} == {a.id: 10, b.id: 20}


def test_save_with_the_loaded_batch_id_goes_through(client, db, eighth):
    a, b, _ = eighth
    saved = batch(db, "8th", "Mathematics", "P.T. First", marks={a.id: 10, b.id: 20})
    db.commit()
    r = client.post("/api/marks/batches", json=_form(a.id, base_batch_id=saved.id), headers=auth("staff", ["8th"]))
    assert r.status_code == 200
    assert [(i["student_id"], i["marks"]) for i in r.json()["items"]] == [(a.id, 30)]


def test_save_naming_a_batch_that_no_longer_exists_is_refused(client, db, eighth):
    a, _, _ = eighth
    r = client.post("/api/marks/batches", json=_form(a.id, base_batch_id=999), headers=auth("staff", ["8th"]))
    assert r.status_code == 409
    assert db.query(MarksBatch).count() == 0


def test_older_apps_that_omit_the_base_keep_the_unchecked_save(client, db, eighth):
    a, b, _ = eighth
    batch(db, "8th", "Mathematics", "P.T. First", marks={a.id: 10, b.id: 20})
    db.commit()
    r = client.post("/api/marks/batches", json=_form(a.id), headers=auth("staff", ["8th"]))
    assert r.status_code == 200


def test_marks_entry_needs_the_menu_grant_on_the_server(client, db, eighth):
    """The web and app hide Marks Entry without the grant; the server refuses it too."""
    a, _, _ = eighth
    bt = batch(db, "8th", "Mathematics", "P.T. First", marks={a.id: 10})
    db.commit()
    no_entry = auth("staff", ["8th"], menus=["dashboard", "marks-results"])
    q = {"class": "8th", "subject": "Mathematics", "exam_type": "P.T. First", "session": "2026-27"}
    assert client.get("/api/marks/batches", params=q, headers=no_entry).status_code == 403
    r = client.post("/api/marks/batches", json=_form(a.id, base_batch_id=bt.id), headers=no_entry)
    assert r.status_code == 403 and "marks entry" in r.json()["detail"]
    assert client.post(f"/api/marks/batches/{bt.id}/submit", headers=no_entry).status_code == 403
    assert client.post(f"/api/marks/batches/{bt.id}/request-edit", json={"reason": "typo"},
                       headers=no_entry).status_code == 403
    db.expire_all()
    assert {m.student_id: m.marks for m in db.query(Marks)} == {a.id: 10}
    # Default staff menus include Marks Entry, and admins always pass.
    assert client.get("/api/marks/batches", params=q, headers=auth("staff", ["8th"])).status_code == 200
    assert client.get("/api/marks/batches", params=q, headers=auth("admin", menus=[])).status_code == 200
