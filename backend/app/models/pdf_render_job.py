import enum
from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class RenderJobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"


def _status_values(obj):
    return [e.value for e in obj]


class PdfRenderJob(Base):
    """One bulk render request (migration 0017). A detached runner process
    renders the students one by one and updates progress after each."""
    __tablename__ = "pdf_render_jobs"
    __table_args__ = (Index("ix_pdf_render_jobs_template_created", "template_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("pdf_templates.id", ondelete="CASCADE"), nullable=False
    )
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    # Persist .value, not the attribute name (Gotcha #8).
    status: Mapped[RenderJobStatus] = mapped_column(
        Enum(RenderJobStatus, values_callable=_status_values, native_enum=False, length=12),
        nullable=False, default=RenderJobStatus.queued, server_default=RenderJobStatus.queued.value,
    )
    include_drafts: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    force: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("0"))
    student_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    done_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    results: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    worker_pid: Mapped[int | None] = mapped_column(Integer, nullable=True)
