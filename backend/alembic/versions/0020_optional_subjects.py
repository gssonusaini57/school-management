"""optional subjects: class_subjects.is_optional + subject_enrollments

Revision ID: 0020_optional_subjects
Revises: 0019_clear_v1_card_overrides
Create Date: 2026-10-19

In 11th and 12th, Mathematics is an additional subject taken by only a few
students, so it must count only for them. A subject marked `is_optional` is
taken only by the students listed in `subject_enrollments`; for everyone else
it is left out of marks entry, results and the report card. Existing subjects
start as not optional (the whole class takes them), so nothing changes until a
super-admin ticks a subject as optional.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0020_optional_subjects"
down_revision: Union[str, None] = "0019_clear_v1_card_overrides"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "class_subjects",
        sa.Column("is_optional", sa.Boolean, nullable=False, server_default=sa.text("0")),
    )
    op.create_table(
        "subject_enrollments",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "class_subject_id", sa.BigInteger,
            sa.ForeignKey("class_subjects.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "student_id", sa.BigInteger,
            sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False, server_default=""),
        sa.UniqueConstraint("class_subject_id", "student_id", name="uq_subject_enrollment"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_subject_enrollments_student_id", "subject_enrollments", ["student_id"])


def downgrade() -> None:
    # Dropping the table drops its indexes and FKs (dropping an index that backs
    # an FK first fails on MySQL with error 1553).
    op.drop_table("subject_enrollments")
    op.drop_column("class_subjects", "is_optional")
