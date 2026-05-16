from sqlalchemy import BigInteger, String, DateTime, Date, ForeignKey, Enum, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
import enum
from ..db import Base


class AttendanceStatus(str, enum.Enum):
    P = "P"
    A = "A"
    L = "L"


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("class_name", "date", name="uq_class_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    class_name: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    updated_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    records: Mapped[list["AttendanceRecord"]] = relationship(
        "AttendanceRecord", cascade="all, delete-orphan", back_populates="attendance", lazy="selectin"
    )


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    attendance_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("attendance.id", ondelete="CASCADE"), primary_key=True
    )
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), nullable=False)

    attendance: Mapped[Attendance] = relationship("Attendance", back_populates="records")
