"""result module: explicit term on exam components + marks-aware report-card cache

Revision ID: 0013_component_term
Revises: 0012_attendance_holiday_halfday
Create Date: 2026-06-07

Adds an explicit `term` (1 | 2 | NULL=both) to subject_exam_components so the
result aggregation can roll components up by Term 1 / Term 2 / Annual without
parsing component names at query time. Existing rows are backfilled from the
known KIS component-name patterns.

Also:
  - widens marks.exam_type 60 -> 80 to fit the longest component names
    (component_name / marks_batches.exam_type are already VARCHAR(80)).
  - adds pdf_cache.source_hash so a marks change auto-invalidates a cached
    report card (the cache key only tracks template.version today).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0013_component_term"
down_revision: Union[str, None] = "0012_attendance_holiday_halfday"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subject_exam_components",
        sa.Column("term", sa.SmallInteger(), nullable=True),
    )
    # Backfill Term 1. `Oral I` / `Term 1` matched exactly so they don't also
    # catch `Oral II` / `Term 10`; the prefix patterns cover the practical/
    # written splits (`Semester First — Written/Practical`, `Term 1 — Written`).
    op.execute(
        "UPDATE subject_exam_components SET term=1 WHERE term IS NULL AND ("
        "component_name LIKE 'P.T. First%' "
        "OR component_name LIKE 'P.T. Second%' "
        "OR component_name LIKE 'Semester First%' "
        "OR component_name LIKE 'Semester 1%' "       # manual edits e.g. 'Semester 1'
        "OR component_name = 'Oral I' "
        "OR component_name = 'Term 1' "
        "OR component_name = 'Term 1 Grade' "
        "OR component_name LIKE 'Term 1 —%'"
        ")"
    )
    # Backfill Term 2.
    op.execute(
        "UPDATE subject_exam_components SET term=2 WHERE term IS NULL AND ("
        "component_name LIKE 'P.T. Third%' "
        "OR component_name LIKE 'P.T. Fourth%' "
        "OR component_name LIKE 'Semester Second%' "
        "OR component_name LIKE 'Semester 2%' "       # manual edits e.g. 'Semester 2'
        "OR component_name = 'Oral II' "
        "OR component_name = 'Term 2' "
        "OR component_name = 'Term 2 Grade' "
        "OR component_name LIKE 'Term 2 —%'"
        ")"
    )

    # Component names can be up to 80 chars; marks.exam_type stores the
    # component name, so widen it to match (was 60).
    op.alter_column(
        "marks", "exam_type",
        existing_type=sa.String(60), type_=sa.String(80),
        existing_nullable=False,
    )

    # Marks-aware cache: NULL on existing rows so the first marks-hashed
    # lookup misses and re-renders, then stores the hash.
    op.add_column(
        "pdf_cache",
        sa.Column("source_hash", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pdf_cache", "source_hash")
    op.alter_column(
        "marks", "exam_type",
        existing_type=sa.String(80), type_=sa.String(60),
        existing_nullable=False,
    )
    op.drop_column("subject_exam_components", "term")
