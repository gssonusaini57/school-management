"""Marks-entry workflow: batch + edit-request models.

A `MarksBatch` represents one (class, subject, exam_type, session) tuple — the
unit a teacher fills in during marks entry. While `status = draft` the batch
is editable; flipping to `submitted` locks every row underneath. Only super-
admin can edit a submitted batch directly; admin/staff must enqueue a
`MarksEditRequest` (mirror of `student_edit_requests`) for super-admin
approval, which flips the batch back to draft.
"""
import enum
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, Text, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db import Base


class MarksBatchStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"


def _batch_status_values(obj):
    return [e.value for e in obj]


class MarksBatch(Base):
    __tablename__ = "marks_batches"
    __table_args__ = (
        UniqueConstraint(
            "class_name", "subject", "exam_type", "session",
            name="uq_marks_batches_quadruple",
        ),
        Index("ix_marks_batches_class_session", "class_name", "session"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    class_name: Mapped[str] = mapped_column(String(20), nullable=False)
    subject: Mapped[str] = mapped_column(String(60), nullable=False)
    exam_type: Mapped[str] = mapped_column(String(80), nullable=False)
    session: Mapped[str] = mapped_column(String(20), nullable=False)
    max_marks: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    status: Mapped[MarksBatchStatus] = mapped_column(
        Enum(MarksBatchStatus, values_callable=_batch_status_values, native_enum=False, length=12),
        nullable=False,
        default=MarksBatchStatus.draft,
        server_default=MarksBatchStatus.draft.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    created_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    edit_requests: Mapped[list["MarksEditRequest"]] = relationship(
        "MarksEditRequest",
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="MarksEditRequest.requested_at.desc()",
    )


# Reuse the same status/role enums shape as StudentEditRequest — distinct enums
# so a future divergence doesn't ripple across both queues.
class MarksEditRequestStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


def _mer_status_values(obj):
    return [e.value for e in obj]


class MarksEditRequestRole(str, enum.Enum):
    admin = "admin"
    staff = "staff"


def _mer_role_values(obj):
    return [e.value for e in obj]


class MarksEditRequest(Base):
    __tablename__ = "marks_edit_requests"
    __table_args__ = (
        Index("ix_marks_edit_requests_pending", "batch_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("marks_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    requested_by: Mapped[str] = mapped_column(String(120), nullable=False)
    requested_by_role: Mapped[MarksEditRequestRole] = mapped_column(
        Enum(MarksEditRequestRole, values_callable=_mer_role_values, native_enum=False, length=10),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[MarksEditRequestStatus] = mapped_column(
        Enum(MarksEditRequestStatus, values_callable=_mer_status_values, native_enum=False, length=10),
        nullable=False,
        default=MarksEditRequestStatus.pending,
        server_default=MarksEditRequestStatus.pending.value,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    batch: Mapped[MarksBatch] = relationship("MarksBatch", back_populates="edit_requests")
