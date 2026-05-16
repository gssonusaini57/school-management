from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from ..db import Base


class AdminAuth(Base):
    __tablename__ = "admin_auth"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )


class SuperAdminAuth(Base):
    __tablename__ = "super_admin_auth"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
