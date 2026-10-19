"""marks_batches.revision: refuse saves from a screen showing an outdated batch

Revision ID: 0018_marks_batch_revision
Revises: 0017_pdf_render_jobs
Create Date: 2026-10-19

A Marks Entry save carried only the id of the batch its screen had loaded, so
a screen left open (a second device, a cached page, an app screen that was
never reloaded) could save an outdated copy of an existing batch: it put back
old marks and pruned students it didn't show. `updated_at` can't tell, because
a marks save writes only `marks` rows and leaves the batch row untouched.

`revision` goes up by one on every change to a batch's marks or status (form
save, CSV import, submit, edit-request approve / reject, class-subject
renames). A save sends the revision its screen loaded (`base_revision`) and is
refused with 409 when the batch has moved on since. Existing batches start at 0.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "0018_marks_batch_revision"
down_revision: Union[str, None] = "0017_pdf_render_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("marks_batches", sa.Column("revision", sa.Integer, nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("marks_batches", "revision")
