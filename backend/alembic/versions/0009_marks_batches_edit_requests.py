"""marks_batches + marks_edit_requests + marks.batch_id FK

Adds the draft → submit → lock → edit-request workflow.

Revision ID: 0009_marks_batches_edit_requests
Revises: 0008_class_subjects
Create Date: 2026-05-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0009_marks_batches_edit_requests"
down_revision: Union[str, None] = "0008_class_subjects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BATCH_STATUS_ENUM = sa.Enum("draft", "submitted", native_enum=False, length=12)
MER_STATUS_ENUM = sa.Enum("pending", "approved", "rejected", native_enum=False, length=10)
MER_ROLE_ENUM = sa.Enum("admin", "staff", native_enum=False, length=10)


def upgrade() -> None:
    op.create_table(
        "marks_batches",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("class_name", sa.String(20), nullable=False),
        sa.Column("subject", sa.String(60), nullable=False),
        sa.Column("exam_type", sa.String(80), nullable=False),
        sa.Column("session", sa.String(20), nullable=False),
        sa.Column("max_marks", sa.Integer, nullable=False, server_default="100"),
        sa.Column("status", BATCH_STATUS_ENUM, nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("created_by", sa.String(120), nullable=False, server_default=""),
        sa.Column("submitted_at", sa.DateTime, nullable=True),
        sa.Column("submitted_by", sa.String(120), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
            onupdate=sa.func.current_timestamp(),
        ),
        sa.UniqueConstraint(
            "class_name", "subject", "exam_type", "session",
            name="uq_marks_batches_quadruple",
        ),
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_marks_batches_class_session",
        "marks_batches",
        ["class_name", "session"],
    )

    op.create_table(
        "marks_edit_requests",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "batch_id", sa.BigInteger,
            sa.ForeignKey("marks_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requested_at", sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("requested_by", sa.String(120), nullable=False),
        sa.Column("requested_by_role", MER_ROLE_ENUM, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("status", MER_STATUS_ENUM, nullable=False, server_default="pending"),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("reviewed_by", sa.String(120), nullable=True),
        sa.Column("reject_reason", sa.Text, nullable=True),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_marks_edit_requests_batch_id", "marks_edit_requests", ["batch_id"])
    op.create_index(
        "ix_marks_edit_requests_pending",
        "marks_edit_requests",
        ["batch_id", "status"],
    )

    # Extend the existing `marks` table — nullable FK keeps legacy rows working.
    op.add_column(
        "marks",
        sa.Column("batch_id", sa.BigInteger, nullable=True),
    )
    op.create_foreign_key(
        "fk_marks_batch_id",
        "marks",
        "marks_batches",
        ["batch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_marks_batch", "marks", ["batch_id"])
    # MySQL treats NULL as distinct in unique indexes, so this only constrains
    # rows with a batch_id (legacy NULL rows stay tolerated).
    op.create_unique_constraint(
        "uq_marks_batch_student",
        "marks",
        ["batch_id", "student_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_marks_batch_student", "marks", type_="unique")
    op.drop_index("ix_marks_batch", table_name="marks")
    op.drop_constraint("fk_marks_batch_id", "marks", type_="foreignkey")
    op.drop_column("marks", "batch_id")

    op.drop_index("ix_marks_edit_requests_pending", table_name="marks_edit_requests")
    op.drop_index("ix_marks_edit_requests_batch_id", table_name="marks_edit_requests")
    op.drop_table("marks_edit_requests")

    op.drop_index("ix_marks_batches_class_session", table_name="marks_batches")
    op.drop_table("marks_batches")
