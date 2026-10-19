import re
import secrets
import hashlib
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import select, func, update
from ..deps import db_dep, current_user, CurrentUser, require_admin
from ..schemas.auth import (
    DeviceInfo,
    DeviceSessionOut,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)
from ..models.admin import AdminAuth, SuperAdminAuth
from ..models.staff import Staff
from ..models.record_status import RecordStatus
from ..models.password_reset import PasswordResetToken, ResetAccountType
from ..models.device_session import DeviceSession, SessionAccountType, SessionPlatform, SessionVia
from ..security import hash_password, verify_password, create_token, decode_token_ignoring_expiry
from ..config import settings
from ..logging_config import get_logger
from ..mailer import send_email, EmailNotConfigured
from ..email_templates import password_reset_email
from ..services import device_sessions as ds
from ..services.device_sessions import ADMIN_SUB, SUPER_ADMIN_SUB, revoke_sessions_hook

router = APIRouter(prefix="/auth", tags=["auth"])
log = get_logger("app.auth")

# Hardcoded identifiers for the singleton admin / super-admin accounts.
# Staff log in by their own email or phone (server-managed).
ADMIN_EMAIL = "gssonusaini57@gmail.com"
SUPER_ADMIN_EMAIL = "khalsainternationalschool@gmail.com"

_DIGIT_RE = re.compile(r"^\d+$")

# --- Brute-force guard --------------------------------------------------------
# Failed sign-ins per lowercased identifier inside a sliding window, kept in this
# process (one gunicorn worker serves the app — see events.py). Once an identifier
# has LOGIN_FAIL_LIMIT failures in the window, the next attempt is refused with
# 429 before any password is checked; a successful sign-in clears the counter.
LOGIN_FAIL_LIMIT = 10
LOGIN_FAIL_WINDOW_SECONDS = 15 * 60
TOO_MANY_ATTEMPTS_MSG = "Too many failed sign-in attempts. Try again in 15 minutes."
_login_failures: dict[str, deque[float]] = {}
_login_failures_lock = threading.Lock()
_FAILURE_KEYS_SWEEP_AT = 10_000

# Refresh-token rules (see services/device_sessions.py for the row semantics).
SIGNED_OUT_MSG = "Signed out on this device. Sign in again."
ROTATION_GRACE = timedelta(seconds=60)


def _recent_failures(key: str, now: float) -> deque[float]:
    """The identifier's failures still inside the window (older ones dropped)."""
    q = _login_failures.setdefault(key, deque())
    cutoff = now - LOGIN_FAIL_WINDOW_SECONDS
    while q and q[0] <= cutoff:
        q.popleft()
    return q


def _refuse_if_locked(key: str) -> None:
    with _login_failures_lock:
        q = _recent_failures(key, time.monotonic())
        if len(q) >= LOGIN_FAIL_LIMIT:
            log.warning("login throttled", extra={"event": "login_throttled", "failures": len(q)})
            raise HTTPException(status_code=429, detail=TOO_MANY_ATTEMPTS_MSG)
        if not q:
            _login_failures.pop(key, None)


def _record_failure(key: str) -> None:
    with _login_failures_lock:
        now = time.monotonic()
        if len(_login_failures) > _FAILURE_KEYS_SWEEP_AT:
            # Someone is cycling identifiers: drop every key whose window is empty.
            for k in [k for k in _login_failures if not _recent_failures(k, now)]:
                _login_failures.pop(k, None)
        _recent_failures(key, now).append(now)


def _clear_failures(key: str) -> None:
    with _login_failures_lock:
        _login_failures.pop(key, None)


def reset_login_failures() -> None:
    """Forget every counter (tests)."""
    with _login_failures_lock:
        _login_failures.clear()


def _ensure_admin_seed(db: Session) -> AdminAuth:
    row = db.get(AdminAuth, 1)
    if row is not None:
        return row
    try:
        row = AdminAuth(id=1, password_hash=hash_password(settings.ADMIN_DEFAULT_PASSWORD))
        db.add(row)
        db.commit()
        db.refresh(row)
        log.info("admin seeded", extra={"event": "admin_seeded"})
        return row
    except IntegrityError:
        db.rollback()
        existing = db.get(AdminAuth, 1)
        if existing is None:
            raise
        return existing


def _ensure_super_admin_seed(db: Session) -> SuperAdminAuth:
    row = db.get(SuperAdminAuth, 1)
    if row is not None:
        return row
    try:
        row = SuperAdminAuth(id=1, password_hash=hash_password(settings.SUPER_ADMIN_DEFAULT_PASSWORD))
        db.add(row)
        db.commit()
        db.refresh(row)
        log.info("super_admin seeded", extra={"event": "super_admin_seeded"})
        return row
    except IntegrityError:
        db.rollback()
        existing = db.get(SuperAdminAuth, 1)
        if existing is None:
            raise
        return existing


def _normalize_phone(s: str) -> str:
    """Reduce to digits only (strip +, spaces, dashes)."""
    return re.sub(r"\D", "", s)


# --- Refresh-token plumbing ----------------------------------------------------

def _is_https(request: Request) -> bool:
    return request.url.scheme == "https"


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _set_refresh_cookie(response: Response, request: Request, raw: str) -> None:
    response.set_cookie(
        settings.AUTH_COOKIE_NAME,
        raw,
        max_age=settings.REFRESH_TOKEN_DAYS * 86400,
        path=settings.AUTH_COOKIE_PATH,
        secure=_is_https(request),
        httponly=True,
        samesite="Strict",  # type: ignore[arg-type]  # Starlette lower-cases the check, emits as given
    )


def _clear_refresh_cookie(response: Response, request: Request) -> None:
    response.delete_cookie(
        settings.AUTH_COOKIE_NAME,
        path=settings.AUTH_COOKIE_PATH,
        secure=_is_https(request),
        httponly=True,
        samesite="Strict",  # type: ignore[arg-type]
    )


def _attach_refresh(out: dict, response: Response, request: Request, row: DeviceSession, raw: str) -> None:
    """Hand the device its refresh token: Android in the body, the web as an HttpOnly cookie."""
    if row.platform == SessionPlatform.android:
        out["refresh_token"] = raw
        out["refresh_expires_at"] = ds.effective_expiry(row)
    else:
        _set_refresh_cookie(response, request, raw)


def _presented_refresh_token(request: Request, payload: RefreshRequest | LogoutRequest | None) -> tuple[str | None, bool]:
    """The refresh token a request carries, and whether it came from the cookie."""
    if payload is not None and payload.refresh_token and payload.refresh_token.strip():
        return payload.refresh_token.strip(), False
    return (request.cookies.get(settings.AUTH_COOKIE_NAME) or None), True


def _signed_out(request: Request, clear_cookie: bool) -> HTTPException:
    """401 for a refresh token that no longer works; drops the web's dead cookie too."""
    headers = None
    if clear_cookie:
        tmp = Response()
        _clear_refresh_cookie(tmp, request)
        headers = {"set-cookie": tmp.headers["set-cookie"]}
    return HTTPException(status_code=401, detail=SIGNED_OUT_MSG, headers=headers)


def _signed_in(
    db: Session,
    request: Request,
    response: Response,
    payload: LoginRequest,
    *,
    account_type: SessionAccountType,
    account_ref: str,
    via: SessionVia,
) -> LoginResponse:
    """Mint the access token for an authenticated account and, with `remember`,
    open a device session for the signing-in device."""
    role, name, classes, menus, must_change, _staff = ds.claims_for(db, account_type, account_ref)
    out: dict = {
        "role": role,
        "name": name,
        "allowed_classes": classes,
        "allowed_menus": menus,
        # Only the account's own password can be "must change"; a temp login skips it.
        "force_password_change": must_change and via == SessionVia.password,
    }
    # Housekeeping: rows of this account dead for 30+ days go now, so the table
    # never needs a cron.
    pruned = ds.prune(db, account_type, account_ref)
    sid: int | None = None
    if payload.remember:
        device = payload.device or DeviceInfo()
        row, raw = ds.issue(
            db,
            account_type=account_type,
            account_ref=account_ref,
            platform=device.platform,
            device_name=device.name,
            via=via,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        sid = row.id
    if pruned or payload.remember:
        db.commit()
    if payload.remember:
        _attach_refresh(out, response, request, row, raw)
        log.info(
            "device session opened",
            extra={
                "event": "device_session_opened",
                "role": role,
                "subject": account_ref,
                "session_id": row.id,
                "platform": row.platform.value,
                "device_name": row.device_name,
                "via": via.value,
            },
        )
    token = create_token(
        sub=account_ref, role=role, name=name, allowed_classes=classes, allowed_menus=menus, sid=sid
    )
    return LoginResponse(token=token, session_id=sid, **out)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(db_dep)):
    identifier = (payload.identifier or "").strip()
    password = payload.password or ""
    if not identifier or not password:
        log.warning(
            "login rejected",
            extra={"event": "login_rejected", "reason": "missing_credentials"},
        )
        raise HTTPException(status_code=400, detail="Email/phone and password are required")

    ident_lower = identifier.lower()
    _refuse_if_locked(ident_lower)

    # Super-admin
    if ident_lower == SUPER_ADMIN_EMAIL:
        row = _ensure_super_admin_seed(db)
        if not verify_password(password, row.password_hash):
            _record_failure(ident_lower)
            log.warning("login failed", extra={"event": "login_failed", "role": "super_admin"})
            raise HTTPException(status_code=401, detail="Invalid credentials")
        _clear_failures(ident_lower)
        log.info("login success", extra={"event": "login_success", "role": "super_admin"})
        return _signed_in(
            db, request, response, payload,
            account_type=SessionAccountType.super_admin, account_ref=SUPER_ADMIN_SUB, via=SessionVia.password,
        )

    # Admin
    if ident_lower == ADMIN_EMAIL:
        row = _ensure_admin_seed(db)
        if not verify_password(password, row.password_hash):
            _record_failure(ident_lower)
            log.warning("login failed", extra={"event": "login_failed", "role": "admin"})
            raise HTTPException(status_code=401, detail="Invalid credentials")
        _clear_failures(ident_lower)
        log.info("login success", extra={"event": "login_success", "role": "admin"})
        return _signed_in(
            db, request, response, payload,
            account_type=SessionAccountType.admin, account_ref=ADMIN_SUB, via=SessionVia.password,
        )

    # Staff — try email first, then phone (digits-only match).
    matched: Staff | None = None
    if "@" in ident_lower:
        matched = db.execute(
            select(Staff).where(
                func.lower(Staff.email) == ident_lower,
                Staff.status != RecordStatus.deleted,
            )
        ).scalars().first()
    else:
        phone = _normalize_phone(identifier)
        if phone:
            # Compare digit-normalized to handle stored values with spaces/dashes.
            matched = db.execute(
                select(Staff).where(
                    Staff.phone == phone,
                    Staff.status != RecordStatus.deleted,
                )
            ).scalars().first()
            if matched is None:
                # Fallback: scan + normalize in case stored phones aren't pure digits.
                candidates = db.execute(
                    select(Staff).where(Staff.status != RecordStatus.deleted)
                ).scalars().all()
                for s in candidates:
                    if _normalize_phone(s.phone or "") == phone:
                        matched = s
                        break

    # Two valid credentials: the teacher's own password, OR an admin-set temporary
    # password (a second hash that does not replace the real one — used to cover an
    # absence). A temp login never triggers force-password-change (it's not the teacher).
    ok_real = matched is not None and verify_password(password, matched.password_hash)
    ok_temp = (
        matched is not None
        and bool(matched.temp_password_hash)
        and verify_password(password, matched.temp_password_hash)
    )
    if matched is None or not (ok_real or ok_temp):
        _record_failure(ident_lower)
        log.warning("login failed", extra={"event": "login_failed", "role": "staff", "identifier_kind": "email" if "@" in ident_lower else "phone"})
        raise HTTPException(status_code=401, detail="Invalid credentials")
    _clear_failures(ident_lower)

    via = SessionVia.temp_password if (ok_temp and not ok_real) else SessionVia.password
    log.info(
        "login success",
        extra={
            "event": "login_success",
            "role": "staff",
            "subject": str(matched.id),
            "staff_name": matched.name,
            "via": via.value,
        },
    )
    # Claims (classes with the "All" sentinel expanded, menus, force-change flag)
    # come from claims_for, the same helper /auth/refresh rebuilds them with.
    return _signed_in(
        db, request, response, payload,
        account_type=SessionAccountType.staff, account_ref=str(matched.id), via=via,
    )


@router.post("/refresh", response_model=LoginResponse)
def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    db: Session = Depends(db_dep),
):
    """Trade a refresh token for a fresh access token (+ a rotated refresh token).

    No Bearer needed. The token comes from the body (Android) or the cookie (web).
    A consumed token coming back inside 60 s with an unused successor is treated as
    a lost response and healed; otherwise it is a replay and the whole family dies.
    """
    raw, from_cookie = _presented_refresh_token(request, payload)
    now = ds.utcnow()
    row = ds.find_by_raw(db, raw)
    if row is None or row.revoked_at is not None or ds.is_expired(row, now):
        why = "unknown" if row is None else ("revoked" if row.revoked_at is not None else "expired")
        log.warning("refresh refused", extra={"event": "refresh_refused", "reason": why})
        raise _signed_out(request, from_cookie)

    if row.rotated_at is not None:
        successor = db.get(DeviceSession, row.replaced_by_id) if row.replaced_by_id else None
        successor_unused = (
            successor is not None and successor.last_used_at is None and successor.revoked_at is None
        )
        if now - row.rotated_at <= ROTATION_GRACE and successor_unused:
            # The device never saw the successor (lost response): retire that unused
            # token and rotate the old row again into a fresh one.
            successor.revoked_at = now
            successor.revoked_reason = "superseded"
            log.info(
                "refresh healed after lost response",
                extra={"event": "refresh_grace", "session_id": row.id, "superseded_id": successor.id},
            )
        else:
            # A consumed token came back: someone else holds a copy. Kill the family.
            ds.revoke_family(db, row.family_id, reason="replay")
            db.commit()
            log.warning(
                "refresh replay detected",
                extra={
                    "event": "refresh_replay",
                    "session_id": row.id,
                    "account_type": row.account_type.value,
                    "subject": row.account_ref,
                },
            )
            raise _signed_out(request, from_cookie)

    claims = ds.claims_for(db, row.account_type, row.account_ref)
    if claims is None:
        ds.revoke_family(db, row.family_id, reason="account_deleted")
        db.commit()
        log.warning("refresh refused", extra={"event": "refresh_refused", "reason": "account_gone"})
        raise _signed_out(request, from_cookie)
    role, name, classes, menus, must_change, staff = claims
    if row.via == SessionVia.temp_password and (staff is None or not staff.temp_password_hash):
        # The temporary password this session was opened with has been cleared.
        ds.revoke_family(db, row.family_id, reason="temp_password_cleared")
        db.commit()
        log.warning("refresh refused", extra={"event": "refresh_refused", "reason": "temp_password_cleared"})
        raise _signed_out(request, from_cookie)

    new_row, new_raw = ds.rotate(
        db, row, ip=_client_ip(request), user_agent=request.headers.get("user-agent")
    )
    db.commit()
    out: dict = {
        "role": role,
        "name": name,
        "allowed_classes": classes,
        "allowed_menus": menus,
        "force_password_change": must_change and row.via == SessionVia.password,
    }
    _attach_refresh(out, response, request, new_row, new_raw)
    token = create_token(
        sub=row.account_ref, role=role, name=name, allowed_classes=classes, allowed_menus=menus, sid=new_row.id
    )
    log.info(
        "refresh success",
        extra={
            "event": "refresh_success",
            "role": role,
            "subject": row.account_ref,
            "session_id": new_row.id,
            "platform": new_row.platform.value,
        },
    )
    return LoginResponse(token=token, session_id=new_row.id, **out)


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    payload: LogoutRequest | None = None,
    authorization: str | None = Header(default=None),
    db: Session = Depends(db_dep),
):
    """End this device's session. The Bearer is optional and may be expired —
    signing out must always work. Revokes the refresh token's whole family
    (whichever generation the device still holds) and clears the web cookie."""
    sub, role = "-", "-"
    if authorization and authorization.lower().startswith("bearer "):
        claims = decode_token_ignoring_expiry(authorization.split(" ", 1)[1].strip())
        if claims:
            sub, role = str(claims.get("sub") or "-"), str(claims.get("role") or "-")
    raw, _from_cookie = _presented_refresh_token(request, payload)
    row = ds.find_by_raw(db, raw)
    ended = 0
    if row is not None:
        ended = ds.revoke_family(db, row.family_id, reason="logout")
        db.commit()
        sub, role = row.account_ref, row.account_type.value
    log.info("logout", extra={"event": "logout", "subject": sub, "role": role, "session_ended": ended > 0})
    response = Response(status_code=204)
    _clear_refresh_cookie(response, request)
    return response


@router.get("/sessions", response_model=list[DeviceSessionOut])
def list_sessions(user: CurrentUser = Depends(current_user), db: Session = Depends(db_dep)):
    """The caller's signed-in devices (live refresh tokens), newest first."""
    account = ds.account_for(user.role, user.sub)
    if account is None:
        raise HTTPException(status_code=403, detail="Unknown role")
    return ds.list_sessions(db, *account, current_sid=user.sid)


@router.delete("/sessions/{session_id}", status_code=204)
def end_session(session_id: int, user: CurrentUser = Depends(current_user), db: Session = Depends(db_dep)):
    """Sign one of the caller's own devices out. Another account's session is a 404."""
    account = ds.account_for(user.role, user.sub)
    row = db.get(DeviceSession, session_id)
    if account is None or row is None or (row.account_type, row.account_ref) != account:
        raise HTTPException(status_code=404, detail="Not found")
    ds.revoke_family(db, row.family_id, reason="user")
    db.commit()
    log.info(
        "device session ended by user",
        extra={"event": "device_session_ended", "subject": user.sub, "role": user.role, "session_id": row.id},
    )
    return Response(status_code=204)


@router.post("/change-password", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(db_dep),
):
    # Each role changes its own singleton's password.
    if user.role == "super_admin":
        row = _ensure_super_admin_seed(db)
    else:
        row = _ensure_admin_seed(db)
    if not verify_password(payload.current_password, row.password_hash):
        log.warning("password change failed", extra={"event": "password_change_failed", "subject": user.sub})
        raise HTTPException(status_code=400, detail="Current password incorrect")
    row.password_hash = hash_password(payload.new_password)
    db.commit()
    log.info("password changed", extra={"event": "password_changed", "subject": user.sub})
    # Every other device of this account must sign in again; this one stays.
    account = ds.account_for(user.role, user.sub)
    if account is not None:
        revoke_sessions_hook(db, *account, reason="password_changed", except_sid=user.sid)


# Always returned by /forgot-password regardless of whether the account exists —
# never reveal which emails/phones are registered (account-enumeration defense).
_GENERIC_FORGOT_MSG = (
    "If an account with that email or phone exists, a password reset link has been sent."
)


def _resolve_reset_account(db: Session, identifier: str):
    """Map a login identifier to (account_type, account_ref, email, display_name).

    Returns None if no account matches or the matched staff has no email.
    Mirrors the lookup order in `login()`.
    """
    ident = (identifier or "").strip()
    if not ident:
        return None
    ident_lower = ident.lower()

    if ident_lower == SUPER_ADMIN_EMAIL:
        return (ResetAccountType.super_admin, SUPER_ADMIN_EMAIL, SUPER_ADMIN_EMAIL, "Super Admin")
    if ident_lower == ADMIN_EMAIL:
        return (ResetAccountType.admin, ADMIN_EMAIL, ADMIN_EMAIL, "Administrator")

    matched: Staff | None = None
    if "@" in ident_lower:
        matched = db.execute(
            select(Staff).where(
                func.lower(Staff.email) == ident_lower,
                Staff.status != RecordStatus.deleted,
            )
        ).scalars().first()
    else:
        phone = _normalize_phone(ident)
        if phone:
            matched = db.execute(
                select(Staff).where(
                    Staff.phone == phone,
                    Staff.status != RecordStatus.deleted,
                )
            ).scalars().first()
            if matched is None:
                candidates = db.execute(
                    select(Staff).where(Staff.status != RecordStatus.deleted)
                ).scalars().all()
                for s in candidates:
                    if _normalize_phone(s.phone or "") == phone:
                        matched = s
                        break

    if matched is None or not matched.email:
        return None
    return (ResetAccountType.staff, str(matched.id), matched.email, matched.name)


def _session_account_of_reset(row: PasswordResetToken) -> tuple[SessionAccountType, str]:
    """A reset token files admin accounts under their email; device sessions use the JWT sub."""
    if row.account_type == ResetAccountType.super_admin:
        return SessionAccountType.super_admin, SUPER_ADMIN_SUB
    if row.account_type == ResetAccountType.admin:
        return SessionAccountType.admin, ADMIN_SUB
    return SessionAccountType.staff, row.account_ref


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(db_dep)):
    acct = _resolve_reset_account(db, payload.identifier)
    if acct is None:
        # Unknown identifier — respond identically so callers can't enumerate accounts.
        log.info("password reset requested (no match)", extra={"event": "password_reset_no_match"})
        return MessageResponse(message=_GENERIC_FORGOT_MSG)

    account_type, account_ref, email, name = acct
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=settings.RESET_TOKEN_TTL_MINUTES)

    # Invalidate any earlier outstanding tokens for this account, then issue a fresh one.
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.account_type == account_type,
            PasswordResetToken.account_ref == account_ref,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    db.add(
        PasswordResetToken(
            account_type=account_type,
            account_ref=account_ref,
            email=email,
            token_hash=token_hash,
            expires_at=expires_at,
        )
    )
    db.commit()

    reset_url = f"{settings.APP_BASE_URL.rstrip('/')}/reset-password?token={raw_token}"
    subject, html, text = password_reset_email(
        recipient_name=name,
        reset_url=reset_url,
        ttl_minutes=settings.RESET_TOKEN_TTL_MINUTES,
        logo_url=settings.email_logo_url,
    )
    try:
        send_email(to=email, subject=subject, html=html, text=text)
        log.info(
            "password reset email sent",
            extra={"event": "password_reset_sent", "account_type": account_type.value},
        )
    except EmailNotConfigured:
        log.error(
            "password reset requested but SMTP is not configured",
            extra={"event": "password_reset_smtp_unconfigured"},
        )
    except Exception:
        log.exception(
            "failed to send password reset email",
            extra={"event": "password_reset_send_failed"},
        )

    return MessageResponse(message=_GENERIC_FORGOT_MSG)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(db_dep)):
    token_hash = hashlib.sha256((payload.token or "").encode()).hexdigest()
    row = db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    ).scalars().first()
    now = datetime.utcnow()
    if row is None or row.used_at is not None or row.expires_at < now:
        log.warning("password reset failed", extra={"event": "password_reset_invalid_token"})
        raise HTTPException(
            status_code=400,
            detail="This reset link is invalid or has expired. Please request a new one.",
        )

    if row.account_type == ResetAccountType.super_admin:
        acct = _ensure_super_admin_seed(db)
        acct.password_hash = hash_password(payload.new_password)
    elif row.account_type == ResetAccountType.admin:
        acct = _ensure_admin_seed(db)
        acct.password_hash = hash_password(payload.new_password)
    else:
        staff = db.get(Staff, int(row.account_ref))
        if staff is None or staff.status == RecordStatus.deleted:
            log.warning("password reset failed", extra={"event": "password_reset_staff_gone"})
            raise HTTPException(
                status_code=400,
                detail="This reset link is invalid or has expired. Please request a new one.",
            )
        staff.password_hash = hash_password(payload.new_password)
        # They've just chosen a password, so clear any forced-change flag.
        staff.force_password_change = False

    row.used_at = now
    db.commit()
    log.info(
        "password reset",
        extra={"event": "password_reset_done", "account_type": row.account_type.value},
    )
    # A forgotten password means every remembered device is suspect: sign them all out.
    revoke_sessions_hook(db, *_session_account_of_reset(row), reason="password_reset")
    return MessageResponse(
        message="Your password has been reset. You can now sign in with your new password."
    )


@router.get("/me")
def me(user: CurrentUser = Depends(current_user)):
    return {
        "role": user.role,
        "name": user.name,
        "allowed_classes": user.allowed_classes,
        "allowed_menus": user.allowed_menus,
    }
