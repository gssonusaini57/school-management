from datetime import date

from app.models.record_status import RecordStatus

from .conftest import auth
from .factories import attendance_day, student


def test_attendance_monthly_counts_half_days_and_skips_holidays(client, db):
    s1 = student(db, name="A", roll_no="1")
    s2 = student(db, name="B", roll_no="2")
    s3 = student(db, name="C", roll_no="3")
    s4 = student(db, name="D", roll_no="4")
    attendance_day(db, "8th", date(2026, 10, 1), {s1.id: "P", s2.id: "A", s3.id: "H", s4.id: "L"})
    attendance_day(db, "8th", date(2026, 10, 2), is_holiday=True)
    db.commit()
    rows = client.get("/api/reports/attendance-monthly", headers=auth("admin")).json()
    assert rows == [{"class": "8th", "date": "2026-10-01", "present": 1, "absent": 1, "leave": 1, "half_day": 1}]


def test_class_wise_excludes_archived_students(client, db):
    student(db, name="Active", roll_no="1")
    student(db, name="Gone", roll_no="2", status=RecordStatus.deleted)
    db.commit()
    rows = client.get("/api/reports/class-wise", headers=auth("admin")).json()
    assert [s["name"] for s in rows[0]["students"]] == ["Active"]
