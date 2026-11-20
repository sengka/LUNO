from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_serializer


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    message: str
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    is_read: bool
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    page: int
    limit: int
    unread_count: int
