from sqlalchemy import BigInteger, String, DateTime, ForeignKey, LargeBinary, Enum, UniqueConstraint, func
from sqlalchemy.dialects.mysql import LONGBLOB
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import enum
from ..db import Base


class DocumentKind(str, enum.Enum):
    photo = "photo"
    dob_cert = "dob_cert"
    aadhar = "aadhar"


class StudentDocument(Base):
    __tablename__ = "student_documents"
    __table_args__ = (UniqueConstraint("student_id", "kind", name="uq_student_kind"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[DocumentKind] = mapped_column(Enum(DocumentKind), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(80), nullable=False, default="application/octet-stream")
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    data: Mapped[bytes] = mapped_column(LONGBLOB, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
