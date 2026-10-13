from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, field_serializer, ConfigDict

class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    avatar_url: Optional[str] = None

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Proje adı (2-100 karakter)")
    description: Optional[str] = Field(None, max_length=2000, description="Proje açıklaması (en fazla 2000 karakter)")
    start_date: date = Field(..., description="Başlangıç tarihi (YYYY-MM-DD)")
    end_date: date = Field(..., description="Bitiş tarihi (YYYY-MM-DD)")

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Proje adı (2-100 karakter)")
    description: Optional[str] = Field(None, max_length=2000, description="Proje açıklaması (en fazla 2000 karakter)")
    start_date: Optional[date] = Field(None, description="Başlangıç tarihi (YYYY-MM-DD)")
    end_date: Optional[date] = Field(None, description="Bitiş tarihi (YYYY-MM-DD)")

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    progress_percent: float = 0.0
    member_count: int = 0
    created_by: Optional[UserSummary] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime, _info):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    @field_serializer("updated_at")
    def serialize_updated_at(self, dt: datetime, _info):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int
    page: int
    limit: int

class ProjectMemberAddRequest(BaseModel):
    email: EmailStr = Field(..., description="Kullanıcı e-posta adresi")
    technical_role: Optional[str] = Field(None, max_length=100, description="Teknik rol (ör. Backend Geliştirici)")

class ProjectMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserSummary
    email: EmailStr
    system_role: str
    technical_role: Optional[str] = None
    capacity_points: Optional[int] = None
    joined_at: datetime

    @field_serializer("joined_at")
    def serialize_joined_at(self, dt: datetime, _info):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
