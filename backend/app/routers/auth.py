import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ..deps import db_dep, current_user, CurrentUser, require_admin
from ..schemas.auth import LoginRequest, LoginResponse, ChangePasswordRequest
from ..models.admin import AdminAuth, SuperAdminAuth
from ..models.staff import Staff
from ..models.record_status import RecordStatus
from ..security import hash_password, verify_password, create_token
from ..config import settings
from ..logging_config import get_logger

router = APIRouter(prefix="/auth", tags=["auth"])
log = get_logger("app.auth")

# Hardcoded identifiers for the singleton admin / super-admin accounts.
# Staff log in by their own email or phone (server-managed).
ADMIN_EMAIL = "admin@direct.com"
SUPER_ADMIN_EMAIL = "superadmin@direct.com"

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

    if matched is None or not verify_password(password, matched.password_hash):
        log.warning("login failed", extra={"event": "login_failed", "role": "staff", "identifier_kind": "email" if "@" in ident_lower else "phone"})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    classes = [c.class_name for c in matched.classes]
    token = create_token(sub=str(matched.id), role="staff", name=matched.name, allowed_classes=classes)
    log.info(
        "login success",
        extra={"event": "login_success", "role": "staff", "subject": str(matched.id), "staff_name": matched.name},
    )
    return LoginResponse(
        token=token,
        role="staff",
        name=matched.name,
        allowed_classes=classes,
        force_password_change=bool(matched.force_password_change),
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


@router.post("/logout", status_code=204)
def logout(user: CurrentUser = Depends(current_user)):
    log.info("logout", extra={"event": "logout", "subject": user.sub, "role": user.role})
    return None


@router.get("/me")
def me(user: CurrentUser = Depends(current_user)):
    return {"role": user.role, "name": user.name, "allowed_classes": user.allowed_classes}
