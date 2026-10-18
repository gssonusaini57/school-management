"""academic sessions: one row per school year with its Term 1 / Term 2 dates

Revision ID: 0014_academic_sessions
Revises: 0013_component_term
Create Date: 2026-10-18

Until now an academic session was only a free-text string ("2026-27") on
marks, batches and templates, and every client guessed the current one from
the calendar year, which is wrong from January to March. This table is the
source of truth for the session list, the current session, and the term date
ranges that attendance summaries and report cards count over.

Seeded with the session containing today (marked current) plus every other
well-formed session already used by marks, batches or templates, all with the
school's April-March year split into Term 1 (Apr-Sep) and Term 2 (Oct-Mar).
Dates are editable afterwards on the Sessions page.
"""
import re
from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0014_academic_sessions"
down_revision: Union[str, None] = "0013_component_term"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SESSION_RE = re.compile(r"^(\d{4})-(\d{2})$")


def _session_for(day: date) -> str:
    y = day.year if day.month >= 4 else day.year - 1
    return f"{y}-{(y + 1) % 100:02d}"


def _row(name: str, current: bool) -> dict | None:
    m = _SESSION_RE.match(name or "")
    if not m:
        return None
    y = int(m.group(1))
    if int(m.group(2)) != (y + 1) % 100:
        return None
    return {
        "session": name,
        "starts_on": date(y, 4, 1), "ends_on": date(y + 1, 3, 31),
        "term1_start": date(y, 4, 1), "term1_end": date(y, 9, 30),
        "term2_start": date(y, 10, 1), "term2_end": date(y + 1, 3, 31),
        "is_current": current, "updated_by": "migration 0014",
    }


def upgrade() -> None:
    table = op.create_table(
        "academic_sessions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("session", sa.String(16), nullable=False),
        sa.Column("starts_on", sa.Date, nullable=False),
        sa.Column("ends_on", sa.Date, nullable=False),
        sa.Column("term1_start", sa.Date, nullable=False),
        sa.Column("term1_end", sa.Date, nullable=False),
        sa.Column("term2_start", sa.Date, nullable=False),
        sa.Column("term2_end", sa.Date, nullable=False),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime,
            server_default=sa.func.current_timestamp(),
            onupdate=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.Column("updated_by", sa.String(120), nullable=False, server_default=""),
        sa.UniqueConstraint("session", name="uq_academic_sessions_session"),
        mysql_charset="utf8mb4",
    )

    conn = op.get_bind()
    used = set(conn.execute(sa.text(
        "SELECT DISTINCT session FROM marks "
        "UNION SELECT DISTINCT session FROM marks_batches "
        "UNION SELECT DISTINCT session FROM pdf_templates"
    )).scalars())
    current = _session_for(date.today())
    rows = []
    for name in sorted(used | {current}):
        r = _row(name, current=(name == current))
        if r:
            rows.append(r)
    if rows:
        op.bulk_insert(table, rows)


def downgrade() -> None:
    op.drop_table("academic_sessions")
