import os
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    from src.config import settings as settings_module
    from src.llm import factory as factory_module
    from src.observability import langfuse as langfuse_module
    from src.storage import postgres as postgres_module

    settings_module._settings = None
    factory_module._factory = None
    langfuse_module._langfuse_client = None
    postgres_module._postgres_connection = None

    original_env = os.environ.copy()
    env_vars_to_clear = [
        k
        for k in os.environ
        if k.startswith(
            (
                "OPENAI_",
                "ANTHROPIC_",
                "GOOGLE_",
                "AZURE_",
                "GROQ_",
                "LANGFUSE_",
                "DATABASE_",
                "DEFAULT_",
                "SUMMARIZATION_",
                "TELEGRAM_",
                "APP_",
                "DATA_PATH",
            )
        )
    ]
    for key in env_vars_to_clear:
        del os.environ[key]
    yield
    os.environ.clear()
    os.environ.update(original_env)
    settings_module._settings = None
    factory_module._factory = None
    langfuse_module._langfuse_client = None
    postgres_module._postgres_connection = None


@pytest.fixture
def mock_env_with_openai(clean_env: None) -> dict[str, str]:
    env = {
        "OPENAI_API_KEY": "sk-test-key-12345",
        "DEFAULT_MODEL": "openai/gpt-4o",
        "SUMMARIZATION_MODEL": "openai/gpt-4o-mini",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test",
    }
    with patch.dict(os.environ, env, clear=False):
        yield env


@pytest.fixture
def mock_env_with_anthropic(clean_env: None) -> dict[str, str]:
    env = {
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
        "DEFAULT_MODEL": "anthropic/claude-3-5-sonnet-20241022",
        "SUMMARIZATION_MODEL": "anthropic/claude-3-5-haiku-20241022",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test",
    }
    with patch.dict(os.environ, env, clear=False):
        yield env


@pytest.fixture
def mock_env_with_multiple_providers(clean_env: None) -> dict[str, str]:
    env = {
        "OPENAI_API_KEY": "sk-openai-key",
        "ANTHROPIC_API_KEY": "sk-ant-key",
        "GOOGLE_API_KEY": "google-key",
        "GROQ_API_KEY": "gsk-groq-key",
        "DEFAULT_MODEL": "openai/gpt-4o",
        "SUMMARIZATION_MODEL": "groq/llama-3.3-70b-versatile",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test",
    }
    with patch.dict(os.environ, env, clear=False):
        yield env


@pytest.fixture
def mock_env_with_langfuse(clean_env: None) -> dict[str, str]:
    env = {
        "OPENAI_API_KEY": "sk-test-key",
        "LANGFUSE_PUBLIC_KEY": "pk-test",
        "LANGFUSE_SECRET_KEY": "sk-test",
        "LANGFUSE_HOST": "https://cloud.langfuse.com",
        "LANGFUSE_ENABLED": "true",
        "DEFAULT_MODEL": "openai/gpt-4o",
        "SUMMARIZATION_MODEL": "openai/gpt-4o-mini",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test",
    }
    with patch.dict(os.environ, env, clear=False):
        yield env


@pytest.fixture
def temp_data_path(tmp_path: Path) -> Path:
    data_path = tmp_path / "data"
    data_path.mkdir(parents=True, exist_ok=True)
    return data_path


@pytest.fixture
def temp_user_path(temp_data_path: Path) -> Path:
    user_path = temp_data_path / "users" / "test-user-123"
    user_path.mkdir(parents=True, exist_ok=True)
    return user_path
