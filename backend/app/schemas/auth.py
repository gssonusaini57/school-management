from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Unified login.

    `identifier` may be:
      - the literal admin email   `admin@kis.com`
      - the literal super-admin email `superadmin@kis.com`
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
    force_password_change: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)
