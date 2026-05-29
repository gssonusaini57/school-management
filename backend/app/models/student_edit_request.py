"""Edit-approval queue for student profile changes.

Mirrors the Session 9 soft-delete pattern: staff and admin PATCHes are queued
here as a diff (old/new pairs); super-admin approves to apply, or rejects with
a reason. Only one `pending` row may exist per student at a time (enforced in
the router; index `ix_student_pending` makes the lookup O(1)).

Super-admin PATCH applies directly — no row written here.
"""
import enum
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


class EditRequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


def _edit_status_values(obj):
    return [e.value for e in obj]


class EditRequestRole(str, enum.Enum):
    admin = "admin"
    staff = "staff"


def _edit_role_values(obj):
    return [e.value for e in obj]


class StudentEditRequest(Base):
    __tablename__ = "student_edit_requests"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    requested_by: Mapped[str] = mapped_column(String(120), nullable=False)
    requested_by_role: Mapped[EditRequestRole] = mapped_column(
        Enum(EditRequestRole, values_callable=_edit_role_values, native_enum=False, length=10),
        nullable=False,
    )
    # {field_name: {"old": <value>, "new": <value>}}
    changes: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[EditRequestStatus] = mapped_column(
        Enum(EditRequestStatus, values_callable=_edit_status_values, native_enum=False, length=10),
        nullable=False,
        default=EditRequestStatus.pending,
        server_default=EditRequestStatus.pending.value,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_student_edit_requests_pending", "student_id", "status"),
    )
