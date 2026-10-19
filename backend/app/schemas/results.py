"""Response models for the aggregated results endpoint (GET /marks/results).

These mirror the dataclasses in app/services/results.py and add the student
name, roll number and attendance (joined in the router), so a client renders
the whole table from one call. Every v2 field is additive: older clients that
read only the original fields keep working.
"""
from typing import Literal

from pydantic import BaseModel, Field


class ComponentInfoOut(BaseModel):
    component_name: str
    group: str
    term: int | None = None
    max: float


class SubjectColumnOut(BaseModel):
    subject_name: str
    subject_name_pa: str | None = None
    category: str
    order_index: int
    max: float
    is_grading: bool = False
    batch_status: Literal["submitted", "draft", "none"] = "none"
    components: list[ComponentInfoOut] = Field(default_factory=list)
    # Taken only by the students enrolled on Class Subjects; for the others
    # their result for it has status "not_taken".
    is_optional: bool = False


class GroupColumnOut(BaseModel):
    key: str
    term: int | None = None
    order_index: int


class ComponentMarkOut(BaseModel):
    component_name: str
    group: str
    term: int | None = None
    max: float
    marks: float | None = None
    grade_letter: str | None = None
    batch_status: Literal["submitted", "draft"] | None = None
    counted: bool = False


class CellOut(BaseModel):
    key: str
    obtained: float
    max: float
    marked: int
    total: int
    status: Literal["complete", "partial", "missing", "none"]


class SubjectResultOut(BaseModel):
    subject_name: str
    category: str
    obtained: float
    max: float
    percentage: float | None = None
    grade: str | None = None
    # "not_taken": an optional subject this student doesn't take. It carries
    # nothing (obtained 0, max 0, percentage / grade null, no components) and
    # is left out of the student's totals, grade and completeness.
    status: Literal["complete", "partial", "missing", "not_taken"]
    is_grading: bool = False
    is_optional: bool = False
    grade_letter: str | None = None
    term_letters: dict[int, str] = Field(default_factory=dict)
    batch_status: Literal["submitted", "draft", "none"] = "none"
    components_total: int = 0
    components_marked: int = 0
    components: list[ComponentMarkOut] = Field(default_factory=list)
    cells: list[CellOut] = Field(default_factory=list)


class AttendanceOut(BaseModel):
    working_days: int
    days_present: float
    pct: float | None = None
    counts: dict[str, int] = Field(default_factory=dict)


class StudentResultOut(BaseModel):
    student_id: int
    name: str
    roll_no: str | None = None
    status: str = "active"
    subjects: list[SubjectResultOut]
    total_obtained: float
    total_max: float
    percentage: float | None = None
    grade: str | None = None
    has_marks: bool = False
    rank: int | None = None
    pass_status: Literal["pass", "fail", "incomplete"] | None = None
    failed_subjects: list[str] = Field(default_factory=list)
    promotion: str | None = None
    draft_components: int = 0
    attendance: AttendanceOut | None = None


class SessionDatesOut(BaseModel):
    start: str
    end: str


class ClassResultsOut(BaseModel):
    class_name: str
    session: str
    scope: Literal["term1", "term2", "annual"]
    subject_columns: list[SubjectColumnOut]
    students: list[StudentResultOut]
    groups: list[GroupColumnOut] = Field(default_factory=list)
    class_size: int = 0
    ranked_count: int = 0
    include_drafts: bool = True
    has_drafts: bool = False
    complete: bool = False
    engine_version: int = 3
    session_dates: SessionDatesOut | None = None
    warnings: list[str] = Field(default_factory=list)
    # The pass rule pass_status / failed_subjects / promotion were worked out with:
    # the class template's promotionRule, else the school default.
    pass_pct: float = 33.0
    conditional_max_fails: int = 2
