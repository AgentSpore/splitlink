from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file.

    All configurable values are defined here with sensible defaults.
    Override any setting via environment variable or .env file.
    """

    db_path: str = "./splitlink.db"
    cors_origins: list[str] = ["*"]
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded and validated once)."""
    return Settings()
