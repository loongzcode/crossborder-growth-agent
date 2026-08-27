"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime configuration.

    Production rejects missing or weak application secrets. Development and
    tests may omit external services because the health endpoint and domain
    contracts must remain runnable without merchant credentials.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "CrossBorder Growth Agent API"
    app_version: str = "0.1.0"
    app_env: Literal["development", "test", "production"] = "development"
    app_log_level: str = "INFO"
    app_secret_key: SecretStr | None = None
    access_token_minutes: int = 480
    refresh_token_days: int = 7

    database_url: str = "postgresql+asyncpg://crossborder:crossborder@localhost:5432/crossborder"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3006"

    llm_api_key: SecretStr | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def signing_secret(self) -> str:
        if self.app_secret_key:
            return self.app_secret_key.get_secret_value()
        return "crossborder-development-signing-key-change-before-production"

    @model_validator(mode="after")
    def validate_production_secret(self) -> "Settings":
        if self.app_env != "production":
            return self
        secret = self.app_secret_key.get_secret_value() if self.app_secret_key else ""
        if len(secret) < 32:
            raise ValueError("生产环境 APP_SECRET_KEY 必须至少为 32 个字符")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
