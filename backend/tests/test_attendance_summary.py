from datetime import date

from app.services.attendance_summary import attendance_summary

from .conftest import auth
from .factories import attendance_day, student


def test_present_half_absent_leave_and_holidays(db):
    s = student(db)
    for d, st in ((1, "P"), (2, "H"), (3, "A"), (4, "L")):
        attendance_day(db, "8th", date(2026, 10, d), {s.id: st})
    attendance_day(db, "8th", date(2026, 10, 5), is_holiday=True)
    db.commit()
    out = attendance_summary(db, student_ids=[s.id], start=date(2026, 10, 1), end=date(2026, 10, 31),
                             today=date(2026, 12, 1))[s.id]
    assert (out.working_days, out.days_present, out.pct) == (4, 1.5, 37.5)
    assert out.counts == {"P": 1, "H": 1, "A": 1, "L": 1}


def test_mid_term_admission_counts_only_recorded_days(db):
    old = student(db, name="Old", roll_no="1")
    new = student(db, name="New", roll_no="2")
    attendance_day(db, "8th", date(2026, 10, 1), {old.id: "P"})
    attendance_day(db, "8th", date(2026, 10, 2), {old.id: "P", new.id: "P"})
    db.commit()
    out = attendance_summary(db, student_ids=[old.id, new.id], start=date(2026, 10, 1), end=date(2026, 10, 31),
                             today=date(2026, 12, 1))
    assert out[old.id].working_days == 2 and out[new.id].working_days == 1
    assert out[new.id].pct == 100.0


def test_range_is_clipped_to_today_and_empty_students_get_zeros(db):
    s = student(db)
    other = student(db, name="Nobody", roll_no="9")
    attendance_day(db, "8th", date(2026, 10, 1), {s.id: "P"})
    attendance_day(db, "8th", date(2026, 10, 20), {s.id: "A"})
    db.commit()
    out = attendance_summary(db, student_ids=[s.id, other.id], start=date(2026, 10, 1), end=date(2027, 3, 31),
                             today=date(2026, 10, 10))
    assert out[s.id].working_days == 1 and out[s.id].pct == 100.0
    assert out[other.id].working_days == 0 and out[other.id].pct is None


def test_records_from_a_previous_class_still_count(db):
    s = student(db, class_name="9th")
    attendance_day(db, "8th", date(2026, 4, 10), {s.id: "P"})      # before promotion to 9th
    attendance_day(db, "9th", date(2026, 7, 10), {s.id: "A"})
    db.commit()
    out = attendance_summary(db, student_ids=[s.id], start=date(2026, 4, 1), end=date(2027, 3, 31),
                             today=date(2026, 12, 1))[s.id]
    assert out.working_days == 2


# ── GET /attendance/today-summary ────────────────────────────────────────
TODAY = date(2026, 10, 19)


def _today_summary(client, monkeypatch, headers):
    monkeypatch.setattr("app.routers.attendance._today", lambda: TODAY)
    r = client.get("/api/attendance/today-summary", headers=headers)
    assert r.status_code == 200
    return r.json()


def test_today_summary_counts_a_half_day_as_half(client, db, monkeypatch):
    kids = [student(db, name=f"Kid {i}", roll_no=str(i)) for i in range(1, 7)]
    attendance_day(db, "8th", TODAY, dict(zip((k.id for k in kids), ("P", "P", "P", "H", "A", "L"))))
    attendance_day(db, "8th", date(2026, 10, 18), {kids[0].id: "A"})        # another day: not today
    db.commit()
    body = _today_summary(client, monkeypatch, auth())
    assert body == {"date": "2026-10-19", "total": 6, "present": 3, "absent": 1, "leave": 1, "half_day": 1,
                    "percent": 58.33}                                       # (3 + 0.5) / 6, still 2 dp


def test_today_summary_for_a_teacher_without_classes_is_zero(client, db, monkeypatch):
    attendance_day(db, "8th", TODAY, {student(db).id: "P"})
    attendance_day(db, "9th", TODAY, {student(db, class_name="9th").id: "A"})
    db.commit()
    assert _today_summary(client, monkeypatch, auth("staff", [])) == {
        "date": "2026-10-19", "total": 0, "present": 0, "absent": 0, "leave": 0, "half_day": 0, "percent": 0.0,
    }
    mine = _today_summary(client, monkeypatch, auth("staff", ["9th"]))
    assert (mine["total"], mine["absent"], mine["percent"]) == (1, 1, 0.0)
    everyone = _today_summary(client, monkeypatch, auth("admin"))
    assert (everyone["total"], everyone["percent"]) == (2, 50.0)
