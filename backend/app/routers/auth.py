import re
import secrets
import hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import select, func, update
from ..deps import db_dep, current_user, CurrentUser, require_admin
from ..schemas.auth import (
    LoginRequest,
    LoginResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)
from ..models.admin import AdminAuth, SuperAdminAuth
from ..models.staff import Staff
from ..models.record_status import RecordStatus
from ..models.password_reset import PasswordResetToken, ResetAccountType
from ..security import hash_password, verify_password, create_token
from ..config import settings
from ..logging_config import get_logger
from ..mailer import send_email, EmailNotConfigured
from ..email_templates import password_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])
log = get_logger("app.auth")

# Hardcoded identifiers for the singleton admin / super-admin accounts.
# Staff log in by their own email or phone (server-managed).
ADMIN_EMAIL = "nsnishasaini57@gmail.com"
SUPER_ADMIN_EMAIL = "gssonusaini57@gmail.com"

_DIGIT_RE = re.compile(r"^\d+$")


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


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(db_dep)):
    identifier = (payload.identifier or "").strip()
    password = payload.password or ""
    if not identifier or not password:
        log.warning(
            "login rejected",
            extra={"event": "login_rejected", "reason": "missing_credentials"},
        )
        raise HTTPException(status_code=400, detail="Email/phone and password are required")

    ident_lower = identifier.lower()

    # Super-admin
    if ident_lower == SUPER_ADMIN_EMAIL:
        row = _ensure_super_admin_seed(db)
        if not verify_password(password, row.password_hash):
            log.warning("login failed", extra={"event": "login_failed", "role": "super_admin"})
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_token(sub="superadmin", role="super_admin", name="Super Admin", allowed_classes=[])
        log.info("login success", extra={"event": "login_success", "role": "super_admin"})
        return LoginResponse(token=token, role="super_admin", name="Super Admin", allowed_classes=[])

    # Admin
    if ident_lower == ADMIN_EMAIL:
        row = _ensure_admin_seed(db)
        if not verify_password(password, row.password_hash):
            log.warning("login failed", extra={"event": "login_failed", "role": "admin"})
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_token(sub="admin", role="admin", name="Administrator", allowed_classes=[])
        log.info("login success", extra={"event": "login_success", "role": "admin"})
        return LoginResponse(token=token, role="admin", name="Administrator", allowed_classes=[])

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
        log.warning("login failed", extra={"event": "login_failed", "role": "staff", "identifier_kind": "email" if "@" in ident_lower else "phone"})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    classes = [c.class_name for c in matched.classes]
    menus = list(matched.allowed_menus or [])
    token = create_token(
        sub=str(matched.id),
        role="staff",
        name=matched.name,
        allowed_classes=classes,
        allowed_menus=menus,
    )
    log.info(
        "login success",
        extra={
            "event": "login_success",
            "role": "staff",
            "subject": str(matched.id),
            "staff_name": matched.name,
            "via": "temp_password" if (ok_temp and not ok_real) else "password",
        },
    )
    return LoginResponse(
        token=token,
        role="staff",
        name=matched.name,
        allowed_classes=classes,
        allowed_menus=menus,
        # Only the teacher's real password can be "must change"; a temp login skips it.
        force_password_change=bool(matched.force_password_change) and ok_real,
    )


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
    return MessageResponse(
        message="Your password has been reset. You can now sign in with your new password."
    )


@router.post("/logout", status_code=204)
def logout(user: CurrentUser = Depends(current_user)):
    log.info("logout", extra={"event": "logout", "subject": user.sub, "role": user.role})
    return None


@router.get("/me")
def me(user: CurrentUser = Depends(current_user)):
    return {
        "role": user.role,
        "name": user.name,
        "allowed_classes": user.allowed_classes,
        "allowed_menus": user.allowed_menus,
    }
