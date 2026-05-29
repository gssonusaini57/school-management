"""staff temporary password (admin override that coexists with the real password)

Revision ID: 0010_staff_temp_password
Revises: 0009_marks_batches_edit_requests
Create Date: 2026-05-29

Adds a second, optional credential for a staff member that an admin/super-admin can
set from the web portal (e.g. to cover an absent teacher). The teacher's own
`password_hash` is untouched, so they keep logging in with their real password; the
temp password just *also* works until an admin clears it.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0010_staff_temp_password"
down_revision: Union[str, None] = "0009_marks_batches_edit_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("staff", sa.Column("temp_password_hash", sa.String(255), nullable=True))
    op.add_column("staff", sa.Column("temp_password_set_at", sa.DateTime(), nullable=True))
    op.add_column("staff", sa.Column("temp_password_set_by", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("staff", "temp_password_set_by")
    op.drop_column("staff", "temp_password_set_at")
    op.drop_column("staff", "temp_password_hash")
