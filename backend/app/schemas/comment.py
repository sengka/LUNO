from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_serializer, field_validator
from app.schemas.project import UserSummary


class CommentCreateRequest(BaseModel):
    """Sözleşme 8.5 & 8.6: Yorum oluşturma istek gövdesi."""
    body: str = Field(..., min_length=1, max_length=2000, description="Yorum içeriği (1-2000 karakter)")

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("Yorum metni boş olamaz.")
        if len(v) > 2000:
            raise ValueError("Yorum en fazla 2000 karakter olabilir.")
        return v_stripped


class CommentResponse(BaseModel):
    """Sözleşme 2. bölüm: Comment nesnesi."""
    id: int
    body: str
    author: UserSummary
    task_id: Optional[int] = None
    file_id: Optional[int] = None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime, _info):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    model_config = {"from_attributes": True}


class CommentListResponse(BaseModel):
    """Sözleşme 1.6 & 8.5: Sayfalı yorum listesi yanıtı."""
    items: List[CommentResponse]
    total: int
    page: int
    limit: int
