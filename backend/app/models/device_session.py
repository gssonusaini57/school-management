"""Device sessions — the server-side half of "stay signed in".

One row per refresh token. A sign-in with `remember` opens a *family* (one
device); every refresh rotates the token into a new row of the same family and
marks the old one `rotated`. Only the SHA-256 hash of the raw token is stored,
so a database leak cannot be replayed.

Expiry is sliding (`expires_at` = last use + REFRESH_TOKEN_DAYS) under an
absolute cap (`absolute_expires_at` = first sign-in + REFRESH_TOKEN_MAX_DAYS,
carried unchanged through rotation). Revocation is explicit (`revoked_at` +
`revoked_reason`): logout, the user or an admin ending a session, a password
change, a cleared temporary password, a deleted account, or a detected replay.
A rotated row keeps `revoked_at` NULL and `revoked_reason='rotated'`, so the
60-second lost-response grace in `routers/auth.py` can still read `rotated_at`.

`account_type` + `account_ref` identify the account the way the JWT does:
`account_ref` is the token `sub` ("admin", "superadmin", or the staff id).
Naive UTC datetimes, like `password_reset_tokens`.
"""
import enum
from datetime import datetime
from sqlalchemy import BigInteger, CHAR, DateTime, Enum, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


class SessionAccountType(str, enum.Enum):
    admin = "admin"
    super_admin = "super_admin"
    staff = "staff"


class SessionPlatform(str, enum.Enum):
    android = "android"
    web = "web"


class SessionVia(str, enum.Enum):
    password = "password"
    temp_password = "temp_password"


def _values(obj):
    return [e.value for e in obj]


class DeviceSession(Base):
    __tablename__ = "device_sessions"
    __table_args__ = (
        Index("ix_device_sessions_account", "account_type", "account_ref"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_type: Mapped[SessionAccountType] = mapped_column(
        Enum(SessionAccountType, values_callable=_values, native_enum=False, length=20),
        nullable=False,
    )
    account_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    token_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, unique=True, index=True)
    family_id: Mapped[str] = mapped_column(CHAR(32), nullable=False, index=True)
    platform: Mapped[SessionPlatform] = mapped_column(
        Enum(SessionPlatform, values_callable=_values, native_enum=False, length=10),
        nullable=False,
    )
    device_name: Mapped[str] = mapped_column(String(120), nullable=False, default="", server_default="")
    via: Mapped[SessionVia] = mapped_column(
        Enum(SessionVia, values_callable=_values, native_enum=False, length=20),
        nullable=False,
    )
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    replaced_by_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
