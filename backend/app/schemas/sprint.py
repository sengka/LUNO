from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SprintCreate(BaseModel):
    """Sprint oluşturma isteği (US-040, FR-066; sözleşme 11.1)."""

    name: str = Field(..., min_length=1, max_length=100)
    goal: Optional[str] = Field(default=None, max_length=2000)
    start_date: date
    end_date: date
    capacity_points: Optional[int] = Field(default=None, gt=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Sprint adı boş olamaz.")
        return stripped


class SprintUpdate(BaseModel):
    """Sprint güncelleme isteği (US-040, US-025; sözleşme 11.2)."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    goal: Optional[str] = Field(default=None, max_length=2000)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    capacity_points: Optional[int] = Field(default=None, gt=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            raise ValueError("Sprint adı boş olamaz.")
        return stripped


class SprintTasksAddRequest(BaseModel):
    """Görevleri sprinte ekleme isteği (US-040, FR-067; sözleşme 11.3)."""

    task_ids: list[int] = Field(..., min_length=1)


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


class SprintTasksAddResponse(SprintResponse):
    """Sprinte görev ekleme yanıtı (sözleşme 11.3)."""

    capacity_warning: bool = False
