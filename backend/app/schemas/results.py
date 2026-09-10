"""Response models for the aggregated results endpoint (GET /marks/results).

These mirror the dataclasses in app/services/results.py but add the student
name/roll (joined in the router) so the frontend renders the table from a
single call.
"""
from pydantic import BaseModel
from typing import Literal


class SubjectColumnOut(BaseModel):
    subject_name: str
    subject_name_pa: str | None = None
    category: str
    order_index: int
    max: float


class SubjectResultOut(BaseModel):
    subject_name: str
    category: str
    obtained: float
    max: float
    percentage: float | None = None
    grade: str | None = None
    status: Literal["complete", "partial", "missing"]


class StudentResultOut(BaseModel):
    student_id: int
    name: str
    roll_no: str | None = None
    subjects: list[SubjectResultOut]
    total_obtained: float
    total_max: float
    percentage: float | None = None
    grade: str | None = None


class ClassResultsOut(BaseModel):
    class_name: str
    session: str
    scope: Literal["term1", "term2", "annual"]
    subject_columns: list[SubjectColumnOut]
    students: list[StudentResultOut]
