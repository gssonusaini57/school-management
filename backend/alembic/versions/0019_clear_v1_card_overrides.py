"""report cards: clear the values the v1 editor had teachers type per student

Revision ID: 0019_clear_v1_card_overrides
Revises: 0018_marks_batch_revision
Create Date: 2026-10-19

The v1 report-card sheet (on prod since June) had hand-typed Att %, Rank and
Class size per student, because nothing was computed then. v2 computes them
and reads a stored value as an admin's override that beats the computed one,
so a stale rank would print as final (rank 1 of 8 in a class of 4), and a
rank or class size of 0 or an Att % over 100 fails v2's validation: the card
won't render and every later save for that student is refused.

v1 wrote `coScholasticGrades` on every save and v2 never does, so a row that
still has it was last saved by v1. On those report-card rows this removes
rank, classSize, attendancePct, workingDays, daysPresent and
coScholasticGrades, so the card prints the computed values; remarks, house,
promotion and admissionNo (and anything else) stay. Rows saved by v2 hold real
overrides and are left alone. Running it again changes nothing.

Downgrade is a no-op: the cleared values are not kept anywhere, and going back
doesn't need them, because the v1 code (54db9cd) reads every one of these keys
as optional (a missing value is "not set", coScholasticGrades defaults to []).
"""
from typing import Any, Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0019_clear_v1_card_overrides"
down_revision: Union[str, None] = "0018_marks_batch_revision"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

V1_MARKER = "coScholasticGrades"
V1_CLEARED_KEYS = ("rank", "classSize", "attendancePct", "workingDays", "daysPresent", V1_MARKER)

_student_data = sa.table(
    "pdf_student_data",
    sa.column("id", sa.BigInteger),
    sa.column("kind", sa.String),
    sa.column("data", sa.JSON),
)


def cleared_v1_row(data: Any) -> dict | None:
    """The row without the v1 sheet's hand-typed values, or None when the v1
    editor didn't save it (nothing to change)."""
    if not isinstance(data, dict) or V1_MARKER not in data:
        return None
    return {k: v for k, v in data.items() if k not in V1_CLEARED_KEYS}


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.select(_student_data.c.id, _student_data.c.data).where(_student_data.c.kind == "report-card")
    ).all()
    for row_id, data in rows:
        new = cleared_v1_row(data)
        if new is not None:
            conn.execute(_student_data.update().where(_student_data.c.id == row_id).values(data=new))


def downgrade() -> None:
    pass  # see the module docstring
