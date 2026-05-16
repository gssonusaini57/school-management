"""staff: drop access_code; add email/password_hash/employee_id/force_password_change

Revision ID: 0005_staff_email_password_employee_id
Revises: 0004_student_admission_roll
Create Date: 2026-05-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0005_staff_email_password_employee_id"
down_revision: Union[str, None] = "0004_student_admission_roll"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: add new columns as nullable so we can backfill safely.
    op.add_column("staff", sa.Column("email", sa.String(120), nullable=True))
    op.add_column("staff", sa.Column("employee_id", sa.String(32), nullable=True))
    op.add_column("staff", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column(
        "staff",
        sa.Column(
            "force_password_change",
            sa.Boolean,
            nullable=False,
            server_default="1",
        ),
    )

    # Step 2: backfill existing rows.
    # - email: placeholder `staff{id}@kis.local` — admin will reset to real email post-deploy.
    # - employee_id: `KIS/EMP/{YEAR(created_at)}/{seq:04d}`, seq monotonic per year.
    # - password_hash: bcrypt("changeme") — same default; safe because force_password_change=TRUE.
    # `passlib` is imported lazily here so this migration works in an env that has it
    # (matches the runtime env — see backend/requirements.txt).
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    default_hash = pwd_context.hash("changeme")

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, created_at FROM staff ORDER BY created_at, id")
    ).fetchall()

    seq_by_year: dict[int, int] = {}
    for row in rows:
        sid = row[0]
        created_at = row[1]
        year = created_at.year if created_at is not None else 2026
        seq_by_year[year] = seq_by_year.get(year, 0) + 1
        seq = seq_by_year[year]
        employee_id = f"KIS/EMP/{year:04d}/{seq:04d}"
        email = f"staff{sid}@kis.local"
        bind.execute(
            sa.text(
                "UPDATE staff SET email = :email, employee_id = :eid, "
                "password_hash = :ph WHERE id = :id"
            ),
            {"email": email, "eid": employee_id, "ph": default_hash, "id": sid},
        )

    # Step 3: enforce NOT NULL + UNIQUE indexes on the new columns.
    op.alter_column("staff", "email", existing_type=sa.String(120), nullable=False)
    op.alter_column("staff", "employee_id", existing_type=sa.String(32), nullable=False)
    op.alter_column("staff", "password_hash", existing_type=sa.String(255), nullable=False)
    op.create_index("ix_staff_email_unique", "staff", ["email"], unique=True)
    op.create_index("ix_staff_employee_id_unique", "staff", ["employee_id"], unique=True)

    # Step 4: drop legacy access_code columns.
    op.drop_column("staff", "access_code_hash")
    op.drop_column("staff", "access_code_last4")


def downgrade() -> None:
    # Re-add access_code columns with empty defaults (irrecoverable: original hashes are gone).
    op.add_column(
        "staff",
        sa.Column("access_code_hash", sa.String(255), nullable=False, server_default=""),
    )
    op.add_column(
        "staff",
        sa.Column("access_code_last4", sa.String(4), nullable=False, server_default=""),
    )
    op.drop_index("ix_staff_employee_id_unique", table_name="staff")
    op.drop_index("ix_staff_email_unique", table_name="staff")
    op.drop_column("staff", "force_password_change")
    op.drop_column("staff", "password_hash")
    op.drop_column("staff", "employee_id")
    op.drop_column("staff", "email")
