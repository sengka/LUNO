from datetime import date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models.task import TaskStatus, TaskPriority

class CalendarEventResponse(BaseModel):
    id: int
    title: str
    event_type: str  # "PROJECT" or "TASK"
    start_date: Optional[date]
    end_date: Optional[date]
    status: str
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    assigned_to_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class GanttTaskItem(BaseModel):
    id: int
    title: str
    start_date: Optional[date]
    due_date: Optional[date]
    status: TaskStatus
    priority: TaskPriority
    assigned_to_id: Optional[int] = None
    progress_percent: float  # 0.0 for TODO, 50.0 for IN_PROGRESS, 100.0 for DONE

    model_config = ConfigDict(from_attributes=True)

class GanttProjectItem(BaseModel):
    project_id: int
    project_name: str
    status: str
    start_date: Optional[date]
    end_date: Optional[date]
    tasks: List[GanttTaskItem] = []

    model_config = ConfigDict(from_attributes=True)

class GanttTimelineResponse(BaseModel):
    projects: List[GanttProjectItem]
