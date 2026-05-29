"""class_subjects + subject_exam_components master tables

Revision ID: 0008_class_subjects
Revises: 0007_student_edit_requests
Create Date: 2026-05-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0008_class_subjects"
down_revision: Union[str, None] = "0007_student_edit_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATEGORY_ENUM = sa.Enum(
    "academic", "co_curricular", "grading",
    native_enum=False, length=20,
)


def upgrade() -> None:
    op.create_table(
        "class_subjects",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("class_name", sa.String(20), nullable=False),
        sa.Column("subject_name", sa.String(60), nullable=False),
        sa.Column("subject_name_pa", sa.String(60), nullable=True),
        sa.Column("category", CATEGORY_ENUM, nullable=False, server_default="academic"),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime,
            server_default=sa.func.current_timestamp(),
            onupdate=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.UniqueConstraint("class_name", "subject_name", name="uq_class_subjects_class_subject"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_class_subjects_class_name", "class_subjects", ["class_name"])

    op.create_table(
        "subject_exam_components",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "class_subject_id", sa.BigInteger,
            sa.ForeignKey("class_subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("component_name", sa.String(80), nullable=False),
        sa.Column("max_marks", sa.Integer, nullable=False, server_default="0"),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime,
            server_default=sa.func.current_timestamp(),
            onupdate=sa.func.current_timestamp(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "class_subject_id", "component_name",
            name="uq_subject_exam_components_subject_component",
        ),
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_subject_exam_components_subject",
        "subject_exam_components",
        ["class_subject_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_subject_exam_components_subject", table_name="subject_exam_components")
    op.drop_table("subject_exam_components")
    op.drop_index("ix_class_subjects_class_name", table_name="class_subjects")
    op.drop_table("class_subjects")
