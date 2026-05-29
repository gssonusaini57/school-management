from sqlalchemy import BigInteger, String, Integer, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from ..db import Base


class Marks(Base):
    __tablename__ = "marks"
    __table_args__ = (
        Index("ix_marks_class_exam", "class_name", "exam_type"),
        Index("ix_marks_batch", "batch_id"),
        # Composite unique on (batch_id, student_id) enforces the upsert contract
        # for the new batch-driven flow. MySQL treats NULL as distinct in unique
        # indexes, so legacy rows (batch_id IS NULL) are unaffected.
        UniqueConstraint("batch_id", "student_id", name="uq_marks_batch_student"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Nullable: pre-existing legacy rows + CSV bulk-import rows stay free-form.
    # New writes from /marks/batches always populate this.
    batch_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("marks_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    class_name: Mapped[str] = mapped_column(String(20), nullable=False)
    exam_type: Mapped[str] = mapped_column(String(60), nullable=False)
    subject: Mapped[str] = mapped_column(String(60), nullable=False)
    marks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_marks: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    session: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    saved_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
