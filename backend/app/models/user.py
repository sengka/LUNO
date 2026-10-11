from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base

class SystemRole(str, enum.Enum):
    YONETICI = "YONETICI"
    EKIP_UYESI = "EKIP_UYESI"

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default=SystemRole.EKIP_UYESI.value, nullable=False)
    avatar_url = Column(String(500), nullable=True, default=None)
    theme = Column(String(20), default="LIGHT", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
