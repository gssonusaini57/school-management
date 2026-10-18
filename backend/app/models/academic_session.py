from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class AcademicSession(Base):
    """One school year ("2026-27") with its two term date ranges.

    Source of truth for the session list, the current session, and the date
    ranges attendance summaries and report cards count over (migration 0014).
    """
    __tablename__ = "academic_sessions"
    __table_args__ = (UniqueConstraint("session", name="uq_academic_sessions_session"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session: Mapped[str] = mapped_column(String(16), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    term1_start: Mapped[date] = mapped_column(Date, nullable=False)
    term1_end: Mapped[date] = mapped_column(Date, nullable=False)
    term2_start: Mapped[date] = mapped_column(Date, nullable=False)
    term2_end: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("0"), default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    updated_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
