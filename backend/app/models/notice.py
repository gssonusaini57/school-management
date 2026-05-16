from sqlalchemy import BigInteger, String, DateTime, Text, Enum, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import enum
from ..db import Base


class Priority(str, enum.Enum):
    normal = "normal"
    medium = "medium"
    high = "high"


class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[Priority] = mapped_column(Enum(Priority), nullable=False, default=Priority.normal)
    audience: Mapped[str] = mapped_column(String(80), nullable=False, default="all")
    posted_by: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
