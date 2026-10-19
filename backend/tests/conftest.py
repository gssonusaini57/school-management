"""Test harness: an in-memory SQLite database stands in for MySQL.

Real schemas are built by Alembic only (never `create_all`). Here `create_all`
builds a throwaway schema per test, with two MySQL-only column types mapped to
SQLite equivalents. The app's lifespan (admin seeding against the real DB) is
skipped by never entering the TestClient context.

Run:  cd backend && .venv/bin/python -m pytest -q
"""
from __future__ import annotations

import os
import tempfile

# Must be set before `app` is imported: app.db builds its engine at import time.
# A file URL (not :memory:) because the app engine passes QueuePool options.
_TMP = tempfile.mkdtemp(prefix="kis-tests-")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_TMP}/import-only.db"
os.environ.setdefault("JWT_SECRET", "test-secret-not-used-anywhere-else")
os.environ.setdefault("SMTP_USER", "")      # keeps email_enabled False
os.environ.setdefault("SMTP_PASSWORD", "")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import BigInteger, create_engine, event
from sqlalchemy.dialects.mysql import LONGBLOB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@compiles(BigInteger, "sqlite")
def _bigint_as_integer(type_, compiler, **kw):  # noqa: ANN001
    # SQLite only autoincrements an INTEGER PRIMARY KEY.
    return "INTEGER"


@compiles(LONGBLOB, "sqlite")
def _longblob_as_blob(type_, compiler, **kw):  # noqa: ANN001
    return "BLOB"


from app.db import Base, get_db  # noqa: E402
# Same model list as backend/alembic/env.py, so every table exists.
from app.models import (  # noqa: E402,F401
    admin, staff, student, document, attendance, marks, fee, notice, pdf_template,
    student_edit_request, class_subject, marks_batch, password_reset, academic_session, pdf_render_job,
)
from app.main import app  # noqa: E402
from app.permissions import DEFAULT_STAFF_MENUS  # noqa: E402
from app.security import create_token  # noqa: E402


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _foreign_keys_on(dbapi_conn, _record):  # noqa: ANN001
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture()
def db(session_factory) -> Session:
    s = session_factory()
    yield s
    s.close()


@pytest.fixture()
def client(session_factory):
    def _get_db():
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_token(role: str = "admin", classes: list[str] | None = None, name: str = "Test User",
               menus: list[str] | None = None) -> str:
    # Staff get the real default menus unless a test says otherwise; admins have none (they bypass).
    if menus is None:
        menus = list(DEFAULT_STAFF_MENUS) if role == "staff" else []
    return create_token(sub="1", role=role, name=name, allowed_classes=classes or [], allowed_menus=menus)


def auth(role: str = "admin", classes: list[str] | None = None, name: str = "Test User",
         menus: list[str] | None = None) -> dict[str, str]:
    """Bearer header for a role: "admin", "super_admin" or "staff" (+ its classes and menus)."""
    return {"Authorization": f"Bearer {make_token(role, classes, name, menus)}"}
