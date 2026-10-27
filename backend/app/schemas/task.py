from datetime import date, datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, field_serializer, field_validator, ConfigDict

from app.models.enums import STORY_POINT_VALUES, Priority

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


class TaskAssigneeUpdateRequest(BaseModel):
    """PATCH /tasks/{id}/assignee istek gövdesi (US-012 / 6.6)."""
    assignee_id: Optional[int] = Field(None, description="Atanan kullanıcının id'si")
    confirm_over_capacity: bool = False


class TaskCreateRequest(BaseModel):
    """Sözleşme 6.2 (görev oluştur) ve 6.10 (alt görev ekle) istek gövdesi.

    Alt görevde `parent_id` ve proje, ana görevden otomatik alınır.
    """
    title: str = Field(..., min_length=2, max_length=200, description="Görev başlığı (2-200 karakter)")
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    priority: Optional[Priority] = None
    story_points: Optional[int] = Field(None, description="Yalnızca 1, 2, 3, 5, 8, 13 (FR-036)")
    label_ids: List[int] = []
    sprint_id: Optional[int] = None
    # Kapasite kontrolü (sözleşme 6.6, FR-073) eklendiğinde kullanılacak.
    confirm_over_capacity: bool = False

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Görev başlığı zorunludur.")
        return value

    @field_validator("story_points")
    @classmethod
    def check_story_points(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value not in STORY_POINT_VALUES:
            raise ValueError("Efor puanı 1, 2, 3, 5, 8 veya 13 olmalıdır.")
        return value


class TaskUpdateRequest(BaseModel):
    """PATCH /tasks/{id} istek gövdesi (US-013, US-032 / 6.4)."""
    title: Optional[str] = Field(None, min_length=2, max_length=200, description="Görev başlığı (2-200 karakter)")
    description: Optional[str] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    priority: Optional[Priority] = None
    story_points: Optional[int] = Field(None, description="Yalnızca 1, 2, 3, 5, 8, 13 (FR-036)")
    label_ids: Optional[List[int]] = None
    sprint_id: Optional[int] = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            raise ValueError("Görev başlığı zorunludur.")
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Görev başlığı zorunludur.")
        return value

    @field_validator("story_points")
    @classmethod
    def check_story_points(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value not in STORY_POINT_VALUES:
            raise ValueError("Efor puanı 1, 2, 3, 5, 8 veya 13 olmalıdır.")
        return value


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


class TaskListResponse(BaseModel):
    """Sözleşme 1.6 & 6.1: Sayfalı görev listesi yanıtı."""
    items: List[TaskResponse]
    total: int
    page: int
    limit: int


class BoardColumn(BaseModel):
    """Sözleşme 7.1: Kanban sütunu."""
    status: str
    tasks: List[TaskResponse]


class BoardResponse(BaseModel):
    """Sözleşme 7.1: Kanban panosu yanıtı."""
    columns: List[BoardColumn]


class CalendarEvent(BaseModel):
    """Sözleşme 7.2: Takvim etkinliği."""
    task_id: int
    title: str
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    status: str
    assignee: Optional[UserSummary] = None


class CalendarResponse(BaseModel):
    """Sözleşme 7.2: Takvim yanıtı."""
    events: List[CalendarEvent]


class GanttProjectSummary(BaseModel):
    """Sözleşme 7.3: Gantt proje tarihleri."""
    start_date: date
    end_date: date


class GanttItem(BaseModel):
    """Sözleşme 7.3: Gantt görev öğesi."""
    task_id: int
    title: str
    start_date: date
    due_date: date
    progress_percent: float
    status: str
    parent_id: Optional[int] = None
    depends_on: List[int] = Field(default_factory=list)


class GanttResponse(BaseModel):
    """Sözleşme 7.3: Gantt şeması yanıtı."""
    project: GanttProjectSummary
    items: List[GanttItem]
