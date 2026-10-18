"""Academic sessions: naming, current-session lookup, and term date ranges.

The school year runs April to March. Term 1 is April-September and Term 2 is
October-March by default; the real dates live in `academic_sessions` and are
editable per session.
"""
from __future__ import annotations

import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.academic_session import AcademicSession

SESSION_RE = re.compile(r"^(\d{4})-(\d{2})$")


def session_name_for(day: date) -> str:
    """The session containing `day`, e.g. 2027-02-10 -> "2026-27" (April rollover)."""
    y = day.year if day.month >= 4 else day.year - 1
    return f"{y}-{(y + 1) % 100:02d}"


def is_valid_session_name(name: str) -> bool:
    m = SESSION_RE.match(name or "")
    return bool(m) and int(m.group(2)) == (int(m.group(1)) + 1) % 100


def default_dates(name: str) -> dict[str, date]:
    """Default calendar for a session name: Apr 1 - Mar 31, terms split at Oct 1."""
    if not is_valid_session_name(name):
        raise ValueError(f"session must look like 2026-27, got {name!r}")
    y = int(name[:4])
    return {
        "starts_on": date(y, 4, 1), "ends_on": date(y + 1, 3, 31),
        "term1_start": date(y, 4, 1), "term1_end": date(y, 9, 30),
        "term2_start": date(y, 10, 1), "term2_end": date(y + 1, 3, 31),
    }


def date_errors(d: dict[str, date]) -> list[str]:
    """Ordering rules: start <= term1 start <= term1 end < term2 start <= term2 end <= end."""
    errs = []
    if not d["starts_on"] <= d["term1_start"]:
        errs.append("Term 1 must start on or after the session start")
    if not d["term1_start"] <= d["term1_end"]:
        errs.append("Term 1 must end on or after it starts")
    if not d["term1_end"] < d["term2_start"]:
        errs.append("Term 2 must start after Term 1 ends")
    if not d["term2_start"] <= d["term2_end"]:
        errs.append("Term 2 must end on or after it starts")
    if not d["term2_end"] <= d["ends_on"]:
        errs.append("Term 2 must end on or before the session end")
    return errs


def get_session(db: Session, name: str) -> AcademicSession | None:
    return db.scalar(select(AcademicSession).where(AcademicSession.session == name))


def current_session(db: Session, today: date | None = None) -> AcademicSession | None:
    """The row flagged current, else the row whose dates contain today."""
    row = db.scalar(select(AcademicSession).where(AcademicSession.is_current.is_(True)))
    if row:
        return row
    today = today or date.today()
    return db.scalar(
        select(AcademicSession).where(AcademicSession.starts_on <= today, AcademicSession.ends_on >= today)
    )


def scope_dates(row: AcademicSession, scope: str) -> tuple[date, date]:
    """Date range a result scope covers: term1, term2 or annual (whole session)."""
    if scope == "term1":
        return row.term1_start, row.term1_end
    if scope == "term2":
        return row.term2_start, row.term2_end
    return row.starts_on, row.ends_on
