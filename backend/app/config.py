import os
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Meta Ads Audit API"
    environment: str = "development"
    debug: bool = False
    database_url: str = "postgresql://postgres:postgres@postgres:5432/meta_ads_audit"

    secret_key: str = "local-dev-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=5, le=1440)

    encryption_key: str = "X7v0bRrKp5Kz8mQ3Z9xY2wA1cD4eF6gH8iJ0kL2mN4o="

    redis_url: str = "redis://redis:6379/0"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    frontend_app_url: str = "http://localhost:3000"
    meta_app_id: str = "mock"
    meta_app_secret: str = ""
    meta_redirect_uri: str = "http://localhost:3000/dashboard/meta/callback"
    meta_api_version: str = "v19.0"
    meta_oauth_scopes: str = "ads_read,ads_management,business_management"
    meta_state_ttl_minutes: int = Field(default=10, ge=1, le=60)
    meta_initial_sync_lookback_days: int = Field(default=90, ge=7, le=365)
    meta_incremental_sync_lookback_days: int = Field(default=30, ge=1, le=90)
    meta_http_timeout_seconds: int = Field(default=60, ge=5, le=180)
    meta_pagination_max_pages: int = Field(default=250, ge=1, le=2000)

    ai_provider: str = "mock"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_openai_base_url: str = "https://api.openai.com/v1"
    ai_anthropic_base_url: str = "https://api.anthropic.com/v1"
    ai_timeout_seconds: int = Field(default=45, ge=5, le=180)
    ai_max_retries: int = Field(default=2, ge=0, le=5)
    ai_prompt_version: str = "v1"

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@example.com"

    free_max_ad_accounts: int = 1
    free_max_findings: int = 3
    free_max_recommendations: int = 2
    free_max_history_items: int = 4
    free_max_trend_points: int = 6
    free_max_reports_per_month: int = 3

    model_config = {"env_file": ".env", "extra": "ignore"}

    @field_validator("debug", mode="before")
    @classmethod
    def disable_debug_in_production(cls, value: bool) -> bool:
        if os.getenv("ENVIRONMENT", "development").lower() == "production" and value:
            return False
        return bool(value)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def validate_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            if value.startswith("["):
                import json
                return json.loads(value)
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache()
def get_settings() -> Settings:
    return Settings()
