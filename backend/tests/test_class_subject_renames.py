"""Renames and max changes in the class-subjects master keep marks attached."""
import pytest

from app.models.class_subject import SubjectExamComponent
from app.models.marks import Marks
from app.models.marks_batch import MarksBatch

from .conftest import auth
from .factories import academic_session, batch, student, subject


@pytest.fixture()
def maths(db):
    academic_session(db)
    s = student(db)
    cs = subject(db, "8th", "Mathematics", [("PT First", 35, 1), ("P.T. Second", 35, 1)])
    batch(db, "8th", "Mathematics", "PT First", marks={s.id: 30})
    batch(db, "8th", "Mathematics", "P.T. Second", marks={s.id: 20})
    db.commit()
    comps = {c.component_name: c for c in cs.components}
    return cs, comps, s


def _names(db):
    db.expire_all()
    return (sorted({m.exam_type for m in db.query(Marks)}), sorted({b.exam_type for b in db.query(MarksBatch)}))


def test_patch_rename_moves_marks_and_batches(client, db, maths):
    _, comps, _ = maths
    r = client.patch(f"/api/class-subjects/components/{comps['PT First'].id}",
                     json={"component_name": "P.T. First"}, headers=auth("super_admin"))
    assert r.status_code == 200, r.text
    assert _names(db) == (["P.T. First", "P.T. Second"], ["P.T. First", "P.T. Second"])


def test_put_with_ids_handles_a_name_swap(client, db, maths):
    cs, comps, s = maths
    payload = {"components": [
        {"id": comps["PT First"].id, "component_name": "P.T. Second", "max_marks": 35, "term": 1, "order_index": 1},
        {"id": comps["P.T. Second"].id, "component_name": "PT First", "max_marks": 35, "term": 1, "order_index": 2},
    ]}
    r = client.put(f"/api/class-subjects/{cs.id}/components", json=payload, headers=auth("super_admin"))
    assert r.status_code == 200, r.text
    db.expire_all()
    by_name = {m.exam_type: m.marks for m in db.query(Marks)}
    # The component that was "PT First" (mark 30) is now named "P.T. Second".
    assert by_name == {"P.T. Second": 30, "PT First": 20}


def test_deleting_a_component_with_marks_needs_force(client, db, maths):
    cs, comps, _ = maths
    keep_one = {"components": [{"id": comps["P.T. Second"].id, "component_name": "P.T. Second",
                                "max_marks": 35, "term": 1}]}
    r = client.put(f"/api/class-subjects/{cs.id}/components", json=keep_one, headers=auth("super_admin"))
    assert r.status_code == 409 and "PT First" in r.json()["detail"]
    r = client.put(f"/api/class-subjects/{cs.id}/components?force=true", json=keep_one, headers=auth("super_admin"))
    assert r.status_code == 200
    assert client.delete(f"/api/class-subjects/components/{comps['P.T. Second'].id}",
                         headers=auth("super_admin")).status_code == 409


def test_max_cannot_drop_below_entered_marks_and_syncs_batches(client, db, maths):
    _, comps, _ = maths
    url = f"/api/class-subjects/components/{comps['PT First'].id}"
    assert client.patch(url, json={"max_marks": 25}, headers=auth("super_admin")).status_code == 409
    assert client.patch(url, json={"max_marks": 40}, headers=auth("super_admin")).status_code == 200
    db.expire_all()
    assert db.query(MarksBatch).filter_by(exam_type="PT First").one().max_marks == 40
    assert db.query(Marks).filter_by(exam_type="PT First").one().max_marks == 40


def test_subject_rename_moves_marks(client, db, maths):
    cs, _, _ = maths
    r = client.patch(f"/api/class-subjects/{cs.id}", json={"subject_name": "Maths"}, headers=auth("super_admin"))
    assert r.status_code == 200
    db.expire_all()
    assert {m.subject for m in db.query(Marks)} == {"Maths"}
    assert {b.subject for b in db.query(MarksBatch)} == {"Maths"}


def test_put_without_ids_still_matches_by_name(client, db, maths):
    cs, comps, _ = maths
    payload = {"components": [
        {"component_name": "PT First", "max_marks": 35, "term": 1},
        {"component_name": "P.T. Second", "max_marks": 35, "term": 1},
        {"component_name": "Semester First", "max_marks": 80, "term": 1},
    ]}
    r = client.put(f"/api/class-subjects/{cs.id}/components", json=payload, headers=auth("super_admin"))
    assert r.status_code == 200, r.text
    db.expire_all()
    ids = {c.component_name: c.id for c in db.query(SubjectExamComponent)}
    assert ids["PT First"] == comps["PT First"].id and "Semester First" in ids
