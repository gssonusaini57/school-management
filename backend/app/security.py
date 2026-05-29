import hashlib
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from .config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_reset_token() -> tuple[str, str]:
    """Return (raw_token, token_hash).

    The raw token goes in the emailed link; only its SHA-256 hash is persisted.
    URL-safe so it drops straight into a query string.
    """
    raw = secrets.token_urlsafe(48)
    return raw, hash_reset_token(raw)


def hash_reset_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(password, hashed)
    except Exception:
        return False


def create_token(
    *,
    sub: str,
    role: str,
    name: str,
    allowed_classes: list[str],
    allowed_menus: list[str] | None = None,
) -> str:
    payload = {
        "sub": sub,
        "role": role,
        "name": name,
        "allowed_classes": allowed_classes,
        # Empty list for admin/super_admin (frontend treats it as "all menus").
        "allowed_menus": list(allowed_menus or []),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
