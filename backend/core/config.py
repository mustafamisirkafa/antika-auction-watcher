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

    # Phase 2: Marketplace API Credentials
    ebay_app_id: str | None = None
    ebay_cert_id: str | None = None
    ebay_dev_id: str | None = None
    ebay_oauth_token: str | None = None
    
    etsy_api_key: str | None = None
    
    # Phase 10.5: AutoBid Anti-Sniping
    anti_sniping_enabled: bool = True
    sniping_window_sec: int = 7  # Last-X seconds window
    escalation_cooldown_ms: int = 600  # Min delay between escalations
    max_escalations_per_item: int = 5
    sniping_step_multiplier: float = 2.0  # Multiply step in snipe window
    microbuffer_sec: float = 1.0  # Hold bid if new price seen within 1s
    etsy_secret_key: str | None = None
    etsy_oauth_token: str | None = None
    
    # Phase 2: Admin & Rate Limiting
    admin_secret_key: str | None = None
    rate_limit_enabled: bool = True
    cache_ttl_seconds: int = 3600


settings = Settings()
