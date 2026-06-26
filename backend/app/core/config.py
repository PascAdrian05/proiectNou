from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    app_name: str = "Security Monitoring API"
    environment: str = "development"

    database_url: str = "postgresql+psycopg2://postgres:postgres@db:5432/security_monitor"
    redis_url: str = "redis://redis:6379/0"

    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14

    frontend_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000"

    auth_max_failed_attempts: int = 5
    auth_lockout_minutes: int = 15
    auth_fail_window_seconds: int = 900

    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None

    facebook_client_id: str | None = None
    facebook_client_secret: str | None = None
    facebook_redirect_uri: str | None = None

    stripe_api_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_basic_id: str | None = None
    stripe_price_pro_id: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None

    groq_api_key: str | None = None

    rate_limit_per_minute: int = 60
    rate_limit_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra='ignore')

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v in ("change-me-in-production", "changeme", "secret", "supersecretkeyfordevelopmentonly", ""):
            raise ValueError(
                "SECRET_KEY is set to an insecure default. "
                "Generate a strong random key and set it in .env"
            )
        return v


settings = Settings()


def get_cors_origins() -> list[str]:
    return [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
