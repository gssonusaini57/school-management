"""super_admin_auth + soft-delete columns on students/staff

Revision ID: 0003_soft_delete_workflow
Revises: 0002_pdf_templates_cache
Create Date: 2026-05-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0003_soft_delete_workflow"
down_revision: Union[str, None] = "0002_pdf_templates_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Inline (non-native) ENUM so the column matches values exactly — see Gotcha #12
# (SQLAlchemy `Enum(..., values_callable=..., native_enum=False)`).
STATUS_ENUM = sa.Enum("active", "pending_delete", "deleted", native_enum=False, length=20)


def upgrade() -> None:
    op.create_table(
        "super_admin_auth",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime,
            server_default=sa.func.current_timestamp(), nullable=False,
        ),
        mysql_charset="utf8mb4",
    )

    for table in ("students", "staff"):
        op.add_column(
            table,
            sa.Column("status", STATUS_ENUM, nullable=False, server_default="active"),
        )
        op.add_column(table, sa.Column("delete_requested_at", sa.DateTime, nullable=True))
        op.add_column(table, sa.Column("delete_requested_by", sa.String(120), nullable=True))
        op.add_column(table, sa.Column("delete_reason", sa.String(500), nullable=True))
        op.add_column(table, sa.Column("deleted_at", sa.DateTime, nullable=True))
        op.add_column(table, sa.Column("deleted_by", sa.String(120), nullable=True))
        op.create_index(f"ix_{table}_status", table, ["status"])


def downgrade() -> None:
    for table in ("students", "staff"):
        op.drop_index(f"ix_{table}_status", table_name=table)
        op.drop_column(table, "deleted_by")
        op.drop_column(table, "deleted_at")
        op.drop_column(table, "delete_reason")
        op.drop_column(table, "delete_requested_by")
        op.drop_column(table, "delete_requested_at")
        op.drop_column(table, "status")
    op.drop_table("super_admin_auth")
