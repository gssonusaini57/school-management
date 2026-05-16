"""admission_no + admission_id + roll_no on students

Revision ID: 0004_student_admission_roll
Revises: 0003_soft_delete_workflow
Create Date: 2026-05-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0004_student_admission_roll"
down_revision: Union[str, None] = "0003_soft_delete_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("students", sa.Column("admission_no", sa.Integer, nullable=True))
    op.add_column("students", sa.Column("admission_id", sa.String(32), nullable=True))
    op.add_column("students", sa.Column("roll_no", sa.String(20), nullable=True))
    # admission_id is globally unique across the school (it embeds the year).
    op.create_index(
        "ix_students_admission_id_unique",
        "students",
        ["admission_id"],
        unique=True,
    )
    # roll_no is unique only within a class — same roll can repeat across classes.
    op.create_index(
        "ix_students_class_rollno_unique",
        "students",
        ["class_name", "roll_no"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_students_class_rollno_unique", table_name="students")
    op.drop_index("ix_students_admission_id_unique", table_name="students")
    op.drop_column("students", "roll_no")
    op.drop_column("students", "admission_id")
    op.drop_column("students", "admission_no")
