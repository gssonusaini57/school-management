"""Academic sessions: April rollover, term ranges, API rules, migration 0014 seeding."""
import importlib.util
from datetime import date
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from app.models.academic_session import AcademicSession
from app.services.sessions import is_valid_session_name, scope_dates, session_name_for

from .conftest import auth
from .factories import academic_session, batch, report_card_template


@pytest.mark.parametrize("day,name", [
    (date(2026, 4, 1), "2026-27"), (date(2026, 12, 31), "2026-27"),
    (date(2027, 2, 10), "2026-27"), (date(2027, 3, 31), "2026-27"), (date(2027, 4, 1), "2027-28"),
    (date(2099, 6, 1), "2099-00"),
])
def test_april_rollover(day, name):
    assert session_name_for(day) == name


def test_session_name_validation():
    assert is_valid_session_name("2026-27")
    assert is_valid_session_name("2099-00")
    assert not is_valid_session_name("2026-28")
    assert not is_valid_session_name("2026")
    assert not is_valid_session_name("26-27")


def test_scope_dates(db):
    row = academic_session(db, "2026-27")
    assert scope_dates(row, "term1") == (date(2026, 4, 1), date(2026, 9, 30))
    assert scope_dates(row, "term2") == (date(2026, 10, 1), date(2027, 3, 31))
    assert scope_dates(row, "annual") == (date(2026, 4, 1), date(2027, 3, 31))


def test_list_and_current_for_any_signed_in_user(client, db):
    academic_session(db, "2025-26", is_current=False)
    academic_session(db, "2026-27", is_current=True)
    db.commit()
    r = client.get("/api/sessions", headers=auth("staff", ["8th"]))
    assert [s["session"] for s in r.json()] == ["2026-27", "2025-26"]
    assert client.get("/api/sessions/current", headers=auth("staff", ["8th"])).json()["session"] == "2026-27"


def test_create_is_super_admin_only_and_defaults_dates(client):
    assert client.post("/api/sessions", json={"session": "2027-28"}, headers=auth("admin")).status_code == 403
    r = client.post("/api/sessions", json={"session": "2027-28"}, headers=auth("super_admin"))
    assert r.status_code == 201, r.text
    body = r.json()
    assert (body["term1_start"], body["term1_end"], body["term2_start"], body["term2_end"]) == (
        "2027-04-01", "2027-09-30", "2027-10-01", "2028-03-31")
    assert client.post("/api/sessions", json={"session": "2027-28"}, headers=auth("super_admin")).status_code == 409
    assert client.post("/api/sessions", json={"session": "2027-29"}, headers=auth("super_admin")).status_code == 422


def test_overlapping_terms_rejected(client, db):
    row = academic_session(db, "2026-27")
    db.commit()
    r = client.patch(f"/api/sessions/{row.id}", json={"term2_start": "2026-09-15"}, headers=auth("super_admin"))
    assert r.status_code == 422
    r = client.patch(f"/api/sessions/{row.id}", json={"term1_end": "2026-10-10", "term2_start": "2026-10-11"},
                     headers=auth("super_admin"))
    assert r.status_code == 200 and r.json()["term1_end"] == "2026-10-10"


def test_only_one_current(client, db):
    old = academic_session(db, "2025-26", is_current=True)
    new = academic_session(db, "2026-27", is_current=False)
    db.commit()
    client.patch(f"/api/sessions/{new.id}", json={"is_current": True}, headers=auth("super_admin"))
    db.expire_all()
    assert [s.session for s in db.query(AcademicSession).filter_by(is_current=True)] == ["2026-27"]
    assert db.get(AcademicSession, old.id).is_current is False


def test_marks_batch_requires_a_configured_session(client, db):
    academic_session(db, "2026-27")
    db.commit()
    body = {"class_name": "8th", "subject": "Mathematics", "exam_type": "P.T. First", "session": "2027-28",
            "max_marks": 35, "items": []}
    r = client.post("/api/marks/batches", json=body, headers=auth("admin"))
    assert r.status_code == 422 and "academic session" in r.json()["detail"]


def _load_migration(name: str):
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_migration_0014_seeds_used_and_current_sessions(engine, db):
    AcademicSession.__table__.drop(engine)
    batch(db, "8th", "Mathematics", "P.T. First", session="2025-26")
    batch(db, "8th", "Mathematics", "P.T. Second", session="garbage")
    report_card_template(db, session="2024-25")
    db.commit()
    mig = _load_migration("0014_academic_sessions")
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            mig.upgrade()
        rows = conn.execute(text("SELECT session, is_current, term2_start FROM academic_sessions ORDER BY session")).all()
    current = mig._session_for(date.today())
    expected = sorted({"2024-25", "2025-26", current})
    assert [r[0] for r in rows] == expected
    assert [r[0] for r in rows if r[1]] == [current]
    assert str(rows[0][2]) == "2024-10-01"
