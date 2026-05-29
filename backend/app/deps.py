from dataclasses import dataclass
from fastapi import Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
from .db import get_db
from .security import decode_token


@dataclass
class CurrentUser:
    sub: str
    role: str
    name: str
    allowed_classes: list[str]
    allowed_menus: list[str]


def _parse(token: str) -> CurrentUser:
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return CurrentUser(
        sub=str(payload.get("sub")),
        role=payload.get("role", ""),
        name=payload.get("name", ""),
        allowed_classes=payload.get("allowed_classes", []) or [],
        allowed_menus=payload.get("allowed_menus", []) or [],
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
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def require_super_admin(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    if user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super-admin only")
    return user


def assert_class_allowed(user: CurrentUser, class_name: str | None) -> None:
    if user.role in ("admin", "super_admin"):
        return
    if class_name is None:
        return
    if class_name not in user.allowed_classes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Class not in scope")


def db_dep(db: Session = Depends(get_db)) -> Session:
    return db
