import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "LUNO Proje & Görev Yönetimi API"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./luno.db"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
