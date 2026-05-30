from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: str = "development"

    # Database (required)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dogdiet"

    # Security (required in production)
    secret_key: str = "dev-secret-key-change-in-production"

    # Cloudflare R2 storage
    cloudflare_r2_account_id: str = ""
    cloudflare_r2_access_key_id: str = ""
    cloudflare_r2_secret_access_key: str = ""
    cloudflare_r2_bucket_name: str = "dog-breed-diet-planner"
    cloudflare_r2_endpoint_url: str = ""
    cloudflare_r2_public_url: str = ""

    # CORS — comma-separated list
    allowed_origins: str = "http://localhost:3000"

    # Rate limiting
    rate_limit_per_minute: int = 60
    analyze_rate_limit_per_minute: int = 10

    # File upload
    max_upload_size_mb: int = 10

    # ---------------------------------------------------------------------------
    # AI Providers — backend only, never exposed to frontend
    # ---------------------------------------------------------------------------
    # Google Gemini (free tier: 15 RPM, 1M tokens/day on gemini-1.5-flash)
    gemini_api_key: str = ""

    # Active provider for this deployment profile (Gemini only)
    ai_active_provider: str = "gemini"
    ai_enabled: str = "true"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


settings = Settings()
