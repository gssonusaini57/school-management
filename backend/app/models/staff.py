from sqlalchemy import BigInteger, Boolean, String, DateTime, ForeignKey, Enum, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from ..db import Base
from .record_status import RecordStatus, _status_values


class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    designation: Mapped[str] = mapped_column(String(80), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    employee_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    force_password_change: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    # Optional admin-set temporary password — a SECOND valid credential that does NOT
    # replace `password_hash`. Lets an admin/super-admin log in as this staff member
    # (e.g. to cover an absence) while the teacher keeps their own password. Cleared
    # by an admin from the web portal; no auto-expiry.
    temp_password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    temp_password_set_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    temp_password_set_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
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

    # Per-staff sidebar/route permission grants. List of MENU_KEYS keys
    # (see backend/app/permissions.py). Admin and super-admin ignore this
    # field — they always have full access.
    allowed_menus: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    classes: Mapped[list["StaffClass"]] = relationship(
        "StaffClass", cascade="all, delete-orphan", back_populates="staff", lazy="selectin"
    )


class StaffClass(Base):
    __tablename__ = "staff_classes"

    staff_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("staff.id", ondelete="CASCADE"), primary_key=True
    )
    class_name: Mapped[str] = mapped_column(String(20), primary_key=True)

    staff: Mapped[Staff] = relationship("Staff", back_populates="classes")
