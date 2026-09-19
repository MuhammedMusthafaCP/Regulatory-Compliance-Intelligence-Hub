from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    PROJECT_NAME: str = "Regulatory & Compliance Intelligence Hub"
    API_V1_PREFIX: str = "/api"
    FRONTEND_ORIGIN: str = "http://localhost:4001"

    # Connection pool guardrails (Aiven free tier caps at 20 max connections)
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
