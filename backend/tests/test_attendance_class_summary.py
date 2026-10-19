"""GET /api/attendance/class-summary: attendance per class over a date range,
behind the dashboard's marked / pending classes view."""
from datetime import date

import pytest

from app.constants import CLASSES
from app.models.record_status import RecordStatus

from .conftest import auth
from .factories import attendance_day, student

URL = "/api/attendance/class-summary"
TODAY = date(2026, 10, 19)
ZERO_TOTALS = {"class_size": 0, "present": 0, "absent": 0, "leave": 0, "half_day": 0,
               "records": 0, "percent": None, "classes_marked": 0, "classes_total": 0}


@pytest.fixture(autouse=True)
def pinned_today(monkeypatch):
    monkeypatch.setattr("app.routers.attendance._today", lambda: TODAY)


def _classes(body: dict) -> dict[str, dict]:
    return {c["class_name"]: c for c in body["classes"]}


def _three(db, class_name: str = "8th"):
    return [student(db, name=n, class_name=class_name, roll_no=str(i))
            for i, n in enumerate(("Asha Kaur", "Ravi Kumar", "Simran Kaur"), start=1)]


def test_admins_see_every_class_in_order_marked_or_not(client, db):
    student(db, class_name="8th")
    db.commit()
    for role in ("admin", "super_admin"):
        r = client.get(URL, headers=auth(role))
        assert r.status_code == 200
        body = r.json()
        assert (body["from"], body["to"]) == ("2026-10-19", "2026-10-19")   # both default to today
        assert [c["class_name"] for c in body["classes"]] == CLASSES
        assert _classes(body)["8th"] == {
            "class_name": "8th", "class_size": 1, "marked_days": 0, "holiday_days": 0,
            "present": 0, "absent": 0, "leave": 0, "half_day": 0, "records": 0, "percent": None,
        }
        assert body["totals"] == {**ZERO_TOTALS, "class_size": 1, "classes_total": 15}


def test_teachers_see_only_their_classes_in_class_order(client, db):
    for cls in ("8th", "9th", "Nursery"):
        attendance_day(db, cls, TODAY, {student(db, class_name=cls).id: "P"})
    db.commit()
    body = client.get(URL, headers=auth("staff", ["9th", "Nursery"])).json()
    assert [c["class_name"] for c in body["classes"]] == ["Nursery", "9th"]
    assert (body["totals"]["present"], body["totals"]["classes_marked"], body["totals"]["classes_total"]) == (2, 2, 2)
    # The "All" sentinel is expanded into every real class.
    assert [c["class_name"] for c in client.get(URL, headers=auth("staff", ["All"])).json()["classes"]] == CLASSES


def test_a_teacher_with_no_classes_gets_an_empty_list(client, db):
    attendance_day(db, "8th", TODAY, {student(db).id: "P"})
    db.commit()
    body = client.get(URL, headers=auth("staff", [])).json()
    assert body["classes"] == [] and body["totals"] == ZERO_TOTALS


def test_a_half_day_counts_as_half_and_percent_has_one_decimal(client, db):
    a, b, c = _three(db)
    attendance_day(db, "8th", date(2026, 10, 14), {a.id: "P", b.id: "H", c.id: "A"})
    attendance_day(db, "8th", date(2026, 10, 15), {a.id: "P", b.id: "L", c.id: "P"})
    attendance_day(db, "8th", date(2026, 10, 16), {a.id: "H", b.id: "P", c.id: "P"})
    t1 = student(db, name="Tara Devi", class_name="9th", roll_no="1")
    t2 = student(db, name="Vikram Singh", class_name="9th", roll_no="2")
    attendance_day(db, "9th", date(2026, 10, 16), {t1.id: "P", t2.id: "A"})
    db.commit()
    body = client.get(URL, params={"from": "2026-10-14", "to": "2026-10-16"}, headers=auth()).json()
    eighth, ninth = _classes(body)["8th"], _classes(body)["9th"]
    assert (eighth["present"], eighth["absent"], eighth["leave"], eighth["half_day"], eighth["records"]) == (5, 1, 1, 2, 9)
    assert eighth["percent"] == 66.7            # (5 + 0.5 × 2) / 9 = 66.67 %; leave is not present
    assert (eighth["marked_days"], eighth["class_size"]) == (3, 3)
    assert (ninth["percent"], ninth["marked_days"]) == (50.0, 1)
    totals = body["totals"]
    assert (totals["present"], totals["absent"], totals["leave"], totals["half_day"], totals["records"]) == (6, 2, 1, 2, 11)
    assert totals["percent"] == 63.6            # (6 + 1) / 11 = 63.64 %
    assert (totals["class_size"], totals["classes_marked"], totals["classes_total"]) == (5, 2, 15)


def test_holidays_are_counted_apart_and_left_out_of_the_counts(client, db):
    s = student(db, class_name="8th")
    attendance_day(db, "8th", date(2026, 10, 15), {s.id: "P"})
    attendance_day(db, "8th", date(2026, 10, 16), is_holiday=True)
    # A holiday that still carries records (a CSV import over a holiday) counts nothing either.
    attendance_day(db, "8th", date(2026, 10, 17), {s.id: "A"}, is_holiday=True)
    attendance_day(db, "9th", date(2026, 10, 16), is_holiday=True)
    db.commit()
    body = client.get(URL, params={"from": "2026-10-14"}, headers=auth()).json()
    eighth, ninth = _classes(body)["8th"], _classes(body)["9th"]
    assert (eighth["marked_days"], eighth["holiday_days"]) == (1, 2)
    assert (eighth["present"], eighth["absent"], eighth["records"], eighth["percent"]) == (1, 0, 1, 100.0)
    assert (ninth["marked_days"], ninth["holiday_days"], ninth["percent"]) == (0, 1, None)
    assert body["totals"]["classes_marked"] == 1   # a holiday is not a marked day


def test_the_range_is_inclusive_and_never_runs_past_today(client, db):
    s = student(db, class_name="8th")
    attendance_day(db, "8th", date(2026, 10, 9), {s.id: "A"})     # the day before the range
    attendance_day(db, "8th", date(2026, 10, 10), {s.id: "P"})    # first day
    attendance_day(db, "8th", TODAY, {s.id: "H"})                 # last day: today
    attendance_day(db, "8th", date(2026, 10, 20), {s.id: "A"})    # tomorrow, entered early
    db.commit()
    body = client.get(URL, params={"from": "2026-10-10", "to": "2026-10-31"}, headers=auth()).json()
    assert (body["from"], body["to"]) == ("2026-10-10", "2026-10-19")
    eighth = _classes(body)["8th"]
    assert (eighth["marked_days"], eighth["present"], eighth["half_day"], eighth["absent"]) == (2, 1, 1, 0)
    assert eighth["percent"] == 75.0


def test_bad_ranges_are_refused(client):
    h = auth()
    assert client.get(URL, params={"from": "2026-10-20"}, headers=h).status_code == 422          # after today
    assert client.get(URL, params={"from": "2026-10-12", "to": "2026-10-11"}, headers=h).status_code == 422
    assert client.get(URL, params={"to": "2026-10-11"}, headers=h).status_code == 422             # from defaults to today
    assert client.get(URL, params={"from": "not-a-date"}, headers=h).status_code == 422
    # 2026-07-20 .. 2026-10-19 is exactly 92 days; one more day is refused.
    assert client.get(URL, params={"from": "2026-07-20", "to": "2026-10-19"}, headers=h).status_code == 200
    r = client.get(URL, params={"from": "2026-07-19", "to": "2026-10-19"}, headers=h)
    assert r.status_code == 422 and "at most 92 days" in r.json()["detail"]
    # The limit is checked after 'to' stops at today.
    assert client.get(URL, params={"from": "2026-07-20", "to": "2027-03-31"}, headers=h).status_code == 200


def test_class_size_leaves_out_archived_students(client, db):
    student(db, name="Asha Kaur", class_name="8th", roll_no="1")
    student(db, name="Ravi Kumar", class_name="8th", roll_no="2", status=RecordStatus.pending_delete)
    student(db, name="Gone Away", class_name="8th", roll_no="3", status=RecordStatus.deleted)
    student(db, name="Tara Devi", class_name="9th", roll_no="1")
    db.commit()
    body = client.get(URL, headers=auth()).json()
    assert (_classes(body)["8th"]["class_size"], _classes(body)["9th"]["class_size"]) == (2, 1)
    assert body["totals"]["class_size"] == 3


def test_the_summary_needs_a_login(client):
    assert client.get(URL).status_code == 401
