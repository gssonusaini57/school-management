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
