from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, field_serializer, ConfigDict

class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, description="Kullanıcı ad soyad (2-100 karakter)")
    email: EmailStr = Field(..., description="Geçerli e-posta adresi")
    password: str = Field(..., min_length=8, description="En az 8 karakterli şifre")

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Kayıtlı e-posta adresi")
    password: str = Field(..., description="Kullanıcı şifresi")

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    role: str
    avatar_url: Optional[str] = None
    theme: str = "LIGHT"
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400
    user: UserResponse

class ErrorDetail(BaseModel):
    code: str
    message: str
    fields: Optional[Dict[str, Any]] = None
    details: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
