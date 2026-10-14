import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "LUNO"
    API_V1_STR: str = "/api/v1"
    # Varsayılan değer yok: .env veya ortam değişkeninde tanımlı değilse uygulama başlamaz.
    SECRET_KEY: str = Field(min_length=1)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 86400  # 24 hours (NFR-003)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./luno.db")
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

settings = Settings()
