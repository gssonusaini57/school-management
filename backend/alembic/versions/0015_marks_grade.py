"""marks.grade: letter grades for grading subjects

Revision ID: 0015_marks_grade
Revises: 0014_academic_sessions
Create Date: 2026-10-18

Grading subjects (Computer, Physical Education, G.K., Drawing, …) have
max-0 exam components ("Term 1 Grade"). Teachers now enter a letter for them
in Marks Entry; it is stored in this column with `marks` kept at 0, so the
existing NOT NULL integer column and every client that reads it are unchanged.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0015_marks_grade"
down_revision: Union[str, None] = "0014_academic_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("marks", sa.Column("grade", sa.String(4), nullable=True))


def downgrade() -> None:
    op.drop_column("marks", "grade")
