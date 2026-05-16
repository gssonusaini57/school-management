"""pdf_templates + pdf_student_data + pdf_cache

Revision ID: 0002_pdf_templates_cache
Revises: 0001_initial
Create Date: 2026-05-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "0002_pdf_templates_cache"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# `term_key` is a non-null mirror of the nullable `term` so the unique
# constraint can include it (MySQL UNIQUE on a nullable column allows
# multiple NULLs, which would let two templates collide on no-term).
# The router writes both columns at once: term_key = term or "".


KIND_ENUM = sa.Enum("report-card", "pseb-admit-card", name="pdf_template_kind")


def upgrade() -> None:
    op.create_table(
        "pdf_templates",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("kind", KIND_ENUM, nullable=False),
        sa.Column("class_name", sa.String(32), nullable=False),
        sa.Column("session", sa.String(16), nullable=False),
        sa.Column("term", sa.String(32), nullable=True),
        sa.Column("term_key", sa.String(32), nullable=False, server_default=""),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("data", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_by", sa.String(120), nullable=False, server_default=""),
        sa.UniqueConstraint("kind", "class_name", "session", "term_key", name="uq_pdf_template_scope"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_pdf_templates_class_name", "pdf_templates", ["class_name"])

    op.create_table(
        "pdf_student_data",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("kind", KIND_ENUM, nullable=False),
        sa.Column(
            "student_id", sa.BigInteger,
            sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("session", sa.String(16), nullable=False),
        sa.Column("term", sa.String(32), nullable=True),
        sa.Column("term_key", sa.String(32), nullable=False, server_default=""),
        sa.Column("data", sa.JSON, nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_by", sa.String(120), nullable=False, server_default=""),
        sa.UniqueConstraint("kind", "student_id", "session", "term_key", name="uq_pdf_student_data_scope"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_pdf_student_data_student_id", "pdf_student_data", ["student_id"])

    op.create_table(
        "pdf_cache",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("kind", KIND_ENUM, nullable=False),
        sa.Column(
            "student_id", sa.BigInteger,
            sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "template_id", sa.BigInteger,
            sa.ForeignKey("pdf_templates.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("template_version", sa.Integer, nullable=False),
        sa.Column("mime_type", sa.String(64), nullable=False, server_default="application/pdf"),
        sa.Column("byte_size", sa.Integer, nullable=False, server_default="0"),
        sa.Column("data", mysql.LONGBLOB, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False, server_default=""),
        sa.UniqueConstraint(
            "kind", "student_id", "template_id", "template_version",
            name="uq_pdf_cache_scope",
        ),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_pdf_cache_student_id", "pdf_cache", ["student_id"])
    op.create_index("ix_pdf_cache_template_id", "pdf_cache", ["template_id"])


def downgrade() -> None:
    op.drop_index("ix_pdf_cache_template_id", table_name="pdf_cache")
    op.drop_index("ix_pdf_cache_student_id", table_name="pdf_cache")
    op.drop_table("pdf_cache")
    op.drop_index("ix_pdf_student_data_student_id", table_name="pdf_student_data")
    op.drop_table("pdf_student_data")
    op.drop_index("ix_pdf_templates_class_name", table_name="pdf_templates")
    op.drop_table("pdf_templates")
    # The Enum is shared by all three tables; SQLAlchemy doesn't auto-drop
    # named MySQL ENUMs (they live inline on the column), so nothing extra
    # to do — dropping the tables removes the inline enum definitions.
