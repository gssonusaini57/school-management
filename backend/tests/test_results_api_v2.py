"""GET /marks/results v2 and letter-grade entry through batches."""
from datetime import date

import pytest

from app.models.class_subject import SubjectCategory
from app.models.marks import Marks
from app.models.marks_batch import MarksBatchStatus

from .conftest import auth
from .factories import academic_session, attendance_day, batch, student, subject


@pytest.fixture()
def eighth(db):
    academic_session(db, "2026-27")
    s10 = student(db, name="Tenth Roll", roll_no="10")
    s2 = student(db, name="Second Roll", roll_no="2")
    s_none = student(db, name="No Roll", roll_no=None)
    s1 = student(db, name="First Roll", roll_no="1")
    subject(db, "8th", "Mathematics", [("P.T. First", 35, 1), ("P.T. Second", 35, 1), ("P.T. Third", 35, 2)])
    subject(db, "8th", "Computer", [("Term 1 Grade", 0, 1), ("Term 2 Grade", 0, 2)],
            category=SubjectCategory.grading, order_index=10)
    batch(db, "8th", "Mathematics", "P.T. First", status=MarksBatchStatus.submitted,
          marks={s1.id: 30, s2.id: 20, s10.id: 30})
    batch(db, "8th", "Mathematics", "P.T. Second", status=MarksBatchStatus.draft, marks={s1.id: 10})
    db.commit()
    return {"1": s1, "2": s2, "10": s10, "none": s_none}


def _get(client, **params):
    q = {"class": "8th", "session": "2026-27", "scope": "term1", **params}
    return client.get("/api/marks/results", params=q, headers=auth("admin"))


def test_natural_roll_order_and_ranks(client, eighth):
    body = _get(client).json()
    assert [s["roll_no"] for s in body["students"]] == ["1", "2", "10", None]
    ranks = {s["roll_no"]: s["rank"] for s in body["students"]}
    assert ranks == {"1": 1, "10": 2, "2": 3, None: None}   # 40, 30, 20; no marks → unranked
    assert body["class_size"] == 4 and body["ranked_count"] == 3


def test_drafts_included_by_default_and_flagged(client, eighth):
    body = _get(client).json()
    assert body["has_drafts"] is True and body["complete"] is False
    maths_col = next(c for c in body["subject_columns"] if c["subject_name"] == "Mathematics")
    assert maths_col["batch_status"] == "draft"
    first = body["students"][0]
    assert first["total_obtained"] == 40
    excl = _get(client, include_drafts="false").json()["students"][0]
    assert excl["total_obtained"] == 30 and excl["draft_components"] == 1


def test_per_exam_columns_and_components_returned(client, eighth):
    body = _get(client).json()
    assert [g["key"] for g in body["groups"]] == ["P.T. First", "P.T. Second"]
    maths = body["students"][0]["subjects"][0]
    assert [c["key"] for c in maths["cells"]] == ["P.T. First", "P.T. Second"]
    assert [c["component_name"] for c in maths["components"]] == ["P.T. First", "P.T. Second"]


def test_attendance_uses_the_session_term_dates(client, db, eighth):
    s1 = eighth["1"]
    attendance_day(db, "8th", date(2026, 5, 4), {s1.id: "P"})     # Term 1
    attendance_day(db, "8th", date(2026, 5, 5), {s1.id: "H"})     # Term 1
    attendance_day(db, "8th", date(2026, 10, 6), {s1.id: "A"})    # Term 2
    db.commit()
    body = _get(client).json()
    assert body["session_dates"] == {"start": "2026-04-01", "end": "2026-09-30"}
    att = body["students"][0]["attendance"]
    assert (att["working_days"], att["days_present"], att["pct"]) == (2, 1.5, 75.0)


def test_unknown_session_warns_instead_of_failing(client, eighth):
    body = _get(client, session="2030-31").json()
    assert body["session_dates"] is None
    assert any("not configured" in w for w in body["warnings"])


def test_staff_outside_class_forbidden(client, eighth):
    r = client.get("/api/marks/results", params={"class": "8th", "session": "2026-27"},
                   headers=auth("staff", ["5th"]))
    assert r.status_code == 403


def test_grading_batch_saves_letters(client, db, eighth):
    s1 = eighth["1"]
    body = {"class_name": "8th", "subject": "Computer", "exam_type": "Term 1 Grade", "session": "2026-27",
            "max_marks": 0, "items": [{"student_id": s1.id, "grade": " a1 "}]}
    r = client.post("/api/marks/batches", json=body, headers=auth("staff", ["8th"]))
    assert r.status_code == 200, r.text
    assert r.json()["items"][0]["grade"] == "A1" and r.json()["items"][0]["marks"] == 0
    res = _get(client).json()
    computer = next(s for s in res["students"][0]["subjects"] if s["subject_name"] == "Computer")
    assert computer["grade_letter"] == "A1" and computer["is_grading"] is True

    body["items"] = [{"student_id": s1.id, "grade": "Z"}]
    assert client.post("/api/marks/batches", json=body, headers=auth("admin")).status_code == 400


def test_batch_checks_component_and_its_max(client, eighth):
    s1 = eighth["1"]
    base = {"class_name": "8th", "subject": "Mathematics", "session": "2026-27",
            "items": [{"student_id": s1.id, "marks": 10}]}
    assert client.post("/api/marks/batches", json={**base, "exam_type": "Final", "max_marks": 35},
                       headers=auth("admin")).status_code == 400
    r = client.post("/api/marks/batches", json={**base, "exam_type": "P.T. Third", "max_marks": 40},
                    headers=auth("admin"))
    assert r.status_code == 400 and "Reload" in r.json()["detail"]
    missing = {**base, "exam_type": "P.T. Third", "max_marks": 35, "items": [{"student_id": s1.id}]}
    assert client.post("/api/marks/batches", json=missing, headers=auth("admin")).status_code == 400


def test_csv_import_accepts_letter_grades(client, db, eighth):
    s1 = eighth["1"]
    csv = ("class_name,subject,exam_type,session,student_id,marks,grade\n"
           f"8th,Computer,Term 1 Grade,2026-27,{s1.id},,b2\n")
    r = client.post("/api/marks/bulk-import", files={"file": ("m.csv", csv, "text/csv")}, headers=auth("admin"))
    assert r.json()["inserted"] == 1, r.json()
    db.expire_all()
    row = db.query(Marks).filter(Marks.subject == "Computer").one()
    assert (row.grade, row.marks) == ("B2", 0)


def test_meta_lists_reference_data(client):
    body = client.get("/api/meta", headers=auth("staff", ["8th"])).json()
    assert body["grade_letters"] == ["A1", "A2", "B1", "B2", "C1", "C2", "D"]
    assert body["houses"] == ["Ravidas", "Tagore", "Bhagat Singh", "Nanak"]
    assert "L.K.G" in body["classes"] and body["pass_pct"] == 33.0


def test_grades_only_once_a_subject_is_complete(client, eighth):
    """The table, its CSV and the app show only the grades the report card prints."""
    by_roll = {s["roll_no"]: s for s in _get(client).json()["students"]}
    maths = {roll: by_roll[roll]["subjects"][0] for roll in ("1", "10")}
    assert (maths["1"]["status"], maths["1"]["grade"]) == ("complete", "C1")      # 40 of 70, draft counted
    assert (maths["10"]["status"], maths["10"]["grade"]) == ("partial", None)     # P.T. Second not in yet
    assert by_roll["10"]["percentage"] == 42.86 and by_roll["10"]["grade"] is None
    assert by_roll["1"]["grade"] is None                                          # Computer's letter is missing
