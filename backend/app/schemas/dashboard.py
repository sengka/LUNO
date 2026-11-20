
from pydantic import BaseModel

from app.schemas.task import TaskResponse


class DashboardProject(BaseModel):
    """Dashboard'daki proje kartı (sözleşme 10.1)."""

    id: int
    name: str
    progress_percent: float = 0.0
    my_open_tasks: int = 0


class DashboardResponse(BaseModel):
    """GET /dashboard yanıtı (US-022, FR-060, sözleşme 10.1)."""

    projects: list[DashboardProject]
    my_task_counts: dict[str, int]
    upcoming_tasks: list[TaskResponse]
    unread_notification_count: int = 0
