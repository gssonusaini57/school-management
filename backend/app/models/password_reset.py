"""Password-reset tokens (forgot-password flow).

One row per reset request. We store only the SHA-256 hash of the raw token —
the raw token lives solely in the emailed link, so a DB leak can't be replayed.
Tokens are single-use (`used_at`) and short-lived (`expires_at`).

`account_type` + `account_ref` identify which credential to update:
  - admin / super_admin → singleton tables (ref is the literal email)
  - staff               → ref is the staff id as a string
"""
import enum
from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


class ResetAccountType(str, enum.Enum):
    admin = "admin"
    super_admin = "super_admin"
    staff = "staff"


def _reset_account_values(obj):
    return [e.value for e in obj]


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_type: Mapped[ResetAccountType] = mapped_column(
        Enum(ResetAccountType, values_callable=_reset_account_values, native_enum=False, length=20),
        nullable=False,
    )
    account_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(120), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
