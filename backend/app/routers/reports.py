from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from collections import defaultdict
from ..deps import db_dep, require_admin, CurrentUser
from ..models.student import Student
from ..models.staff import Staff
from ..models.fee import FeePayment
from ..models.attendance import Attendance, AttendanceRecord, AttendanceStatus

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/class-wise")
def class_wise(user: CurrentUser = Depends(require_admin), db: Session = Depends(db_dep)):
    rows = db.execute(select(Student).order_by(Student.class_name, Student.name)).scalars().all()
    grouped: dict[str, list[dict]] = defaultdict(list)
    for s in rows:
        grouped[s.class_name].append({
            "id": s.id, "name": s.name, "father": s.father,
            "dob": str(s.dob) if s.dob else "", "phone": s.phone,
        })
    return [{"class": k, "count": len(v), "students": v} for k, v in sorted(grouped.items())]


@router.get("/fee-summary")
def fee_summary(user: CurrentUser = Depends(require_admin), db: Session = Depends(db_dep)):
    rows = db.execute(
        select(FeePayment.month, func.sum(FeePayment.amount), func.count(FeePayment.id))
        .group_by(FeePayment.month)
    ).all()
    grand = sum((float(r[1] or 0) for r in rows), 0.0)
    return {
        "rows": [{"month": r[0], "total": float(r[1] or 0), "count": r[2]} for r in rows],
        "grand_total": grand,
    }


@router.get("/attendance-monthly")
def attendance_monthly(user: CurrentUser = Depends(require_admin), db: Session = Depends(db_dep)):
    out = []
    for a in db.execute(select(Attendance).order_by(Attendance.date.desc())).scalars().all():
        p = a_ = l_ = 0
        for r in a.records:
            if r.status == AttendanceStatus.P: p += 1
            elif r.status == AttendanceStatus.A: a_ += 1
            else: l_ += 1
        out.append({
            "class": a.class_name, "date": str(a.date),
            "present": p, "absent": a_, "leave": l_,
        })
    return out


@router.get("/staff-list")
def staff_list(user: CurrentUser = Depends(require_admin), db: Session = Depends(db_dep)):
    rows = db.execute(select(Staff).order_by(Staff.name)).scalars().all()
    return [{
        "id": s.id, "name": s.name, "designation": s.designation,
        "assigned_classes": [c.class_name for c in s.classes], "phone": s.phone,
    } for s in rows]
