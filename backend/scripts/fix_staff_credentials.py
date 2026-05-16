"""One-shot maintenance: assign real-name emails + a uniform password to staff
with placeholder credentials, AND canonicalize legacy `staff_classes.class_name`
spellings (e.g. 'LKG' → 'L.K.G').

Run on the deployed server from the project root so the .env is picked up:

    cd /opt/school-management && \
      sudo -u school /opt/school-management/app/.venv/bin/python \
      /opt/school-management/app/scripts/fix_staff_credentials.py

Idempotent: re-running it skips rows already in canonical state.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_ROOT = HERE.parent
sys.path.insert(0, str(APP_ROOT))

from sqlalchemy import select, update  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models.staff import Staff, StaffClass  # noqa: E402
from app.security import hash_password  # noqa: E402

DEFAULT_PASSWORD = "Test123"
EMAIL_DOMAIN = "kis.com"
PLACEHOLDER_DOMAIN = "@kis.local"

# Canonical class names — keep in sync with frontend/src/lib/utils.ts CLASSES.
CANONICAL_CLASSES = [
    "Nursery", "L.K.G", "U.K.G",
    "1st", "2nd", "3rd", "4th", "5th", "6th",
    "7th", "8th", "9th", "10th", "11th", "12th",
]


def slugify_name(name: str) -> str:
    s = (name or "").lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s or "staff"


def _norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def canonicalize_class(raw: str) -> str:
    target = _norm_key(raw)
    for c in CANONICAL_CLASSES:
        if _norm_key(c) == target:
            return c
    return raw


def fix_credentials(db) -> int:
    rows = db.execute(select(Staff)).scalars().all()
    reserved = {
        (r.email or "").lower()
        for r in rows
        if r.email and not r.email.lower().endswith(PLACEHOLDER_DOMAIN)
    }
    new_hash = hash_password(DEFAULT_PASSWORD)
    updates: list[tuple[int, str, str, str]] = []
    for r in rows:
        if not r.email or not r.email.lower().endswith(PLACEHOLDER_DOMAIN):
            continue
        slug = slugify_name(r.name)
        candidate = f"{slug}@{EMAIL_DOMAIN}"
        if candidate.lower() in reserved:
            candidate = f"{slug}.{r.id}@{EMAIL_DOMAIN}"
        reserved.add(candidate.lower())
        old_email = r.email
        r.email = candidate
        r.password_hash = new_hash
        r.force_password_change = True
        updates.append((r.id, r.name, old_email, candidate))
    if updates:
        db.commit()
    return len(updates), updates


def fix_class_names(db) -> int:
    """Update staff_classes rows whose `class_name` isn't canonical."""
    rows = db.execute(select(StaffClass)).scalars().all()
    n = 0
    for r in rows:
        canon = canonicalize_class(r.class_name)
        if canon != r.class_name:
            # Avoid duplicate-key collision: check if (staff_id, canon) already exists.
            exists = db.execute(
                select(StaffClass).where(
                    StaffClass.staff_id == r.staff_id,
                    StaffClass.class_name == canon,
                )
            ).first()
            if exists:
                # Canonical already present for this staff — drop the legacy duplicate.
                db.delete(r)
            else:
                r.class_name = canon
            n += 1
    if n:
        db.commit()
    return n


def main() -> int:
    db = SessionLocal()
    try:
        n_creds, cred_updates = fix_credentials(db)
        n_classes = fix_class_names(db)

        print(f"Credential updates: {n_creds}  (password set to: {DEFAULT_PASSWORD})")
        if cred_updates:
            print(f"{'ID':<5} {'Name':<24} {'Old email':<28} {'New email'}")
            print("-" * 80)
            for sid, name, old, new in cred_updates:
                print(f"{sid:<5} {name[:24]:<24} {old[:28]:<28} {new}")
        print(f"Class-name normalizations: {n_classes}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
