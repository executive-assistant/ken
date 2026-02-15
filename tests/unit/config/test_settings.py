from __future__ import annotations

from pathlib import Path

import pytest

from src.config.settings import (
    AppSettings,
    LLMSettings,
    Settings,
    get_settings,
    parse_model_string,
)


class TestParseModelString:
    def test_parse_valid_model_string(self) -> None:
        provider, model = parse_model_string("openai/gpt-4o")
        assert provider == "openai"
        assert model == "gpt-4o"

    def test_parse_anthropic_model(self) -> None:
        provider, model = parse_model_string("anthropic/claude-3-5-sonnet-20241022")
        assert provider == "anthropic"
        assert model == "claude-3-5-sonnet-20241022"

    def test_parse_google_model(self) -> None:
        provider, model = parse_model_string("google/gemini-2.0-flash")
        assert provider == "google"
        assert model == "gemini-2.0-flash"

    def test_parse_model_with_slashes_in_name(self) -> None:
        provider, model = parse_model_string("azure/gpt-4o-2024-05-13")
        assert provider == "azure"
        assert model == "gpt-4o-2024-05-13"

    def test_parse_invalid_model_string_no_slash(self) -> None:
        with pytest.raises(ValueError, match="Invalid model format"):
            parse_model_string("gpt-4o")

    def test_parse_empty_string(self) -> None:
        with pytest.raises(ValueError, match="Invalid model format"):
            parse_model_string("")


class TestLLMSettings:
    def test_default_model_config(self, mock_env_with_openai: None) -> None:
        settings = LLMSettings()
        assert settings.default_model == "openai/gpt-4o"
        assert settings.summarization_model == "openai/gpt-4o-mini"

    def test_model_config_with_different_providers(
        self, mock_env_with_multiple_providers: None
    ) -> None:
        settings = LLMSettings()
        assert settings.default_model == "openai/gpt-4o"
        assert settings.summarization_model == "groq/llama-3.3-70b-versatile"

    def test_openai_api_key(self, mock_env_with_openai: None) -> None:
        settings = LLMSettings()
        assert settings.openai_api_key == "sk-test-key-12345"

    def test_anthropic_api_key(self, mock_env_with_anthropic: None) -> None:
        settings = LLMSettings()
        assert settings.anthropic_api_key == "sk-ant-test-key"

    def test_google_api_key(self, mock_env_with_multiple_providers: None) -> None:
        settings = LLMSettings()
        assert settings.google_api_key == "google-key"

    def test_groq_api_key(self, mock_env_with_multiple_providers: None) -> None:
        settings = LLMSettings()
        assert settings.groq_api_key == "gsk-groq-key"

    def test_missing_api_key_is_none(self, clean_env: None) -> None:
        settings = LLMSettings()
        assert settings.openai_api_key is None
        assert settings.anthropic_api_key is None


class TestAppSettings:
    def test_default_app_settings(self, clean_env: None) -> None:
        settings = AppSettings()
        assert settings.env == "development"
        assert settings.debug is True

    def test_production_settings(self, clean_env: None) -> None:
        import os

        os.environ["APP_ENV"] = "production"
        os.environ["APP_DEBUG"] = "false"
        settings = AppSettings()
        assert settings.env == "production"
        assert settings.debug is False


class TestSettings:
    def test_settings_initialization(self, mock_env_with_openai: None) -> None:
        settings = Settings()
        assert settings.llm is not None
        assert settings.app is not None
        assert settings.database_url is not None

    def test_settings_database_url(self, mock_env_with_openai: None) -> None:
        settings = Settings()
        assert "postgresql" in settings.database_url

    def test_settings_langfuse_disabled_by_default(self, mock_env_with_openai: None) -> None:
        settings = Settings()
        assert settings.langfuse_enabled is False

    def test_settings_langfuse_enabled(self, mock_env_with_langfuse: None) -> None:
        settings = Settings()
        assert settings.langfuse_enabled is True
        assert settings.langfuse_public_key == "pk-test"
        assert settings.langfuse_secret_key == "sk-test"

    def test_settings_data_path(self, mock_env_with_openai: None) -> None:
        settings = Settings()
        assert settings.data_path == Path("/data")


class TestGetSettings:
    def test_get_settings_returns_singleton(self, mock_env_with_openai: None) -> None:
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_get_settings_caches_settings(self, mock_env_with_openai: None) -> None:
        from src.config import settings as settings_module

        settings_module._settings = None
        settings = get_settings()
        assert settings is not None
        settings_module._settings = None
