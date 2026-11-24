"""Yapay zekâ (LLM) öneri şemaları (sözleşme 13)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import STORY_POINT_VALUES

LLMProviderName = Literal["groq", "gemini"]


class StoryPointsSuggestion(BaseModel):
    """Modelden beklenen JSON (13.4). LLMService yanıtı bu şemayla doğrular.

    Model 1, 2, 3, 5, 8, 13 dışında bir puan döndürürse doğrulama başarısız olur ve
    servis yedek modele geçer; ikisi de uymazsa 503 LLM_UNAVAILABLE döner. Böylece
    uç nokta sözleşme dışı bir puanı hiçbir zaman döndürmez.
    """

    story_points: int
    reason: str = Field(..., min_length=1)

    @field_validator("story_points")
    @classmethod
    def must_be_story_point(cls, value: int) -> int:
        if value not in STORY_POINT_VALUES:
            raise ValueError("Efor puanı 1, 2, 3, 5, 8 veya 13 olmalıdır.")
        return value

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Gerekçe boş olamaz.")
        return value


class SuggestPointsResponse(StoryPointsSuggestion):
    """POST /ai/tasks/{task_id}/suggest-points yanıtı (13.4)."""

    provider: LLMProviderName


def _clean_items(items: list[str]) -> list[str]:
    return [item.strip() for item in items if item and item.strip()]


class WeeklySummaryLLMOutput(BaseModel):
    """Haftalık özet için modelden beklenen JSON (13.5)."""

    summary: str = Field(..., min_length=1)

    @field_validator("summary")
    @classmethod
    def strip_summary(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Özet boş olamaz.")
        return value


class WeeklySummaryResponse(BaseModel):
    """POST /ai/projects/{project_id}/weekly-summary yanıtı (13.5)."""

    model_config = ConfigDict(populate_by_name=True)

    provider: LLMProviderName
    from_date: date = Field(..., alias="from")
    to_date: date = Field(..., alias="to")
    summary: str


class CommentSummaryLLMOutput(WeeklySummaryLLMOutput):
    """Yorum zinciri özeti için modelden beklenen JSON (13.6). Listeler boş olabilir."""

    decisions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

    @field_validator("decisions", "open_questions")
    @classmethod
    def clean_items(cls, value: list[str]) -> list[str]:
        return _clean_items(value)


class CommentSummaryResponse(BaseModel):
    """POST /ai/tasks/{task_id}/summarize-comments yanıtı (13.6)."""

    provider: LLMProviderName
    decisions: list[str]
    open_questions: list[str]
    summary: str
