"""Migration 0016 backfills each report-card template's scope from its term label."""
import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from .factories import report_card_template


def _load(name):
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_scope_backfill(engine, db):
    labels = {"8th": "Term I", "7th": "term 2", "6th": "Annual", "5th": None, "4th": "Half Yearly"}
    for cls, term in labels.items():
        report_card_template(db, cls, term=term)
    db.commit()
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE pdf_templates DROP COLUMN scope"))
        conn.execute(text("ALTER TABLE pdf_templates DROP COLUMN layout"))
        with Operations.context(MigrationContext.configure(conn)):
            _load("0016_pdf_template_scope_layout").upgrade()
        rows = dict(conn.execute(text("SELECT class_name, scope FROM pdf_templates")).all())
        layouts = {r[0] for r in conn.execute(text("SELECT layout FROM pdf_templates")).all()}
    assert rows == {"8th": "term1", "7th": "term2", "6th": "annual", "5th": "annual", "4th": None}
    assert layouts == {"summary"}
