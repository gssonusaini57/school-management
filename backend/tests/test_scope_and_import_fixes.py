"""A teacher with no classes sees no students; importing attendance onto a day
saved as a holiday makes it a working day again (otherwise every summary skips it)."""
from datetime import date

from app.models.attendance import Attendance

from .conftest import auth
from .factories import attendance_day, student


def test_a_teacher_with_no_classes_sees_no_students(client, db):
    student(db, class_name="8th")
    db.commit()
    r = client.get("/api/students", headers=auth("staff", classes=[]))
    assert r.status_code == 200
    assert r.json()["total"] == 0 and r.json()["items"] == []
    assert client.get("/api/students", headers=auth("staff", classes=["8th"])).json()["total"] == 1
    assert client.get("/api/students", headers=auth("admin")).json()["total"] == 1


def test_importing_attendance_onto_a_holiday_makes_it_a_working_day(client, db):
    s = student(db, class_name="8th")
    attendance_day(db, "8th", date(2026, 10, 16), {}, is_holiday=True)
    db.commit()
    csv = f"class_name,date,student_id,status\n8th,2026-10-16,{s.id},P\n"
    r = client.post("/api/attendance/bulk-import", files={"file": ("a.csv", csv, "text/csv")},
                    headers=auth("admin"))
    assert r.status_code == 201, r.text
    db.expire_all()
    day = db.query(Attendance).filter_by(class_name="8th", date=date(2026, 10, 16)).one()
    assert day.is_holiday is False
    assert len(day.records) == 1
