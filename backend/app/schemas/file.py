"""Dosya şemaları (sözleşme 2. bölüm File nesnesi, 8.1 – 8.4)."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_serializer

from app.schemas.project import UserSummary


class FileResponse(BaseModel):
    """Sözleşme 2. bölüm: File nesnesi."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    size_bytes: int
    mime_type: str
    project_id: int
    task_id: Optional[int] = None
    uploaded_by: Optional[UserSummary] = None
    comment_count: int = 0
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime, _info):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class FileListResponse(BaseModel):
    """Sözleşme 8.2: sayfalı File listesi."""

    items: List[FileResponse]
    total: int
    page: int
    limit: int
