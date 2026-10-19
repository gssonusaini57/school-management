"""marks_batches.revision: a screen showing an outdated batch can't save over newer marks."""
from app.models.class_subject import SubjectExamComponent
from app.models.marks import Marks
from app.models.marks_batch import MarksBatch, MarksBatchStatus

from .conftest import auth
from .factories import batch
from .test_marks_write_paths import _csv, _form, _upload, eighth  # noqa: F401  (shared fixture)

STAFF = auth("staff", ["8th"])
Q = {"class": "8th", "subject": "Mathematics", "exam_type": "P.T. First", "session": "2026-27"}


def _load(client, headers=STAFF):
    return client.get("/api/marks/batches", params=Q, headers=headers).json()


def _save(client, loaded, items, headers=STAFF, **extra):
    body = _form(0, items=items, base_batch_id=loaded["id"], base_revision=loaded["revision"], **extra)
    return client.post("/api/marks/batches", json=body, headers=headers)


def _rows(db, batch_id):
    db.expire_all()
    return {m.student_id: m.marks for m in db.query(Marks).filter(Marks.batch_id == batch_id)}


def _revision(db, batch_id):
    db.expire_all()
    return db.get(MarksBatch, batch_id).revision


def test_a_screen_left_open_cannot_put_back_old_marks(client, db, eighth):
    """Laptop loads (Asha 10); the phone then saves Asha 30 and Ravi 20; the laptop,
    still showing Asha 10 and Ravi blank, saves with the same batch id."""
    a, b, _ = eighth
    bt = batch(db, "8th", "Mathematics", "P.T. First", marks={a.id: 10})
    db.commit()
    laptop = _load(client)
    phone = _load(client)
    assert laptop["revision"] == phone["revision"] == 0
    r = _save(client, phone, [{"student_id": a.id, "marks": 30}, {"student_id": b.id, "marks": 20}])
    assert r.status_code == 200 and r.json()["revision"] == 1
    r = _save(client, laptop, [{"student_id": a.id, "marks": 10}])
    assert r.status_code == 409 and "changed after this screen loaded" in r.json()["detail"]
    assert _rows(db, bt.id) == {a.id: 30, b.id: 20}
    assert _revision(db, bt.id) == 1
    # Submit final runs the same save first, so it can't lock the old set either.
    assert _save(client, laptop, [{"student_id": a.id, "marks": 10}], headers=auth("super_admin")).status_code == 409


def test_a_matching_revision_saves_and_moves_the_revision_on(client, db, eighth):
    a, b, _ = eighth
    first = client.post("/api/marks/batches", json=_form(a.id, base_batch_id=None), headers=STAFF)
    assert first.status_code == 200 and first.json()["revision"] == 1      # created and filled
    loaded = _load(client)
    assert loaded["revision"] == 1
    r = _save(client, loaded, [{"student_id": a.id, "marks": 31}, {"student_id": b.id, "marks": 5}])
    assert r.status_code == 200 and r.json()["revision"] == 2
    assert _rows(db, loaded["id"]) == {a.id: 31, b.id: 5}


def test_an_omitted_revision_is_not_checked(client, db, eighth):
    """Clients that send only base_batch_id (web and app before the revision) keep that check alone."""
    a, _, _ = eighth
    bt = batch(db, "8th", "Mathematics", "P.T. First", marks={a.id: 10})
    bt.revision = 7
    db.commit()
    r = client.post("/api/marks/batches", json=_form(a.id, base_batch_id=bt.id), headers=STAFF)
    assert r.status_code == 200 and r.json()["revision"] == 8


def test_submit_approve_reject_and_csv_import_move_the_revision(client, db, eighth):
    a, b, _ = eighth
    bt = batch(db, "8th", "Mathematics", "P.T. First", marks={a.id: 10})
    db.commit()
    before_submit = _load(client)
    assert client.post(f"/api/marks/batches/{bt.id}/submit", headers=STAFF).status_code == 200
    assert _revision(db, bt.id) == 1
    # The super-admin re-submitting a locked batch changes nothing.
    assert client.post(f"/api/marks/batches/{bt.id}/submit", headers=auth("super_admin")).status_code == 200
    assert _revision(db, bt.id) == 1
    # A screen loaded before the submit is outdated, even for the super-admin.
    r = _save(client, before_submit, [{"student_id": a.id, "marks": 12}], headers=auth("super_admin"))
    assert r.status_code == 409

    req = client.post(f"/api/marks/batches/{bt.id}/request-edit", json={"reason": "typo"}, headers=STAFF)
    assert req.status_code == 201 and _revision(db, bt.id) == 1          # asking changes nothing yet
    r = client.post(f"/api/admin/marks-edit-requests/{req.json()['id']}/approve", headers=auth("super_admin"))
    assert r.status_code == 200 and _revision(db, bt.id) == 2
    assert _load(client)["status"] == "draft"

    assert client.post(f"/api/marks/batches/{bt.id}/submit", headers=STAFF).status_code == 200
    assert _revision(db, bt.id) == 3
    req = client.post(f"/api/marks/batches/{bt.id}/request-edit", json={"reason": "again"}, headers=STAFF)
    r = client.post(f"/api/admin/marks-edit-requests/{req.json()['id']}/reject", json={"reason": "no"},
                    headers=auth("super_admin"))
    assert r.status_code == 200 and _revision(db, bt.id) == 4

    r = _upload(client, _csv(f"8th,Mathematics,P.T. First,2026-27,{b.id},20"), role="super_admin")
    assert r.json()["inserted"] == 1 and _revision(db, bt.id) == 5


def test_renaming_an_exam_in_class_subjects_moves_the_revision(client, db, eighth):
    a, _, _ = eighth
    bt = batch(db, "8th", "Mathematics", "P.T. First", marks={a.id: 10})
    db.commit()
    comp = db.query(SubjectExamComponent).filter(SubjectExamComponent.component_name == "P.T. First").first()
    r = client.patch(f"/api/class-subjects/components/{comp.id}", json={"component_name": "P.T. 1"},
                     headers=auth("super_admin"))
    assert r.status_code == 200
    db.expire_all()
    renamed = db.get(MarksBatch, bt.id)
    assert (renamed.exam_type, renamed.revision, renamed.status) == ("P.T. 1", 1, MarksBatchStatus.draft)
