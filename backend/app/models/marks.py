from sqlalchemy import BigInteger, String, Integer, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from ..db import Base


class Marks(Base):
    __tablename__ = "marks"
    __table_args__ = (Index("ix_marks_class_exam", "class_name", "exam_type"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    class_name: Mapped[str] = mapped_column(String(20), nullable=False)
    exam_type: Mapped[str] = mapped_column(String(60), nullable=False)
    subject: Mapped[str] = mapped_column(String(60), nullable=False)
    marks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_marks: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    session: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    saved_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
