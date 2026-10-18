"""background render jobs for bulk report cards / admit cards

Revision ID: 0017_pdf_render_jobs
Revises: 0016_pdf_template_scope_layout
Create Date: 2026-10-18

A whole class's cards used to render inside one HTTP request, which can
outlive gunicorn's 120 s timeout. A job row records the request; a detached
runner process renders one student at a time, updating progress after each,
and the browser polls the row. Progress is polled over HTTP rather than
pushed over SSE because the SSE broker lives in one gunicorn worker.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0017_pdf_render_jobs"
down_revision: Union[str, None] = "0016_pdf_template_scope_layout"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pdf_render_jobs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("template_id", sa.BigInteger, sa.ForeignKey("pdf_templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_version", sa.Integer, nullable=False),
        sa.Column("requested_by", sa.String(120), nullable=False, server_default=""),
        sa.Column("status", sa.String(12), nullable=False, server_default="queued"),
        sa.Column("include_drafts", sa.Boolean, nullable=True),
        sa.Column("force", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("student_ids", sa.JSON, nullable=False),
        sa.Column("total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("done_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("results", sa.JSON, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("heartbeat_at", sa.DateTime, nullable=True),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("worker_pid", sa.Integer, nullable=True),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_pdf_render_jobs_template_created", "pdf_render_jobs", ["template_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_pdf_render_jobs_template_created", table_name="pdf_render_jobs")
    op.drop_table("pdf_render_jobs")
