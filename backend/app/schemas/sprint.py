from datetime import date

from pydantic import BaseModel


class SprintResponse(BaseModel):
    """Sözleşme 2. bölüm: Sprint nesnesi (11.1 – 11.3)."""

    id: int
    project_id: int
    name: str
    goal: str | None = None
    start_date: date
    end_date: date
    capacity_points: int | None = None
    total_points: int = 0
    done_points: int = 0
    progress_percent: float = 0.0
    is_active: bool = False
