from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Unified login.

    `identifier` may be:
      - the literal admin email   `gssonusaini57@gmail.com`
      - the literal super-admin email `khalsainternationalschool@gmail.com`
      - a staff `email`
      - a staff `phone` (digits only)
    """

    identifier: str
    password: str


class LoginResponse(BaseModel):
    token: str
    role: str
    name: str
    allowed_classes: list[str]
    allowed_menus: list[str] = []
    force_password_change: bool = False


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
