from datetime import date
from typing import List, Optional, Dict
from pydantic import BaseModel

class ProjectProgressReport(BaseModel):
    project_id: int
    project_name: str
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    todo_tasks: int
    progress_percentage: float

class UserTaskSummaryReport(BaseModel):
    user_id: int
    total_assigned: int
    completed_tasks: int
    in_progress_tasks: int
    todo_tasks: int
    completion_rate_percentage: float

class PeriodStatPoint(BaseModel):
    label: str  # e.g. "2026-10-01" or "2026-W40" or "2026-10"
    created_tasks: int
    completed_tasks: int

class PeriodicStatsReport(BaseModel):
    timeframe: str  # "daily", "weekly", "monthly"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_created: int
    total_completed: int
    data_points: List[PeriodStatPoint]
