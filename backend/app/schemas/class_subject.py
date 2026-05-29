from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Literal


SubjectCategoryT = Literal["academic", "co_curricular", "grading"]


# ── Exam component schemas (children of a class_subject) ───────────
class ExamComponentBase(BaseModel):
    component_name: str = Field(min_length=1, max_length=80)
    max_marks: int = Field(default=0, ge=0, le=1000)
    order_index: int = Field(default=0, ge=0)


class ExamComponentCreate(ExamComponentBase):
    pass


class ExamComponentUpdate(BaseModel):
    component_name: str | None = Field(default=None, min_length=1, max_length=80)
    max_marks: int | None = Field(default=None, ge=0, le=1000)
    order_index: int | None = Field(default=None, ge=0)


class ExamComponentOut(ExamComponentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    class_subject_id: int
    created_at: datetime
    updated_at: datetime


# ── Class-subject (parent) schemas ─────────────────────────────────
class ClassSubjectBase(BaseModel):
    class_name: str = Field(min_length=1, max_length=20)
    subject_name: str = Field(min_length=1, max_length=60)
    subject_name_pa: str | None = Field(default=None, max_length=60)
    category: SubjectCategoryT = "academic"
    order_index: int = Field(default=0, ge=0)


class ClassSubjectCreate(ClassSubjectBase):
    pass


class ClassSubjectUpdate(BaseModel):
    subject_name: str | None = Field(default=None, min_length=1, max_length=60)
    subject_name_pa: str | None = Field(default=None, max_length=60)
    category: SubjectCategoryT | None = None
    order_index: int | None = Field(default=None, ge=0)


class ClassSubjectOut(ClassSubjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class ClassSubjectDetailOut(ClassSubjectOut):
    components: list[ExamComponentOut] = []


class ComponentsReplaceBody(BaseModel):
    """Used by the detail page's bulk-save button to replace all components
    for a subject in a single transaction. Simpler than per-row PATCH for
    the spreadsheet-style editor."""
    components: list[ExamComponentCreate]
