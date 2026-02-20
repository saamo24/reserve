"""Application configuration via environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-based configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        alias="APP_ENV",
    )
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # JWT
    jwt_secret_key: str = Field(default="", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, ge=1, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, ge=1, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    # Server
    workers: int = Field(default=4, ge=1, alias="WORKERS")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/reserve",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=10, ge=1, le=100, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, ge=0, alias="DB_MAX_OVERFLOW")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_pool_size: int = Field(default=10, ge=1, alias="REDIS_POOL_SIZE")

    # Cache TTL (seconds)
    cache_slots_ttl: int = Field(default=90, ge=1, alias="CACHE_SLOTS_TTL")
    cache_tables_ttl: int = Field(default=120, ge=1, alias="CACHE_TABLES_TTL")

    # Lock TTL (seconds)
    lock_ttl_seconds: int = Field(default=10, ge=1, alias="LOCK_TTL_SECONDS")

    # Admin
    admin_email: str = Field(default="admin@example.com", alias="ADMIN_EMAIL")
    admin_temp_password: str = Field(default="admin123", alias="ADMIN_TEMP_PASSWORD")


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
