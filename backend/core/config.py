"""Application configuration using Pydantic settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # API Settings
    api_title: str = "Antika Auction Watcher API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"

    # Database
    database_url: str

    # Redis
    redis_url: str

    # JWT Authentication
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 24  # 24 hours

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Instagram (optional for Phase 1)
    instagram_username: str | None = None
    instagram_password: str | None = None

    # Frontend
    next_public_api_url: str = "http://localhost:8000"

    # Encryption key for credentials (32 bytes base64 encoded)
    encryption_key: str | None = None


settings = Settings()
