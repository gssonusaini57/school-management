from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from time import time
from ..deps import db_dep, current_user, require_admin, CurrentUser, assert_class_allowed
from ..schemas.fee import FeeCreate, FeeOut
from ..models.fee import FeePayment
from ..models.student import Student
from ..events import broker

router = APIRouter(prefix="/fees", tags=["fees"])


@router.get("", response_model=list[FeeOut])
def list_fees(
    class_name: str | None = Query(default=None, alias="class"),
    month: str | None = None,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(db_dep),
):
    stmt = select(FeePayment)
    if class_name:
        assert_class_allowed(user, class_name)
        stmt = stmt.where(FeePayment.class_name == class_name)
    if month:
        stmt = stmt.where(FeePayment.month == month)
    rows = db.execute(stmt.order_by(FeePayment.created_at.desc())).scalars().all()
    return rows


@router.post("", response_model=FeeOut, status_code=201)
def create_fee(
    payload: FeeCreate,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    student = db.get(Student, payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    receipt = payload.receipt_no or f"RC{int(time()*1000)}"
    fee = FeePayment(
        student_id=payload.student_id,
        student_name=student.name,
        class_name=payload.class_name,
        month=payload.month,
        year=payload.year,
        amount=payload.amount,
        date=payload.date,
        receipt_no=receipt,
        saved_by=user.name,
    )
    db.add(fee)
    db.commit()
    db.refresh(fee)
    broker.publish("fees", "upsert", id=fee.id)
    broker.publish("dashboard", "fees_changed")
    return fee


@router.delete("/{fid}", status_code=204)
def delete_fee(fid: int, user: CurrentUser = Depends(require_admin), db: Session = Depends(db_dep)):
    fee = db.get(FeePayment, fid)
    if not fee:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(fee)
    db.commit()
    broker.publish("fees", "delete", id=fid)
    broker.publish("dashboard", "fees_changed")
