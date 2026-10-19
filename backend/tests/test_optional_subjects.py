"""Optional subjects (migration 0020): 11th/12th Mathematics counts only for the students who take it."""
from types import SimpleNamespace as NS

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from app.events import broker
from app.models.class_subject import SubjectCategory, SubjectExamComponent
from app.models.marks import Marks
from app.models.marks_batch import MarksBatch, MarksBatchStatus
from app.models.record_status import RecordStatus
from app.models.subject_enrollment import SubjectEnrollment
from app.pdf.render_or_cache import report_card_payload
from app.services.report_cards import gather_class_inputs
from app.services.results import (
    RESULTS_ENGINE_VERSION, StudentResult, aggregate_class_results, rank_students,
)

from .conftest import auth
from .factories import academic_session, batch, report_card_template, student, subject
from .test_migration_0016 import _load

SUPER = auth("super_admin")
SUBMITTED = MarksBatchStatus.submitted


# ── fixtures ────────────────────────────────────────────────────────────
@pytest.fixture()
def eleventh(db):
    """English for everyone; Mathematics and Music optional, taken by Asha only."""
    academic_session(db, "2026-27")
    a = student(db, name="Asha Kaur", class_name="11th", roll_no="1")
    b = student(db, name="Ravi Kumar", class_name="11th", roll_no="2")
    c = student(db, name="Simran Kaur", class_name="11th", roll_no="3")
    gone = student(db, name="Archived Kid", class_name="11th", roll_no="4", status=RecordStatus.deleted)
    other = student(db, name="Other Class", class_name="12th", roll_no="1")
    english = subject(db, "11th", "English", [("P.T. First", 50, 1)])
    maths = subject(db, "11th", "Mathematics", [("P.T. First", 50, 1)], order_index=1)
    music = subject(db, "11th", "Music", [("Term 1 Grade", 0, 1)], category=SubjectCategory.grading, order_index=10)
    for cs in (maths, music):
        cs.is_optional = True
        db.add(SubjectEnrollment(class_subject_id=cs.id, student_id=a.id))
    db.commit()
    return NS(a=a, b=b, c=c, gone=gone, other=other, english=english, maths=maths, music=music)


def _rows(db, **where):
    db.expire_all()
    return {m.student_id: m.marks for m in db.query(Marks).filter_by(**where)}


# ── migration ───────────────────────────────────────────────────────────
def test_migration_adds_and_removes_the_flag_and_the_table(engine, db):
    subject(db, "11th", "Mathematics", [("P.T. First", 50, 1)])
    db.commit()
    migration = _load("0020_optional_subjects")
    assert (migration.revision, migration.down_revision) == ("0020_optional_subjects", "0019_clear_v1_card_overrides")
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE subject_enrollments"))
        conn.execute(text("ALTER TABLE class_subjects DROP COLUMN is_optional"))
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
        insp = inspect(conn)
        assert "subject_enrollments" in insp.get_table_names()
        assert {u["name"] for u in insp.get_unique_constraints("subject_enrollments")} == {"uq_subject_enrollment"}
        assert {i["name"] for i in insp.get_indexes("subject_enrollments")} >= {"ix_subject_enrollments_student_id"}
        assert conn.execute(text("SELECT is_optional FROM class_subjects")).scalar_one() == 0   # existing rows: not optional
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
        insp = inspect(conn)
        assert "subject_enrollments" not in insp.get_table_names()
        assert "is_optional" not in {c["name"] for c in insp.get_columns("class_subjects")}
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()                         # and back up again
        assert "subject_enrollments" in inspect(conn).get_table_names()


# ── enrolment endpoints ─────────────────────────────────────────────────
def test_enrollments_get_is_scoped_to_the_class(client, eleventh):
    url = f"/api/class-subjects/{eleventh.maths.id}/enrollments"
    body = {"class_subject_id": eleventh.maths.id, "class_name": "11th", "subject_name": "Mathematics",
            "is_optional": True, "student_ids": [eleventh.a.id]}
    assert client.get(url, headers=auth("staff", ["11th"])).json() == body
    assert client.get(url, headers=auth("admin")).json() == body
    assert client.get(url, headers=auth("staff", ["8th"])).status_code == 403
    assert client.get(url).status_code == 401
    assert client.get("/api/class-subjects/999999/enrollments", headers=SUPER).status_code == 404


def test_enrollments_put_is_super_admin_only_and_replaces_the_set(client, db, eleventh, monkeypatch):
    published = []
    monkeypatch.setattr(broker, "publish", lambda channel, event, **kw: published.append((channel, event, kw)))
    url = f"/api/class-subjects/{eleventh.maths.id}/enrollments"
    for role in ("admin", "staff"):
        assert client.put(url, json={"student_ids": []}, headers=auth(role, ["11th"])).status_code == 403
    r = client.put(url, json={"student_ids": [eleventh.c.id, eleventh.b.id, eleventh.c.id]}, headers=SUPER)
    assert r.status_code == 200
    assert r.json()["student_ids"] == sorted([eleventh.b.id, eleventh.c.id])
    db.expire_all()
    stored = {e.student_id for e in db.query(SubjectEnrollment).filter_by(class_subject_id=eleventh.maths.id)}
    assert stored == {eleventh.b.id, eleventh.c.id}                   # Asha removed, two added
    assert published == [("class_subjects", "upsert", {"id": eleventh.maths.id})]
    assert client.put(url, json={"student_ids": []}, headers=SUPER).json()["student_ids"] == []


def test_enrollments_put_refuses_students_who_are_not_active_in_the_class(client, db, eleventh):
    url = f"/api/class-subjects/{eleventh.maths.id}/enrollments"
    r = client.put(url, json={"student_ids": [eleventh.a.id, eleventh.gone.id, eleventh.other.id, 999999]},
                   headers=SUPER)
    assert r.status_code == 422
    assert r.json()["detail"] == ("Archived Kid (archived), Other Class (12th) and student #999999 are not "
                                  "active students of 11th. Reload the page and tick the students again.")
    r = client.put(url, json={"student_ids": [eleventh.other.id]}, headers=SUPER)
    assert r.json()["detail"].startswith("Other Class (12th) is not an active student of 11th.")
    db.expire_all()
    assert [e.student_id for e in db.query(SubjectEnrollment).filter_by(class_subject_id=eleventh.maths.id)] \
        == [eleventh.a.id]                                             # nothing changed


def test_subject_responses_carry_is_optional_and_enrolled_ids(client, db, eleventh, monkeypatch):
    listed = {s["subject_name"]: s for s in client.get("/api/class-subjects", params={"class": "11th"},
                                                         headers=auth("staff", ["11th"])).json()}
    assert (listed["English"]["is_optional"], listed["English"]["enrolled_student_ids"]) == (False, [])
    assert (listed["Mathematics"]["is_optional"], listed["Mathematics"]["enrolled_student_ids"]) == (True, [eleventh.a.id])
    detail = client.get(f"/api/class-subjects/{eleventh.maths.id}", headers=auth("admin")).json()
    assert detail["is_optional"] is True and detail["enrolled_student_ids"] == [eleventh.a.id]
    assert detail["components"][0]["component_name"] == "P.T. First"

    published = []
    monkeypatch.setattr(broker, "publish", lambda channel, event, **kw: published.append((channel, event, kw)))
    url = f"/api/class-subjects/{eleventh.maths.id}"
    assert client.patch(url, json={"is_optional": False}, headers=auth("admin")).status_code == 403
    r = client.patch(url, json={"is_optional": False}, headers=SUPER)
    assert r.status_code == 200
    assert r.json()["is_optional"] is False and r.json()["enrolled_student_ids"] == [eleventh.a.id]  # stored set kept
    assert published == [("class_subjects", "upsert", {"id": eleventh.maths.id})]
    r = client.post("/api/class-subjects", json={"class_name": "12th", "subject_name": "Mathematics", "is_optional": True},
                    headers=SUPER)
    assert r.status_code == 201 and r.json()["is_optional"] is True and r.json()["enrolled_student_ids"] == []

    # A student who moved to another class no longer shows; the next save drops the row.
    eleventh.a.class_name = "12th"
    db.commit()
    assert client.get(f"{url}/enrollments", headers=SUPER).json()["student_ids"] == []
    client.put(f"{url}/enrollments", json={"student_ids": [eleventh.b.id]}, headers=SUPER)
    db.expire_all()
    assert [e.student_id for e in db.query(SubjectEnrollment).filter_by(class_subject_id=eleventh.maths.id)] \
        == [eleventh.b.id]


def test_deleting_the_subject_removes_its_enrolments(client, db, eleventh):
    maths_id = eleventh.maths.id
    assert db.query(SubjectEnrollment).filter_by(class_subject_id=maths_id).count() == 1
    assert client.delete(f"/api/class-subjects/{maths_id}", headers=SUPER).status_code == 204
    db.expire_all()
    assert db.query(SubjectEnrollment).filter_by(class_subject_id=maths_id).count() == 0


# ── marks entry ─────────────────────────────────────────────────────────
def _form(subject_name, items, exam="P.T. First", max_marks=50, **extra):
    return {"class_name": "11th", "subject": subject_name, "exam_type": exam, "session": "2026-27",
            "max_marks": max_marks, "items": items, **extra}


def test_marks_save_refuses_a_student_who_does_not_take_the_subject(client, db, eleventh):
    e = eleventh
    r = client.post("/api/marks/batches", headers=auth("staff", ["11th"]), json=_form("Mathematics", [
        {"student_id": e.a.id, "marks": 40}, {"student_id": e.b.id, "marks": 30}], base_batch_id=None))
    assert r.status_code == 422
    assert r.json()["detail"] == ("Ravi Kumar doesn't take Mathematics (an optional subject). "
                                  "Ask the super-admin to tick them on Class Subjects.")
    r = client.post("/api/marks/batches", headers=SUPER, json=_form("Mathematics", [
        {"student_id": e.c.id, "marks": 1}, {"student_id": e.b.id, "marks": 0}]))
    assert r.json()["detail"].startswith("Ravi Kumar and Simran Kaur don't take Mathematics (an optional subject).")
    r = client.post("/api/marks/batches", headers=SUPER, json=_form(
        "Music", [{"student_id": e.b.id, "grade": "A1"}], exam="Term 1 Grade", max_marks=0))
    assert r.status_code == 422 and "doesn't take Music" in r.json()["detail"]
    assert db.query(MarksBatch).count() == 0
    # Everyone takes English.
    r = client.post("/api/marks/batches", headers=SUPER, json=_form("English", [{"student_id": e.b.id, "marks": 30}]))
    assert r.status_code == 200


def test_marks_save_drops_blank_rows_and_never_prunes_students_who_do_not_take_it(client, db, eleventh):
    e = eleventh
    old = batch(db, "11th", "Mathematics", "P.T. First", max_marks=50, marks={e.a.id: 10, e.b.id: 20})  # Ravi's row predates the enrolment
    db.commit()
    loaded = client.get("/api/marks/batches", headers=SUPER, params={
        "class": "11th", "subject": "Mathematics", "exam_type": "P.T. First", "session": "2026-27"}).json()
    r = client.post("/api/marks/batches", headers=SUPER, json=_form(
        "Mathematics", [{"student_id": e.a.id, "marks": 30}, {"student_id": e.b.id}],
        base_batch_id=loaded["id"], base_revision=loaded["revision"]))
    assert r.status_code == 200
    assert _rows(db, batch_id=old.id) == {e.a.id: 30, e.b.id: 20}
    # An old app (no base_batch_id) that never showed Ravi isn't "removing" his row either.
    r = client.post("/api/marks/batches", headers=SUPER, json=_form("Mathematics", [{"student_id": e.a.id, "marks": 31}]))
    assert r.status_code == 200
    assert _rows(db, batch_id=old.id) == {e.a.id: 31, e.b.id: 20}
    # Clearing a taker still works from a current screen.
    loaded = client.get("/api/marks/batches", headers=SUPER, params={
        "class": "11th", "subject": "Mathematics", "exam_type": "P.T. First", "session": "2026-27"}).json()
    r = client.post("/api/marks/batches", headers=SUPER, json=_form(
        "Mathematics", [], base_batch_id=loaded["id"], base_revision=loaded["revision"]))
    assert r.status_code == 200 and _rows(db, batch_id=old.id) == {e.b.id: 20}


def _csv(*lines):
    return "class_name,subject,exam_type,session,student_id,marks\n" + "\n".join(lines) + "\n"


def test_csv_import_refuses_marks_for_students_who_do_not_take_the_subject(client, db, eleventh):
    e = eleventh
    up = lambda body: client.post("/api/marks/bulk-import", files={"file": ("m.csv", body, "text/csv")},  # noqa: E731
                                  headers=auth("admin"))
    r = up(_csv(f"11th,Mathematics,P.T. First,2026-27,{e.a.id},40", f"11th,Mathematics,P.T. First,2026-27,{e.b.id},30",
                f"11th,English,P.T. First,2026-27,{e.b.id},30"))
    assert r.status_code == 422
    assert r.json()["detail"] == ("Ravi Kumar doesn't take Mathematics (an optional subject). "
                                  "Ask the super-admin to tick them on Class Subjects.")
    assert db.query(Marks).count() == 0
    # A blank row for a student who doesn't take it is skipped.
    r = up(_csv(f"11th,Mathematics,P.T. First,2026-27,{e.a.id},40", f"11th,Mathematics,P.T. First,2026-27,{e.b.id},"))
    assert r.json() == {"inserted": 1, "errors": [], "aborted": False}
    assert _rows(db, subject="Mathematics") == {e.a.id: 40}


# ── engine (pure) ───────────────────────────────────────────────────────
def comp(name, mx, term, order=0):
    return NS(component_name=name, max_marks=mx, term=term, order_index=order)


def subj(sid, name, comps, category="academic", order=0, optional=False):
    return NS(id=sid, subject_name=name, subject_name_pa=None, category=category, order_index=order,
              components=comps, is_optional=optional)


def mark(sid, subject_name, exam_type, value=0, grade=None):
    return NS(student_id=sid, subject=subject_name, exam_type=exam_type, marks=value, grade=grade)


ENGLISH = subj(1, "English", [comp("P.T. First", 50, 1)])
MATHS = subj(2, "Mathematics", [comp("P.T. First", 50, 1)], order=1, optional=True)


def run(rows, ids, enrolled, scope="term1", subjects=(ENGLISH, MATHS), **kw):
    return aggregate_class_results(class_name="11th", session="2026-27", scope=scope, class_subjects=list(subjects),
                                   marks_rows=rows, student_ids=ids, enrolled=enrolled, **kw)


def test_not_taken_is_left_out_of_totals_grade_and_completeness():
    rows = [mark(1, "English", "P.T. First", 40), mark(1, "Mathematics", "P.T. First", 45),
            mark(2, "English", "P.T. First", 30), mark(2, "Mathematics", "P.T. First", 20)]   # 2's Maths row is stale
    res = run(rows, [1, 2], {2: {1}})
    s1, s2 = res.students
    assert (s1.subjects[1].status, s1.subjects[1].obtained, s1.subjects[1].max) == ("complete", 45, 50)
    m2 = s2.subjects[1]
    assert (m2.status, m2.obtained, m2.max, m2.percentage, m2.grade) == ("not_taken", 0, 0, None, None)
    assert (m2.components, m2.components_total, m2.is_optional) == ([], 0, True)
    assert [c.status for c in m2.cells] == ["none"] * len(res.groups)
    assert (s1.total_obtained, s1.total_max, s1.percentage, s1.grade) == (85, 100, 85.0, "A2")
    assert (s2.total_obtained, s2.total_max, s2.percentage, s2.grade) == (30, 50, 60.0, "C1")
    assert res.complete is True                       # 2's missing Maths doesn't hold the class back
    assert [c.is_optional for c in res.subject_columns] == [False, True]
    assert RESULTS_ENGINE_VERSION == res.engine_version == 3


def test_a_subject_the_student_does_not_take_gives_no_marks_and_no_rank():
    res = run([mark(3, "Mathematics", "P.T. First", 45)], [3], {})          # nobody takes Maths
    st = res.students[0]
    assert (st.has_marks, st.rank, st.total_max, st.pass_status) == (False, None, 50, None)
    assert res.ranked_count == 0


def test_an_optional_subject_counts_for_takers_but_never_for_pass_or_promotion():
    rows = [mark(1, "English", "P.T. First", 40), mark(1, "Mathematics", "P.T. First", 10),   # Maths 20 %: failed
            mark(2, "English", "P.T. First", 40)]                                            # Maths not entered yet
    res = run(rows, [1, 2], {2: {1, 2}}, scope="annual")
    s1, s2 = res.students
    assert (s1.subjects[1].percentage, s1.total_obtained, s1.total_max, s1.grade) == (20.0, 50, 100, "C2")
    assert (s1.pass_status, s1.failed_subjects, s1.promotion) == ("pass", [], "Promoted")
    assert (s2.subjects[1].status, s2.grade) == ("missing", None)          # still counts toward completeness
    assert (s2.pass_status, s2.promotion) == ("pass", "Promoted")
    assert res.complete is False


def test_rank_is_by_exact_percentage_with_ties():
    rows = [mark(1, "English", "P.T. First", 40), mark(1, "Mathematics", "P.T. First", 45),   # 85/100
            mark(2, "English", "P.T. First", 44),                                            # 44/50 = 88 %
            mark(3, "English", "P.T. First", 44),                                            # 88 %
            mark(4, "English", "P.T. First", 44), mark(4, "Mathematics", "P.T. First", 44)]   # 88/100: ties 44/50
    res = run(rows, [1, 2, 3, 4, 5], {2: {1, 4}})
    assert [s.rank for s in res.students] == [4, 1, 1, 1, None]   # by total, 1 and 4 would have led


def test_rank_compares_exactly_not_on_rounded_percentages():
    def st(sid, obtained, mx):
        return StudentResult(student_id=sid, subjects=[], total_obtained=float(obtained), total_max=float(mx),
                             percentage=round(obtained / mx * 100, 2), grade=None, has_marks=True)
    students = [st(1, 6, 130), st(2, 37, 800), st(3, 88, 100), st(4, 44, 50)]
    assert students[0].percentage == students[1].percentage == 4.62      # 4.615… % and 4.625 %
    assert rank_students(students) == 4
    assert [s.rank for s in students] == [4, 3, 1, 1]


def test_drafts_of_an_optional_subject_nobody_takes_do_not_hold_the_class_back():
    rows = [mark(1, "English", "P.T. First", 40), mark(1, "Mathematics", "P.T. First", 40)]
    statuses = {("English", "P.T. First"): "submitted", ("Mathematics", "P.T. First"): "draft"}
    assert run(rows, [1], {}, batch_status_by_key=statuses).complete is True
    assert run(rows, [1], {2: {1}}, batch_status_by_key=statuses).has_drafts is True


# ── results API + report cards ──────────────────────────────────────────
def test_results_api_marks_not_taken_subjects(client, db, eleventh):
    e = eleventh
    batch(db, "11th", "English", "P.T. First", max_marks=50, status=SUBMITTED, marks={e.a.id: 40, e.b.id: 45})
    batch(db, "11th", "Mathematics", "P.T. First", max_marks=50, status=SUBMITTED, marks={e.a.id: 45, e.b.id: 50})
    db.commit()
    body = client.get("/api/marks/results", params={"class": "11th", "session": "2026-27", "scope": "term1"},
                      headers=auth("admin")).json()
    assert body["engine_version"] == 3
    assert {c["subject_name"]: c["is_optional"] for c in body["subject_columns"]} == \
        {"English": False, "Mathematics": True, "Music": True}
    by_id = {s["student_id"]: s for s in body["students"]}
    asha, ravi = by_id[e.a.id], by_id[e.b.id]
    ravi_maths = next(s for s in ravi["subjects"] if s["subject_name"] == "Mathematics")
    assert (ravi_maths["status"], ravi_maths["obtained"], ravi_maths["max"], ravi_maths["percentage"]) == \
        ("not_taken", 0, 0, None)
    assert (ravi["total_obtained"], ravi["total_max"], ravi["percentage"]) == (45, 50, 90.0)
    assert (asha["total_obtained"], asha["total_max"], asha["percentage"]) == (85, 100, 85.0)
    assert (ravi["rank"], asha["rank"]) == (1, 2)     # 90 % beats 85 % although 85 > 45 marks


def test_report_card_leaves_out_subjects_the_student_does_not_take(db, eleventh):
    e = eleventh
    batch(db, "11th", "English", "P.T. First", max_marks=50, status=SUBMITTED, marks={e.a.id: 40, e.b.id: 45})
    batch(db, "11th", "Mathematics", "P.T. First", max_marks=50, status=SUBMITTED, marks={e.a.id: 45, e.b.id: 50})
    g = batch(db, "11th", "Music", "Term 1 Grade", max_marks=0, status=SUBMITTED, marks={e.a.id: 0, e.b.id: 0})
    db.query(Marks).filter(Marks.batch_id == g.id).update({"grade": "A1"})
    t = report_card_template(db, "11th", term="Term I")
    t.scope = "term1"
    db.commit()
    inputs = gather_class_inputs(db, t)
    asha, _ = report_card_payload(inputs, e.a.id)
    ravi, _ = report_card_payload(inputs, e.b.id)
    assert [s["name"]["en"] for s in asha["subjects"]] == ["English", "Mathematics"]
    assert [s["name"]["en"] for s in asha["coScholastic"]] == ["Music"]
    assert [s["name"]["en"] for s in ravi["subjects"]] == ["English"]
    assert ravi["coScholastic"] == []
    assert (ravi["summary"]["total"], ravi["summary"]["max"], ravi["summary"]["incomplete"]) == (45, 50, False)
    assert (asha["summary"]["total"], asha["summary"]["max"]) == (85, 100)
    assert (ravi["summary"]["rank"], asha["summary"]["rank"]) == (1, 2)


def test_per_exam_card_drops_columns_only_an_untaken_subject_has(db, eleventh):
    e = eleventh
    db.add(SubjectExamComponent(class_subject_id=e.maths.id, component_name="Practical", max_marks=20,
                                order_index=1, term=1))
    batch(db, "11th", "English", "P.T. First", max_marks=50, status=SUBMITTED, marks={e.a.id: 40, e.b.id: 45})
    batch(db, "11th", "Mathematics", "Practical", max_marks=20, status=SUBMITTED, marks={e.a.id: 18})
    t = report_card_template(db, "11th", term="Term I")
    t.scope, t.layout = "term1", "components"
    db.commit()
    inputs = gather_class_inputs(db, t)
    asha, _ = report_card_payload(inputs, e.a.id)
    ravi, _ = report_card_payload(inputs, e.b.id)
    assert [g["key"] for g in asha["groups"]] == ["P.T. First", "Practical"]
    assert [[c["status"] for c in s["cells"]] for s in asha["subjects"]] == [["complete", "none"], ["missing", "complete"]]
    assert [g["key"] for g in ravi["groups"]] == ["P.T. First"]
    assert [[c["status"] for c in s["cells"]] for s in ravi["subjects"]] == [["complete"]]
