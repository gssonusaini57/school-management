"""device_sessions: refresh tokens behind "stay signed in"

Revision ID: 0021_device_sessions
Revises: 0020_optional_subjects
Create Date: 2026-10-19

Access tokens last an hour and the server kept no session state, so everyone
was signed out every hour on the app and the website. A sign-in with
"remember me" now also opens a device session: a refresh token (stored only as
its SHA-256 hash) that is rotated on every use, slides REFRESH_TOKEN_DAYS from
its last use and dies REFRESH_TOKEN_MAX_DAYS after the first sign-in. Rows
record how they ended (rotated / logout / replay / password change / ...), and
rows dead for 30 days are pruned at the account's next sign-in.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0021_device_sessions"
down_revision: Union[str, None] = "0020_optional_subjects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "device_sessions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "account_type",
            sa.Enum("admin", "super_admin", "staff", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("account_ref", sa.String(120), nullable=False),
        sa.Column("token_hash", sa.CHAR(64), nullable=False),
        sa.Column("family_id", sa.CHAR(32), nullable=False),
        sa.Column("platform", sa.Enum("android", "web", native_enum=False, length=10), nullable=False),
        sa.Column("device_name", sa.String(120), nullable=False, server_default=""),
        sa.Column(
            "via",
            sa.Enum("password", "temp_password", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("last_used_at", sa.DateTime, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime, nullable=False),
        sa.Column("rotated_at", sa.DateTime, nullable=True),
        sa.Column("replaced_by_id", sa.BigInteger, nullable=True),
        sa.Column("revoked_at", sa.DateTime, nullable=True),
        sa.Column("revoked_reason", sa.String(40), nullable=True),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_device_sessions_token_hash", "device_sessions", ["token_hash"], unique=True)
    op.create_index("ix_device_sessions_family_id", "device_sessions", ["family_id"])
    op.create_index("ix_device_sessions_account", "device_sessions", ["account_type", "account_ref"])


def downgrade() -> None:
    # Dropping the table drops its indexes with it.
    op.drop_table("device_sessions")
