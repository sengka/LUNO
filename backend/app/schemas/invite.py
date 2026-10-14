"""Davet bağlantısı şemaları (US-010, sözleşme 5.8 / 5.9)."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_serializer


def to_utc_z(dt: datetime) -> str:
    """Sözleşme 1.1: tarih-saat ISO 8601, UTC (ör. 2026-10-05T09:30:00Z)."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class InviteCreateResponse(BaseModel):
    """POST /projects/{project_id}/invites · 201"""
    invite_url: str
    expires_at: datetime

    @field_serializer("expires_at")
    def serialize_expires_at(self, dt: datetime, _info):
        return to_utc_z(dt)


class InviteUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    avatar_url: Optional[str] = None


class InviteProjectResponse(BaseModel):
    """POST /invites/{token}/accept · 200 — sözleşme 2. bölümdeki Project nesnesi."""
    id: int
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    progress_percent: float = 0.0
    member_count: int = 0
    created_by: Optional[InviteUserSummary] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_datetimes(self, dt: datetime, _info):
        return to_utc_z(dt)
