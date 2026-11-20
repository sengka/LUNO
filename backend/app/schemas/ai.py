"""Yapay zekâ (LLM) öneri şemaları (sözleşme 13)."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

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
