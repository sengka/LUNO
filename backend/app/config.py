import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "LUNO"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "luno-super-secret-jwt-key-sprint2-2026-production-ready")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 86400  # 24 hours (NFR-003)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./luno.db")

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

settings = Settings()
