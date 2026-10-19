"""GET /api/marks/batches/summary: marks progress per class, subject and exam for a session."""
from types import SimpleNamespace as NS

import pytest

from app.models.class_subject import SubjectCategory
from app.models.marks import Marks
from app.models.marks_batch import MarksBatchStatus, MarksEditRequest, MarksEditRequestRole, MarksEditRequestStatus
from app.models.record_status import RecordStatus
from app.models.subject_enrollment import SubjectEnrollment

from .conftest import auth
from .factories import academic_session, batch, student, subject

URL = "/api/marks/batches/summary"
SESSION = {"session": "2026-27"}
NO_MARKS_MENUS = ["dashboard", "attendance", "students"]


def _request(db, b, status: MarksEditRequestStatus) -> None:
    db.add(MarksEditRequest(batch_id=b.id, requested_by="Teacher", requested_by_role=MarksEditRequestRole.staff,
                            reason="typo", status=status))


@pytest.fixture()
def school(db):
    """8th: English (submitted, edit request pending), Mathematics (one draft exam, one
    not started), Art (graded, draft). 10th: Science, not started. Classes, subjects and
    exams are created out of display order, and display order is not alphabetical."""
    academic_session(db, "2026-27")
    academic_session(db, "2025-26", is_current=False)
    science = subject(db, "10th", "Science", [("P.T. First", 20, 1)])
    maths = subject(db, "8th", "Mathematics", [("P.T. First", 20, 1), ("Half Yearly", 80, 2)], order_index=1)
    english = subject(db, "8th", "English", [("P.T. First", 20, 1)], order_index=0)
    art = subject(db, "8th", "Art", [("Term 1 Grade", 0, None)], category=SubjectCategory.grading, order_index=5)
    a = student(db, name="Asha Kaur", class_name="8th", roll_no="1")
    b = student(db, name="Ravi Kumar", class_name="8th", roll_no="2")
    gone = student(db, name="Gone Away", class_name="8th", roll_no="3", status=RecordStatus.deleted)
    student(db, name="Tara Devi", class_name="10th", roll_no="1")

    eng = batch(db, "8th", "English", "P.T. First", max_marks=20, status=MarksBatchStatus.submitted,
                marks={a.id: 15, b.id: 18, gone.id: 10})        # the archived student's mark isn't counted
    eng.revision = 3
    _request(db, eng, MarksEditRequestStatus.pending)
    pt = batch(db, "8th", "Mathematics", "P.T. First", max_marks=20, marks={a.id: 12})
    _request(db, pt, MarksEditRequestStatus.rejected)           # only a pending request counts
    graded = batch(db, "8th", "Art", "Term 1 Grade", max_marks=0, marks={a.id: 0, b.id: 0})
    for m in db.query(Marks).filter_by(batch_id=graded.id, student_id=a.id):
        m.grade = "A1"                                           # Ravi's row has no grade yet
    # Neither of these is an exam of the 2026-27 sheet in Class Subjects:
    batch(db, "8th", "Mathematics", "Half Yearly", session="2025-26", max_marks=80, marks={a.id: 70})
    batch(db, "8th", "Mathematics", "[deleted #99] P.T. Second", max_marks=20, marks={a.id: 5})
    db.commit()
    return NS(a=a, b=b, eng=eng, pt=pt, graded=graded, science=science, maths=maths, english=english, art=art)


def _rows(body: dict) -> list[tuple]:
    return [(i["class_name"], i["subject"], i["exam_type"], i["term"], i["status"], i["entered"], i["class_size"],
             i["pending_edit_request"]) for i in body["items"]]


def test_every_exam_is_listed_with_its_batch_state_in_order(client, school):
    r = client.get(URL, params=SESSION, headers=auth())
    assert r.status_code == 200
    body = r.json()
    assert body["session"] == "2026-27"
    assert _rows(body) == [
        ("8th", "English", "P.T. First", 1, "submitted", 2, 2, True),
        ("8th", "Mathematics", "P.T. First", 1, "draft", 1, 2, False),
        ("8th", "Mathematics", "Half Yearly", 2, "none", 0, 2, False),
        ("8th", "Art", "Term 1 Grade", None, "draft", 1, 2, False),
        ("10th", "Science", "P.T. First", 1, "none", 0, 1, False),
    ]
    assert body["totals"] == {"draft": 2, "submitted": 1, "missing": 2}
    english, not_started = body["items"][0], body["items"][2]
    assert english["revision"] == 3 and english["updated_at"] is not None
    assert not_started["revision"] == 0 and not_started["updated_at"] is None


def test_the_super_admin_and_one_class_filter(client, school):
    assert _rows(client.get(URL, params=SESSION, headers=auth("super_admin")).json())[0][:2] == ("8th", "English")
    only_10th = client.get(URL, params={**SESSION, "class": "10th"}, headers=auth()).json()
    assert _rows(only_10th) == [("10th", "Science", "P.T. First", 1, "none", 0, 1, False)]
    assert only_10th["totals"] == {"draft": 0, "submitted": 0, "missing": 1}


def test_teachers_see_only_their_own_classes(client, school):
    teacher = auth("staff", ["10th"])
    assert {i["class_name"] for i in client.get(URL, params=SESSION, headers=teacher).json()["items"]} == {"10th"}
    assert client.get(URL, params={**SESSION, "class": "10th"}, headers=teacher).status_code == 200
    outside = client.get(URL, params={**SESSION, "class": "8th"}, headers=teacher)
    assert outside.status_code == 403 and outside.json()["detail"] == "Class not in scope"
    nobody = client.get(URL, params=SESSION, headers=auth("staff", []))
    assert nobody.status_code == 200
    assert nobody.json() == {"session": "2026-27", "items": [], "totals": {"draft": 0, "submitted": 0, "missing": 0}}


def test_either_marks_menu_opens_the_summary(client, school):
    refused = client.get(URL, params=SESSION, headers=auth("staff", ["8th"], menus=NO_MARKS_MENUS))
    assert refused.status_code == 403
    assert refused.json()["detail"] == ("Your account doesn't have access to marks entry or results. "
                                        "Ask an admin to enable it.")
    for menus in (["marks-entry"], ["marks-results"], ["marks-entry", "marks-results"]):
        assert client.get(URL, params=SESSION, headers=auth("staff", ["8th"], menus=menus)).status_code == 200


def test_an_unknown_or_missing_session_is_refused(client, school):
    r = client.get(URL, params={"session": "2030-31"}, headers=auth())
    assert r.status_code == 422 and "'2030-31' is not an academic session" in r.json()["detail"]
    assert client.get(URL, headers=auth()).status_code == 422


def test_the_other_session_has_its_own_progress(client, school):
    rows = _rows(client.get(URL, params={"session": "2025-26", "class": "8th"}, headers=auth()).json())
    assert [r[2:6] for r in rows if r[4] != "none"] == [("Half Yearly", 2, "draft", 1)]


def test_pending_flag_follows_the_request_queue(client, db, school):
    queue = client.get("/api/admin/marks-edit-requests", headers=auth("super_admin")).json()["items"]
    pending_id = next(r["id"] for r in queue if r["status"] == "pending")
    assert client.post(f"/api/admin/marks-edit-requests/{pending_id}/approve",
                       headers=auth("super_admin")).status_code == 200
    english = client.get(URL, params={**SESSION, "class": "8th"}, headers=auth()).json()["items"][0]
    assert (english["status"], english["pending_edit_request"], english["revision"]) == ("draft", False, 4)


def test_an_optional_subject_counts_only_the_students_who_take_it(client, db):
    academic_session(db, "2026-27")
    taker = student(db, name="Asha Kaur", class_name="11th", roll_no="1")
    other = student(db, name="Ravi Kumar", class_name="11th", roll_no="2")
    maths = subject(db, "11th", "Mathematics", [("P.T. First", 50, 1)])
    maths.is_optional = True
    db.add(SubjectEnrollment(class_subject_id=maths.id, student_id=taker.id))
    subject(db, "11th", "English", [("P.T. First", 50, 1)], order_index=1)
    # Ravi's mark was saved before Mathematics became optional for him.
    batch(db, "11th", "Mathematics", "P.T. First", max_marks=50, marks={taker.id: 40, other.id: 30})
    db.commit()
    rows = _rows(client.get(URL, params={**SESSION, "class": "11th"}, headers=auth()).json())
    assert [(r[1], r[4], r[5], r[6]) for r in rows] == [("Mathematics", "draft", 1, 1), ("English", "none", 0, 2)]
