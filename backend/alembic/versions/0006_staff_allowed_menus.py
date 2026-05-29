"""staff.allowed_menus JSON column with sensible defaults

Revision ID: 0006_staff_allowed_menus
Revises: 0005_staff_auth
Create Date: 2026-05-17
"""
import json
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0006_staff_allowed_menus"
down_revision: Union[str, None] = "0005_staff_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Mirror of backend/app/permissions.py DEFAULT_STAFF_MENUS, frozen here so
# replaying this migration doesn't drift with future default changes.
_DEFAULTS = [
    "dashboard",
    "students",
    "attendance",
    "marks-entry",
    "marks-results",
    "notices",
    "mobile-apps",
]


def upgrade() -> None:
    # MySQL 8 rejects DEFAULT on JSON for ADD COLUMN; add NULLable, backfill, then NOT NULL.
    op.add_column("staff", sa.Column("allowed_menus", sa.JSON(), nullable=True))
    op.get_bind().execute(
        sa.text("UPDATE staff SET allowed_menus = :menus WHERE allowed_menus IS NULL"),
        {"menus": json.dumps(_DEFAULTS)},
    )
    op.alter_column(
        "staff",
        "allowed_menus",
        existing_type=sa.JSON(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("staff", "allowed_menus")
