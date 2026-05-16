from sqlalchemy import BigInteger, String, DateTime, Date, Numeric, Enum, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date
from decimal import Decimal
from ..db import Base
from .record_status import RecordStatus, _status_values


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    father: Mapped[str] = mapped_column(String(120), nullable=False)
    mother: Mapped[str] = mapped_column(String(120), nullable=False)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    village: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    aadhar: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    alt_phone: Mapped[str] = mapped_column(String(20), nullable=False, default="N/A")
    religion: Mapped[str] = mapped_column(String(80), nullable=False, default="N/A")
    prev_school: Mapped[str] = mapped_column(String(200), nullable=False, default="N/A")
    bank_name: Mapped[str] = mapped_column(String(120), nullable=False, default="N/A")
    bank_acc: Mapped[str] = mapped_column(String(40), nullable=False, default="N/A")
    bank_ifsc: Mapped[str] = mapped_column(String(20), nullable=False, default="N/A")
    annual_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    class_name: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # Ledger sequence number (e.g. 421). Optional; admin assigns when known.
    admission_no: Mapped[int | None] = mapped_column(nullable=True)
    # Auto-derived `KIS/{year}/{admission_no:04d}` — UNIQUE across all students.
    admission_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Class-scoped roll number — UNIQUE (class_name, roll_no) via composite index.
    roll_no: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    added_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    updated_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")

    # Soft-delete workflow columns (see backend/app/models/record_status.py).
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, values_callable=_status_values, native_enum=False, length=20),
        nullable=False,
        default=RecordStatus.active,
        server_default=RecordStatus.active.value,
        index=True,
    )
    delete_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delete_requested_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    delete_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
