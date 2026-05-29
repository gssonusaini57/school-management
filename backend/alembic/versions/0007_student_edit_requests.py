"""student_edit_requests queue (edit-approval workflow)

Revision ID: 0007_student_edit_requests
Revises: 0006_staff_allowed_menus
Create Date: 2026-05-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0007_student_edit_requests"
down_revision: Union[str, None] = "0006_staff_allowed_menus"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


STATUS_ENUM = sa.Enum("pending", "approved", "rejected", native_enum=False, length=10)
ROLE_ENUM = sa.Enum("admin", "staff", native_enum=False, length=10)


def upgrade() -> None:
    op.create_table(
        "student_edit_requests",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "student_id", sa.BigInteger,
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requested_at", sa.DateTime,
            server_default=sa.func.current_timestamp(), nullable=False,
        ),
        sa.Column("requested_by", sa.String(120), nullable=False),
        sa.Column("requested_by_role", ROLE_ENUM, nullable=False),
        sa.Column("changes", sa.JSON, nullable=False),
        sa.Column("status", STATUS_ENUM, nullable=False, server_default="pending"),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("reviewed_by", sa.String(120), nullable=True),
        sa.Column("reject_reason", sa.Text, nullable=True),
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_student_edit_requests_student_id",
        "student_edit_requests",
        ["student_id"],
    )
    op.create_index(
        "ix_student_edit_requests_pending",
        "student_edit_requests",
        ["student_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_student_edit_requests_pending", table_name="student_edit_requests")
    op.drop_index("ix_student_edit_requests_student_id", table_name="student_edit_requests")
    op.drop_table("student_edit_requests")
