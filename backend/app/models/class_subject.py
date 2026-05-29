import enum
from sqlalchemy import BigInteger, String, Integer, DateTime, Enum, UniqueConstraint, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from ..db import Base


class SubjectCategory(str, enum.Enum):
    academic = "academic"
    co_curricular = "co_curricular"
    grading = "grading"


def _category_values() -> list[str]:
    return [c.value for c in SubjectCategory]


class ClassSubject(Base):
    __tablename__ = "class_subjects"
    __table_args__ = (
        UniqueConstraint("class_name", "subject_name", name="uq_class_subjects_class_subject"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    class_name: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    subject_name: Mapped[str] = mapped_column(String(60), nullable=False)
    subject_name_pa: Mapped[str | None] = mapped_column(String(60), nullable=True)
    category: Mapped[SubjectCategory] = mapped_column(
        Enum(SubjectCategory, values_callable=lambda obj: _category_values(), native_enum=False, length=20),
        nullable=False,
        default=SubjectCategory.academic,
        server_default=SubjectCategory.academic.value,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    components: Mapped[list["SubjectExamComponent"]] = relationship(
        "SubjectExamComponent",
        back_populates="class_subject",
        cascade="all, delete-orphan",
        order_by="SubjectExamComponent.order_index",
    )


class SubjectExamComponent(Base):
    __tablename__ = "subject_exam_components"
    __table_args__ = (
        UniqueConstraint(
            "class_subject_id", "component_name",
            name="uq_subject_exam_components_subject_component",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    class_subject_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("class_subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    component_name: Mapped[str] = mapped_column(String(80), nullable=False)
    max_marks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    class_subject: Mapped[ClassSubject] = relationship("ClassSubject", back_populates="components")
