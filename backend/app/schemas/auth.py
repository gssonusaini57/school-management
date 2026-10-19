from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    """What the signing-in device calls itself — shown back in GET /auth/sessions."""

    name: str = ""
    platform: Literal["android", "web"] = "web"


class LoginRequest(BaseModel):
    """Unified login.

    `identifier` may be:
      - the literal admin email   `gssonusaini57@gmail.com`
      - the literal super-admin email `khalsainternationalschool@gmail.com`
      - a staff `email`
      - a staff `phone` (digits only)

    `remember` opens a device session (refresh token) so the sign-in outlives the
    one-hour access token: Android gets `refresh_token` in the response body, the
    web gets an HttpOnly cookie instead.
    """

    identifier: str
    password: str
    remember: bool = False
    device: DeviceInfo | None = None


class LoginResponse(BaseModel):
    token: str
    role: str
    name: str
    allowed_classes: list[str]
    allowed_menus: list[str] = []
    force_password_change: bool = False
    # Device-session id behind `token` (null for a sign-in without `remember`).
    session_id: int | None = None
    # Android only, with `remember`: the web receives the token as a cookie.
    refresh_token: str | None = None
    refresh_expires_at: datetime | None = None


class RefreshRequest(BaseModel):
    """Android sends the token in the body; the web sends nothing (cookie)."""

    refresh_token: str | None = None


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class DeviceSessionOut(BaseModel):
    id: int
    device_name: str
    platform: str
    created_at: datetime | None = None
    last_used_at: datetime | None = None
    is_current: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


class ForgotPasswordRequest(BaseModel):
    """`identifier` is the same email/phone accepted by /auth/login."""

    identifier: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=6)


class MessageResponse(BaseModel):
    message: str
