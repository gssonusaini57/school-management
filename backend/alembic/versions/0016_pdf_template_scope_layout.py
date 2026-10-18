"""report-card templates: explicit result scope + card layout

Revision ID: 0016_pdf_template_scope_layout
Revises: 0015_marks_grade
Create Date: 2026-10-18

`scope` (term1 | term2 | annual) is now chosen when a report-card template is
created, instead of being guessed from the free-text term label at render time
(an unrecognised label used to fall back to whole-year totals silently).
Existing rows are backfilled from their term label; anything unrecognised
stays NULL and the API refuses to render it until a scope is set.

`layout` picks the card design per template: `summary` (one Marks / Max /
Grade row per subject) or `components` (a column per exam, e.g. P.T. First |
P.T. Second | Semester First, or Term 1 | Term 2 on an annual card).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0016_pdf_template_scope_layout"
down_revision: Union[str, None] = "0015_marks_grade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TERM1 = "'term i','term 1','term-1','term1','t1','1','first','first term','1st term'"
_TERM2 = "'term ii','term 2','term-2','term2','t2','2','second','second term','2nd term'"
_ANNUAL = "'','annual','final','full year','year'"


def upgrade() -> None:
    op.add_column("pdf_templates", sa.Column("layout", sa.String(16), nullable=False, server_default="summary"))
    op.add_column("pdf_templates", sa.Column("scope", sa.String(8), nullable=True))
    label = "LOWER(TRIM(COALESCE(term, '')))"
    op.execute(
        "UPDATE pdf_templates SET scope = CASE "
        f"WHEN {label} IN ({_TERM1}) THEN 'term1' "
        f"WHEN {label} IN ({_TERM2}) THEN 'term2' "
        f"WHEN {label} IN ({_ANNUAL}) THEN 'annual' "
        "ELSE NULL END "
        "WHERE kind = 'report-card'"
    )


def downgrade() -> None:
    op.drop_column("pdf_templates", "scope")
    op.drop_column("pdf_templates", "layout")
