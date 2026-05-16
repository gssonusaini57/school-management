"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_auth",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        mysql_charset="utf8mb4",
    )

    op.create_table(
        "staff",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("designation", sa.String(80), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False, server_default=""),
        sa.Column("access_code_hash", sa.String(255), nullable=False),
        sa.Column("access_code_last4", sa.String(4), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_by", sa.String(120), nullable=False, server_default=""),
        mysql_charset="utf8mb4",
    )

    op.create_table(
        "staff_classes",
        sa.Column("staff_id", sa.BigInteger, sa.ForeignKey("staff.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("class_name", sa.String(20), primary_key=True),
        mysql_charset="utf8mb4",
    )

    op.create_table(
        "students",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("father", sa.String(120), nullable=False),
        sa.Column("mother", sa.String(120), nullable=False),
        sa.Column("dob", sa.Date, nullable=True),
        sa.Column("gender", sa.String(20), nullable=False, server_default=""),
        sa.Column("village", sa.String(200), nullable=False, server_default=""),
        sa.Column("phone", sa.String(20), nullable=False, server_default=""),
        sa.Column("aadhar", sa.String(20), nullable=False, server_default=""),
        sa.Column("alt_phone", sa.String(20), nullable=False, server_default="N/A"),
        sa.Column("religion", sa.String(80), nullable=False, server_default="N/A"),
        sa.Column("prev_school", sa.String(200), nullable=False, server_default="N/A"),
        sa.Column("bank_name", sa.String(120), nullable=False, server_default="N/A"),
        sa.Column("bank_acc", sa.String(40), nullable=False, server_default="N/A"),
        sa.Column("bank_ifsc", sa.String(20), nullable=False, server_default="N/A"),
        sa.Column("annual_fee", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("class_name", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("added_by", sa.String(120), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_by", sa.String(120), nullable=False, server_default=""),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_students_class_name", "students", ["class_name"])

    op.create_table(
        "student_documents",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.BigInteger, sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.Enum("photo", "dob_cert", "aadhar", name="document_kind"), nullable=False),
        sa.Column("mime_type", sa.String(80), nullable=False, server_default="application/octet-stream"),
        sa.Column("byte_size", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("data", mysql.LONGBLOB, nullable=False),
        sa.Column("uploaded_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.UniqueConstraint("student_id", "kind", name="uq_student_kind"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_student_documents_student_id", "student_documents", ["student_id"])

    op.create_table(
        "attendance",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("class_name", sa.String(20), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("updated_by", sa.String(120), nullable=False, server_default=""),
        sa.UniqueConstraint("class_name", "date", name="uq_class_date"),
        mysql_charset="utf8mb4",
    )

    op.create_table(
        "attendance_records",
        sa.Column("attendance_id", sa.BigInteger, sa.ForeignKey("attendance.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("student_id", sa.BigInteger, sa.ForeignKey("students.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("status", sa.Enum("P", "A", "L", name="attendance_status"), nullable=False),
        mysql_charset="utf8mb4",
    )

    op.create_table(
        "marks",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.BigInteger, sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("class_name", sa.String(20), nullable=False),
        sa.Column("exam_type", sa.String(60), nullable=False),
        sa.Column("subject", sa.String(60), nullable=False),
        sa.Column("marks", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_marks", sa.Integer, nullable=False, server_default="100"),
        sa.Column("session", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("saved_by", sa.String(120), nullable=False, server_default=""),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_marks_student_id", "marks", ["student_id"])
    op.create_index("ix_marks_class_exam", "marks", ["class_name", "exam_type"])

    op.create_table(
        "fee_payments",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.BigInteger, sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_name", sa.String(120), nullable=False, server_default=""),
        sa.Column("class_name", sa.String(20), nullable=False),
        sa.Column("month", sa.String(20), nullable=False),
        sa.Column("year", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("receipt_no", sa.String(40), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("saved_by", sa.String(120), nullable=False, server_default=""),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_fee_payments_student_id", "fee_payments", ["student_id"])
    op.create_index("ix_fee_payments_class_name", "fee_payments", ["class_name"])

    op.create_table(
        "notices",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("priority", sa.Enum("normal", "medium", "high", name="priority"), nullable=False, server_default="normal"),
        sa.Column("audience", sa.String(80), nullable=False, server_default="all"),
        sa.Column("posted_by", sa.String(120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        mysql_charset="utf8mb4",
    )


def downgrade() -> None:
    op.drop_table("notices")
    op.drop_index("ix_fee_payments_class_name", table_name="fee_payments")
    op.drop_index("ix_fee_payments_student_id", table_name="fee_payments")
    op.drop_table("fee_payments")
    op.drop_index("ix_marks_class_exam", table_name="marks")
    op.drop_index("ix_marks_student_id", table_name="marks")
    op.drop_table("marks")
    op.drop_table("attendance_records")
    op.drop_table("attendance")
    op.drop_index("ix_student_documents_student_id", table_name="student_documents")
    op.drop_table("student_documents")
    op.drop_index("ix_students_class_name", table_name="students")
    op.drop_table("students")
    op.drop_table("staff_classes")
    op.drop_table("staff")
    op.drop_table("admin_auth")
