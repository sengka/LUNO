from datetime import date, datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, field_serializer, ConfigDict

from app.schemas.project import UserSummary


class TaskStatusUpdateEnum(str, Enum):
    """Sözleşme 6.5: İstek gövdesinde kabul edilen görev durumları."""
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW_TESTING = "REVIEW_TESTING"
    DONE = "DONE"


class TaskStatusUpdateRequest(BaseModel):
    """PATCH /tasks/{id}/status istek gövdesi."""
    status: TaskStatusUpdateEnum = Field(
        ...,
        description="Yeni görev durumu (TODO, IN_PROGRESS, REVIEW_TESTING, DONE)"
    )


class TaskLabel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str


class TaskResponse(BaseModel):
    """Sözleşme 2. bölüm: Task nesnesi."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    parent_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    story_points: Optional[int] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    assignee: Optional[UserSummary] = None
    created_by: Optional[UserSummary] = None
    sprint_id: Optional[int] = None
    labels: List[TaskLabel] = []
    subtask_count: int = 0
    subtask_done_count: int = 0
    depends_on: List[int] = []
    risk_level: Optional[str] = None
    comment_count: int = 0
    file_count: int = 0
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime, _info):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    @field_serializer("updated_at")
    def serialize_updated_at(self, dt: datetime, _info):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
