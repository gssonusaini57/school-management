from dataclasses import dataclass
from fastapi import Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
from .db import get_db
from .security import decode_token
from .constants import CLASSES, expand_classes, is_all_sentinel

ADMIN_ROLES = ("admin", "super_admin")


@dataclass
class CurrentUser:
    sub: str
    role: str
    name: str
    allowed_classes: list[str]
    allowed_menus: list[str]
    # Device-session id the access token was minted from (see models/device_session.py).
    # None for a sign-in without "remember me" and for tokens issued before device
    # sessions existed, which stay valid until they expire.
    sid: int | None = None


def _parse(token: str) -> CurrentUser:
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    sid = payload.get("sid")
    try:
        sid = int(sid) if sid is not None else None
    except (TypeError, ValueError):
        sid = None
    return CurrentUser(
        sub=str(payload.get("sub")),
        role=payload.get("role", ""),
        name=payload.get("name", ""),
        # Expand the "All" sentinel so tokens issued before the fix (still valid
        # ~8h) also surface the concrete class list for /me and authorization.
        allowed_classes=expand_classes(payload.get("allowed_classes", []) or []),
        allowed_menus=payload.get("allowed_menus", []) or [],
        sid=sid,
    )


def current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    return _parse(authorization.split(" ", 1)[1].strip())


def current_user_sse(token: str | None = Query(default=None)) -> CurrentUser:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    return _parse(token)


def require_admin(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    # super_admin inherits all admin powers.
    if user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def require_super_admin(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    if user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super-admin only")
    return user


def assert_class_allowed(user: CurrentUser, class_name: str | None) -> None:
    if user.role in ADMIN_ROLES:
        return
    if class_name is None:
        return
    if any(is_all_sentinel(c) for c in user.allowed_classes):
        return
    if class_name not in user.allowed_classes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Class not in scope")


def classes_in_scope(user: CurrentUser) -> list[str]:
    """The classes a user may see, in CLASSES order: every class for admins and
    the super-admin, the user's own classes for staff. A teacher with no classes
    gets an empty list, never every class."""
    if user.role in ADMIN_ROLES:
        return list(CLASSES)
    own = set(expand_classes(user.allowed_classes or []))
    return [c for c in CLASSES if c in own]


def has_menu(user: CurrentUser, key: str) -> bool:
    """Mirror of the web's canAccessMenu: admins pass, staff need the grant."""
    return user.role in ADMIN_ROLES or key in (user.allowed_menus or [])


def _menu_refused(what: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Your account doesn't have access to {what}. Ask an admin to enable it.",
    )


def assert_menu(user: CurrentUser, key: str, what: str) -> None:
    """Enforce a staff menu grant on the server, not just in the navigation."""
    if not has_menu(user, key):
        raise _menu_refused(what)


def require_menu(key: str, what: str):
    """Dependency form of assert_menu for routes behind one menu."""
    def dep(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        assert_menu(user, key, what)
        return user
    return dep


def require_any_menu(*keys: str, what: str):
    """Dependency for routes open to holders of any one of several menus.
    Admins always pass; staff need at least one of the grants."""
    def dep(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in ADMIN_ROLES and not any(has_menu(user, k) for k in keys):
            raise _menu_refused(what)
        return user
    return dep


def db_dep(db: Session = Depends(get_db)) -> Session:
    return db
