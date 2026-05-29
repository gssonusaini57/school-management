"""password_reset_tokens (forgot-password flow)

Revision ID: 0011_password_reset_tokens
Revises: 0010_staff_temp_password
Create Date: 2026-05-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0011_password_reset_tokens"
down_revision: Union[str, None] = "0010_staff_temp_password"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ACCOUNT_TYPE_ENUM = sa.Enum(
    "admin", "super_admin", "staff", native_enum=False, length=20
)


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("account_type", ACCOUNT_TYPE_ENUM, nullable=False),
        sa.Column("account_ref", sa.String(120), nullable=False),
        sa.Column("email", sa.String(120), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("used_at", sa.DateTime, nullable=True),
        sa.Column(
            "created_at", sa.DateTime,
            server_default=sa.func.current_timestamp(), nullable=False,
        ),
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_password_reset_tokens_token_hash",
        "password_reset_tokens",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
