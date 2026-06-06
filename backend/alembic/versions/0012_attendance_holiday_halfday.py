"""attendance: half-day status + day-level holiday flag

Revision ID: 0012_attendance_holiday_halfday
Revises: 0011_password_reset_tokens
Create Date: 2026-06-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0012_attendance_holiday_halfday"
down_revision: Union[str, None] = "0011_password_reset_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # status is a NATIVE MySQL ENUM — widen it with raw SQL to add half-day "H".
    op.execute("ALTER TABLE attendance_records MODIFY status ENUM('P','A','L','H') NOT NULL")
    # Day-level holiday marker on the (class, date) row (a holiday row has NO
    # student records). server_default '0' so the NOT-NULL backfill succeeds.
    op.add_column(
        "attendance",
        sa.Column("is_holiday", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    # Remap half-day rows before narrowing or MySQL truncates them on MODIFY.
    op.execute("UPDATE attendance_records SET status='A' WHERE status='H'")
    op.execute("ALTER TABLE attendance_records MODIFY status ENUM('P','A','L') NOT NULL")
    op.drop_column("attendance", "is_holiday")
