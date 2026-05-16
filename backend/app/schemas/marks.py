from pydantic import BaseModel, ConfigDict
from datetime import datetime


class MarkItem(BaseModel):
    student_id: int
    marks: int


class MarksBulkCreate(BaseModel):
    class_name: str
    exam_type: str
    subject: str
    max_marks: int = 100
    session: str
    items: list[MarkItem]


class MarkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    class_name: str
    exam_type: str
    subject: str
    marks: int
    max_marks: int
    session: str
    created_at: datetime
