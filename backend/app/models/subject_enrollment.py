"""Students who take an optional class subject (migration 0020)."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class SubjectEnrollment(Base):
    """One student taking one optional subject of their class (e.g. 11th
    Mathematics as an additional subject). Only subjects marked
    `class_subjects.is_optional` read these rows; every other subject is taken
    by the whole class. Rows go with the subject or the student (FK CASCADE)."""
    __tablename__ = "subject_enrollments"
    __table_args__ = (
        UniqueConstraint("class_subject_id", "student_id", name="uq_subject_enrollment"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    class_subject_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("class_subjects.id", ondelete="CASCADE"), nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    created_by: Mapped[str] = mapped_column(String(120), nullable=False, default="", server_default="")
