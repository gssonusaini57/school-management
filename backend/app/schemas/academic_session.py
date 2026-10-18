from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class AcademicSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    session: str
    starts_on: date
    ends_on: date
    term1_start: date
    term1_end: date
    term2_start: date
    term2_end: date
    is_current: bool
    updated_at: datetime | None = None
    updated_by: str = ""


class AcademicSessionCreate(BaseModel):
    """Dates left out default to Apr 1 - Mar 31 with terms split at Oct 1."""
    session: str = Field(min_length=7, max_length=16)
    starts_on: date | None = None
    ends_on: date | None = None
    term1_start: date | None = None
    term1_end: date | None = None
    term2_start: date | None = None
    term2_end: date | None = None
    is_current: bool = False


class AcademicSessionUpdate(BaseModel):
    """The session name is immutable: marks and templates reference it as text."""
    starts_on: date | None = None
    ends_on: date | None = None
    term1_start: date | None = None
    term1_end: date | None = None
    term2_start: date | None = None
    term2_end: date | None = None
    is_current: bool | None = None
