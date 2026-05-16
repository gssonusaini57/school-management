"""staff: drop access_code; add email/password_hash/employee_id/force_password_change

Revision ID: 0005_staff_auth
Revises: 0004_student_admission_roll
Create Date: 2026-05-16

Idempotent: on a fresh DB it runs the full add-cols + backfill + drop sequence;
on a DB where the schema is already at this revision's end-state (e.g. a
previous deploy that partially ran), each operation is skipped after inspecting
the live schema. This lets the migration run cleanly after a failed prior
deploy without manual alembic_version surgery.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0005_staff_auth"
down_revision: Union[str, None] = "0004_student_admission_roll"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _staff_cols(bind) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns("staff")}


def _staff_indexes(bind) -> set[str]:
    return {ix["name"] for ix in sa.inspect(bind).get_indexes("staff")}


def upgrade() -> None:
    bind = op.get_bind()
    cols = _staff_cols(bind)

    # Step 1: add new columns as nullable so we can backfill safely.
    if "email" not in cols:
        op.add_column("staff", sa.Column("email", sa.String(120), nullable=True))
    if "employee_id" not in cols:
        op.add_column("staff", sa.Column("employee_id", sa.String(32), nullable=True))
    if "password_hash" not in cols:
        op.add_column("staff", sa.Column("password_hash", sa.String(255), nullable=True))
    if "force_password_change" not in cols:
        op.add_column(
            "staff",
            sa.Column(
                "force_password_change",
                sa.Boolean,
                nullable=False,
                server_default="1",
            ),
        )

    # Step 2: backfill — only rows that still need it. Skip entirely if no row
    # has a NULL in the new columns (means the previous run completed).
    needs_backfill = bind.execute(
        sa.text("SELECT COUNT(*) FROM staff WHERE email IS NULL OR employee_id IS NULL OR password_hash IS NULL")
    ).scalar() or 0

    if needs_backfill:
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        default_hash = pwd_context.hash("changeme")

        rows = bind.execute(
            sa.text(
                "SELECT id, created_at FROM staff "
                "WHERE email IS NULL OR employee_id IS NULL OR password_hash IS NULL "
                "ORDER BY created_at, id"
            )
        ).fetchall()

        # Seed seq_by_year with the highest existing seq per year so newly
        # backfilled rows don't collide with already-assigned employee_ids.
        existing = bind.execute(
            sa.text(
                "SELECT employee_id FROM staff "
                "WHERE employee_id IS NOT NULL AND employee_id LIKE 'KIS/EMP/%'"
            )
        ).fetchall()
        seq_by_year: dict[int, int] = {}
        for (eid,) in existing:
            parts = (eid or "").split("/")
            if len(parts) == 4:
                try:
                    y = int(parts[2])
                    s = int(parts[3])
                    seq_by_year[y] = max(seq_by_year.get(y, 0), s)
                except ValueError:
                    pass

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

    # Step 3: enforce NOT NULL + UNIQUE indexes.
    # `alter_column nullable` is safe even if the column is already NOT NULL.
    op.alter_column("staff", "email", existing_type=sa.String(120), nullable=False)
    op.alter_column("staff", "employee_id", existing_type=sa.String(32), nullable=False)
    op.alter_column("staff", "password_hash", existing_type=sa.String(255), nullable=False)

    indexes = _staff_indexes(bind)
    if "ix_staff_email_unique" not in indexes:
        op.create_index("ix_staff_email_unique", "staff", ["email"], unique=True)
    if "ix_staff_employee_id_unique" not in indexes:
        op.create_index("ix_staff_employee_id_unique", "staff", ["employee_id"], unique=True)

    # Step 4: drop legacy access_code columns if still present.
    cols_after = _staff_cols(bind)
    if "access_code_hash" in cols_after:
        op.drop_column("staff", "access_code_hash")
    if "access_code_last4" in cols_after:
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
