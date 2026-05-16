"""PDF template / per-student data / cached blob models.

These three tables together implement the templated bulk-PDF flow:

- `pdf_templates`     — class-level config (one row per kind × class × session × term)
- `pdf_student_data`  — per-student fields scoped to a (kind, session, term) bucket
- `pdf_cache`         — generated PDF blobs keyed by (kind, student_id, template_id, version)

The class-level + per-student JSON shapes are validated by Pydantic schemas
in app/pdf/schemas.py before being persisted, so the JSON column is a thin
storage layer rather than a free-form bag.
"""
from sqlalchemy import (
    BigInteger, Integer, String, DateTime, ForeignKey, Enum, UniqueConstraint, JSON, func,
)
from sqlalchemy.dialects.mysql import LONGBLOB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import enum

from ..db import Base


class TemplateKind(str, enum.Enum):
    report_card = "report-card"
    pseb_admit_card = "pseb-admit-card"


# Tell SQLAlchemy to persist the .value (e.g. "pseb-admit-card") rather than
# the Python attribute name ("pseb_admit_card"). The MySQL column was created
# with those hyphenated values via the migration; without this callable the
# default attribute-name encoding would trigger
# `Data truncated for column 'kind'` (MySQL error 1265).
def _kind_values(obj):
    return [e.value for e in obj]


class PdfTemplate(Base):
    __tablename__ = "pdf_templates"
    __table_args__ = (
        # IFNULL(term,'') in the migration; SQLAlchemy unique can't express the
        # COALESCE so the migration adds a generated column for the unique key.
        UniqueConstraint("kind", "class_name", "session", "term_key", name="uq_pdf_template_scope"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kind: Mapped[TemplateKind] = mapped_column(
        Enum(TemplateKind, values_callable=_kind_values, native_enum=False, length=32),
        nullable=False,
    )
    class_name: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    session: Mapped[str] = mapped_column(String(16), nullable=False)
    term: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Mirror of `term` with NULL → '' so the unique constraint above works.
    term_key: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    created_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    updated_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")


class PdfStudentData(Base):
    __tablename__ = "pdf_student_data"
    __table_args__ = (
        UniqueConstraint("kind", "student_id", "session", "term_key", name="uq_pdf_student_data_scope"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kind: Mapped[TemplateKind] = mapped_column(
        Enum(TemplateKind, values_callable=_kind_values, native_enum=False, length=32),
        nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session: Mapped[str] = mapped_column(String(16), nullable=False)
    term: Mapped[str | None] = mapped_column(String(32), nullable=True)
    term_key: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    updated_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")


class PdfCache(Base):
    __tablename__ = "pdf_cache"
    __table_args__ = (
        UniqueConstraint(
            "kind", "student_id", "template_id", "template_version",
            name="uq_pdf_cache_scope",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kind: Mapped[TemplateKind] = mapped_column(
        Enum(TemplateKind, values_callable=_kind_values, native_enum=False, length=32),
        nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("pdf_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False, default="application/pdf")
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data: Mapped[bytes] = mapped_column(LONGBLOB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    created_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
