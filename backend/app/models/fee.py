from sqlalchemy import BigInteger, String, DateTime, Date, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date
from decimal import Decimal
from ..db import Base


class FeePayment(Base):
    __tablename__ = "fee_payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    class_name: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    month: Mapped[str] = mapped_column(String(20), nullable=False)
    year: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    receipt_no: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    saved_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
