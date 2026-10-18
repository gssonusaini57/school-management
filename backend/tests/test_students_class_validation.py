"""Class names are normalised to the canonical list on every student write path."""
from app.constants import canonical_class
from app.models.student import Student
from app.models.student_edit_request import EditRequestRole, StudentEditRequest

from .conftest import auth
from .factories import student


def test_canonical_class_matching():
    assert canonical_class("LKG") == "L.K.G"
    assert canonical_class(" l.k.g. ") == "L.K.G"
    assert canonical_class("u k g") == "U.K.G"
    assert canonical_class("nursery") == "Nursery"
    assert canonical_class("10TH") == "10th"
    assert canonical_class("All") is None
    assert canonical_class("Prep") is None
    assert canonical_class(None) is None


def _payload(class_name):
    return {"name": "Asha Kaur", "father": "Gurpreet Singh", "mother": "Harjit Kaur", "class_name": class_name}


def test_create_normalises_known_spelling(client, db):
    r = client.post("/api/students", json=_payload("LKG"), headers=auth("admin"))
    assert r.status_code == 201, r.text
    assert r.json()["class_name"] == "L.K.G"


def test_create_rejects_unknown_class(client):
    for bad in ("Prep", "All", "Class 5"):
        r = client.post("/api/students", json=_payload(bad), headers=auth("admin"))
        assert r.status_code == 422, (bad, r.text)


def test_patch_rejects_unknown_class(client, db):
    s = student(db, class_name="8th")
    db.commit()
    r = client.patch(f"/api/students/{s.id}", json={"class_name": "Prep"}, headers=auth("super_admin"))
    assert r.status_code == 422


def test_bulk_import_maps_and_rejects_classes(client, db):
    csv = (
        "name,father,mother,phone,class_name\n"
        "Asha Kaur,Gurpreet Singh,Harjit Kaur,9876543210,LKG\n"
        "Ravi Kumar,Mohan Lal,Sita Devi,9876543211,Prep\n"
    )
    r = client.post("/api/students/bulk-import", files={"file": ("s.csv", csv, "text/csv")},
                    headers=auth("admin"))
    body = r.json()
    assert body["aborted"] is True
    assert [(e["row"], e["field"]) for e in body["errors"]] == [(3, "class_name")]

    ok = csv.splitlines()[0] + "\n" + csv.splitlines()[1] + "\n"
    r = client.post("/api/students/bulk-import", files={"file": ("s.csv", ok, "text/csv")},
                    headers=auth("admin"))
    assert r.json()["inserted"] == 1
    db.expire_all()
    assert db.query(Student).one().class_name == "L.K.G"


def test_approving_a_queued_edit_with_an_unknown_class_is_a_422_not_a_500(client, db):
    s = student(db, class_name="8th")
    req = StudentEditRequest(student_id=s.id, requested_by="Teacher", requested_by_role=EditRequestRole.staff,
                             changes={"class_name": {"old": "8th", "new": "Prep"}})
    db.add(req)
    db.commit()
    r = client.post(f"/api/admin/edit-requests/{req.id}/approve", headers=auth("super_admin"))
    assert r.status_code == 422
