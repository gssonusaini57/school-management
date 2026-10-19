"""Device sessions: issue, rotate, revoke, list and prune refresh tokens.

Persistence helpers around `models.device_session.DeviceSession`. The HTTP
rules — the 60-second lost-response grace, replay detection, cookies, error
messages — live in `routers/auth.py`; this module only knows rows.

Every function flushes but never commits: the request that called it does,
so a sign-in, a rotation and its bookkeeping land in one transaction. The
exception is `revoke_sessions_hook`, the form routers call AFTER their own
commit; it commits itself and never raises (like the notification helpers).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..constants import expand_classes
from ..logging_config import get_logger
from ..models.device_session import DeviceSession, SessionAccountType, SessionPlatform, SessionVia
from ..models.record_status import RecordStatus
from ..models.staff import Staff
from ..security import generate_refresh_token, hash_refresh_token

log = get_logger("app.device_sessions")

# How the JWT names each account type's role, and the fixed subjects of the two
# singleton accounts (staff use their id as the subject).
ROLE_BY_ACCOUNT: dict[SessionAccountType, str] = {
    SessionAccountType.admin: "admin",
    SessionAccountType.super_admin: "super_admin",
    SessionAccountType.staff: "staff",
}
ACCOUNT_BY_ROLE: dict[str, SessionAccountType] = {v: k for k, v in ROLE_BY_ACCOUNT.items()}
ADMIN_SUB = "admin"
SUPER_ADMIN_SUB = "superadmin"

# Rows revoked, rotated or expired longer ago than this are deleted at the
# account's next sign-in (`prune`).
PRUNE_AFTER_DAYS = 30


def utcnow() -> datetime:
    """Naive UTC — the convention of every DATETIME column in this schema."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _account(account_type: SessionAccountType | str) -> SessionAccountType:
    return SessionAccountType(account_type)


def _clip(value: str | None, limit: int) -> str | None:
    value = (value or "").strip()
    return value[:limit] if value else None


def account_for(role: str, sub: str) -> tuple[SessionAccountType, str] | None:
    """The (account_type, account_ref) a signed-in user's rows are filed under."""
    account_type = ACCOUNT_BY_ROLE.get(role)
    if account_type is None:
        return None
    return account_type, sub


def claims_for(db: Session, account_type: SessionAccountType | str, account_ref: str):
    """Rebuild an account's token claims from the database.

    Returns (role, name, classes, menus, force_password_change, staff_row) — or
    None when the account no longer exists: a staff row that is missing or
    `deleted` (`pending_delete` staff can still sign in). Admin and super-admin
    always exist. Login and refresh both mint their claims from this, so the two
    can never disagree; the "All" class sentinel is expanded exactly as login
    always did (Gotcha #21).
    """
    account_type = _account(account_type)
    if account_type is SessionAccountType.super_admin:
        return "super_admin", "Super Admin", [], [], False, None
    if account_type is SessionAccountType.admin:
        return "admin", "Administrator", [], [], False, None
    try:
        staff_id = int(account_ref)
    except (TypeError, ValueError):
        return None
    staff = db.get(Staff, staff_id)
    if staff is None or staff.status == RecordStatus.deleted:
        return None
    classes = expand_classes([c.class_name for c in staff.classes])
    menus = list(staff.allowed_menus or [])
    return "staff", staff.name, classes, menus, bool(staff.force_password_change), staff


def is_expired(row: DeviceSession, now: datetime | None = None) -> bool:
    now = now or utcnow()
    return row.expires_at <= now or row.absolute_expires_at <= now


def is_live(row: DeviceSession, now: datetime | None = None) -> bool:
    """Usable as presented: not revoked, not rotated, not expired."""
    return row.revoked_at is None and row.rotated_at is None and not is_expired(row, now)


def effective_expiry(row: DeviceSession) -> datetime:
    """When this token stops working: the sliding expiry, capped by the absolute one."""
    return min(row.expires_at, row.absolute_expires_at)


def find_by_raw(db: Session, raw: str | None) -> DeviceSession | None:
    if not raw:
        return None
    return db.execute(
        select(DeviceSession).where(DeviceSession.token_hash == hash_refresh_token(raw))
    ).scalars().first()


def issue(
    db: Session,
    *,
    account_type: SessionAccountType | str,
    account_ref: str,
    platform: SessionPlatform | str,
    device_name: str,
    via: SessionVia | str,
    ip: str | None,
    user_agent: str | None,
) -> tuple[DeviceSession, str]:
    """Open a new family for a device that just signed in. Returns (row, raw_token)."""
    now = utcnow()
    raw, token_hash = generate_refresh_token()
    row = DeviceSession(
        account_type=_account(account_type),
        account_ref=str(account_ref),
        token_hash=token_hash,
        family_id=secrets.token_hex(16),
        platform=SessionPlatform(platform),
        device_name=(device_name or "").strip()[:120],
        via=SessionVia(via),
        ip=_clip(ip, 45),
        user_agent=_clip(user_agent, 200),
        created_at=now,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_DAYS),
        absolute_expires_at=now + timedelta(days=settings.REFRESH_TOKEN_MAX_DAYS),
    )
    db.add(row)
    db.flush()
    return row, raw


def rotate(
    db: Session,
    row: DeviceSession,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[DeviceSession, str]:
    """Consume `row` and hand its device a fresh token in the same family.

    The new row slides `expires_at` out by REFRESH_TOKEN_DAYS and keeps the
    family's `absolute_expires_at`. The old row is marked used + rotated and
    points at its successor; its `revoked_at` stays NULL on purpose so the
    lost-response grace can still tell "rotated a moment ago" from "dead".
    """
    now = utcnow()
    raw, token_hash = generate_refresh_token()
    new = DeviceSession(
        account_type=row.account_type,
        account_ref=row.account_ref,
        token_hash=token_hash,
        family_id=row.family_id,
        platform=row.platform,
        device_name=row.device_name,
        via=row.via,
        ip=_clip(ip, 45) or row.ip,
        user_agent=_clip(user_agent, 200) or row.user_agent,
        created_at=now,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_DAYS),
        absolute_expires_at=row.absolute_expires_at,
    )
    db.add(new)
    db.flush()
    row.last_used_at = now
    row.rotated_at = now
    row.replaced_by_id = new.id
    row.revoked_reason = "rotated"
    db.flush()
    return new, raw


def revoke_family(db: Session, family_id: str, *, reason: str) -> int:
    """End every not-yet-revoked row of one device's family. Returns rows touched."""
    now = utcnow()
    rows = db.execute(
        select(DeviceSession).where(
            DeviceSession.family_id == family_id, DeviceSession.revoked_at.is_(None)
        )
    ).scalars().all()
    for r in rows:
        r.revoked_at = now
        r.revoked_reason = reason
    db.flush()
    return len(rows)


def revoke_sessions(
    db: Session,
    account_type: SessionAccountType | str,
    account_ref: str,
    *,
    reason: str,
    except_sid: int | None = None,
    only_via: SessionVia | str | None = None,
) -> int:
    """Revoke an account's sessions.

    `except_sid` keeps one row (the caller's own device) alive; `only_via`
    limits it to sessions opened with that credential (e.g. the temporary
    password). Returns how many LIVE sessions — devices — were ended; rotated
    predecessors are closed too but not counted.
    """
    now = utcnow()
    conds = [
        DeviceSession.account_type == _account(account_type),
        DeviceSession.account_ref == str(account_ref),
        DeviceSession.revoked_at.is_(None),
    ]
    if except_sid is not None:
        conds.append(DeviceSession.id != except_sid)
    if only_via is not None:
        conds.append(DeviceSession.via == SessionVia(only_via))
    rows = db.execute(select(DeviceSession).where(*conds)).scalars().all()
    ended = 0
    for r in rows:
        if is_live(r, now):
            ended += 1
        r.revoked_at = now
        r.revoked_reason = reason
    db.flush()
    return ended


def revoke_sessions_hook(
    db: Session,
    account_type: SessionAccountType | str,
    account_ref: str,
    *,
    reason: str,
    except_sid: int | None = None,
    only_via: SessionVia | str | None = None,
) -> int:
    """Router hook: call right AFTER the request's own commit.

    Commits the revocation itself and never raises — a credential change that
    already committed must not turn into a 500 because the bookkeeping failed
    (same contract as the notification helpers).
    """
    try:
        ended = revoke_sessions(
            db, account_type, account_ref, reason=reason, except_sid=except_sid, only_via=only_via
        )
        db.commit()
        if ended:
            log.info(
                "device sessions revoked",
                extra={
                    "event": "device_sessions_revoked",
                    "reason": reason,
                    "account_type": _account(account_type).value,
                    "account_ref": str(account_ref),
                    "ended": ended,
                },
            )
        return ended
    except Exception:
        log.exception(
            "device session revocation hook failed",
            extra={"event": "device_sessions_revoke_failed", "reason": reason},
        )
        try:
            db.rollback()
        except Exception:
            pass
        return 0


def live_sessions(db: Session, account_type: SessionAccountType | str, account_ref: str) -> list[DeviceSession]:
    """The account's usable rows, newest first."""
    now = utcnow()
    return list(
        db.execute(
            select(DeviceSession)
            .where(
                DeviceSession.account_type == _account(account_type),
                DeviceSession.account_ref == str(account_ref),
                DeviceSession.revoked_at.is_(None),
                DeviceSession.rotated_at.is_(None),
                DeviceSession.expires_at > now,
                DeviceSession.absolute_expires_at > now,
            )
            .order_by(DeviceSession.id.desc())
        ).scalars().all()
    )


def list_sessions(
    db: Session, account_type: SessionAccountType | str, account_ref: str, *, current_sid: int | None
) -> list[dict]:
    """One entry per signed-in device, for GET /auth/sessions.

    `created_at` is when the device first signed in (the start of its family —
    derived from the absolute cap, which rotation carries unchanged, so pruning
    old rotated rows cannot move it) and `last_used_at` the family's most recent
    refresh (NULL until the first one).
    """
    rows = live_sessions(db, account_type, account_ref)
    if not rows:
        return []
    last_used = dict(
        db.execute(
            select(DeviceSession.family_id, func.max(DeviceSession.last_used_at))
            .where(DeviceSession.family_id.in_([r.family_id for r in rows]))
            .group_by(DeviceSession.family_id)
        ).all()
    )
    cap = timedelta(days=settings.REFRESH_TOKEN_MAX_DAYS)
    return [
        {
            "id": r.id,
            "device_name": r.device_name,
            "platform": r.platform.value,
            "created_at": r.absolute_expires_at - cap,
            "last_used_at": last_used.get(r.family_id),
            "is_current": current_sid is not None and r.id == current_sid,
        }
        for r in rows
    ]


def prune(db: Session, account_type: SessionAccountType | str, account_ref: str) -> int:
    """Delete the account's rows that have been dead for more than PRUNE_AFTER_DAYS.

    Dead = revoked, rotated (a rotated row is only good for the 60-second grace)
    or past either expiry. Called from login, so the table never needs a cron.
    """
    cutoff = utcnow() - timedelta(days=PRUNE_AFTER_DAYS)
    result = db.execute(
        delete(DeviceSession).where(
            DeviceSession.account_type == _account(account_type),
            DeviceSession.account_ref == str(account_ref),
            or_(
                DeviceSession.revoked_at < cutoff,
                DeviceSession.rotated_at < cutoff,
                DeviceSession.expires_at < cutoff,
                DeviceSession.absolute_expires_at < cutoff,
            ),
        )
    )
    db.flush()
    return int(result.rowcount or 0)
