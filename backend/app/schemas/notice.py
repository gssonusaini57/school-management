from pydantic import BaseModel, ConfigDict
from datetime import datetime


class NoticeCreate(BaseModel):
    title: str
    content: str
    priority: str = "normal"
    audience: str = "all"


class NoticeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    content: str
    priority: str
    audience: str
    posted_by: str
    created_at: datetime
