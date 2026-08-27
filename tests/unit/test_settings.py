import pytest
from pydantic import ValidationError

from crossborder_api.config import Settings


def test_development_can_start_without_external_credentials() -> None:
    settings = Settings(app_env="development", _env_file=None)
    assert settings.llm_api_key is None
    assert settings.parsed_cors_origins == ["http://localhost:3006"]


def test_production_rejects_missing_application_secret() -> None:
    with pytest.raises(ValidationError, match="APP_SECRET_KEY"):
        Settings(app_env="production", app_secret_key=None, _env_file=None)


def test_production_accepts_strong_application_secret() -> None:
    settings = Settings(
        app_env="production",
        app_secret_key="x" * 32,
        _env_file=None,
    )
    assert settings.app_env == "production"
