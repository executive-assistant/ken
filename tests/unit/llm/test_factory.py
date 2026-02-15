from unittest.mock import MagicMock

import pytest

from src.llm.errors import LLMProviderNotFoundError
from src.llm.factory import (
    LLMFactory,
    get_llm,
    get_summarization_llm,
    list_providers,
    register_provider,
)


class TestLLMFactory:
    def test_list_providers_returns_available_providers(self) -> None:
        providers = list_providers()
        assert isinstance(providers, list)
        assert "openai" in providers
        assert "anthropic" in providers
        assert "google" in providers

    def test_list_providers_includes_all_expected_providers(self) -> None:
        providers = list_providers()
        expected_providers = [
            "openai",
            "anthropic",
            "google",
            "azure",
            "groq",
            "ollama",
            "mistral",
            "cohere",
        ]
        for provider in expected_providers:
            assert provider in providers

    def test_get_llm_raises_for_unknown_provider(self) -> None:
        with pytest.raises(LLMProviderNotFoundError) as exc_info:
            get_llm(provider="unknown_provider", model="some-model")
        assert "unknown_provider" in str(exc_info.value)

    def test_register_provider_adds_new_provider(self) -> None:
        mock_provider_class = MagicMock
        register_provider("custom_provider", mock_provider_class)
        providers = list_providers()
        assert "custom_provider" in providers

    def test_get_llm_with_provider_and_model(self, mock_env_with_openai: dict[str, str]) -> None:
        llm = get_llm(provider="openai", model="gpt-4o")
        assert llm is not None

    def test_get_llm_with_model_string_only(self, mock_env_with_openai: dict[str, str]) -> None:
        llm = get_llm(model="openai/gpt-4o")
        assert llm is not None

    def test_get_llm_provider_takes_precedence(self, mock_env_with_openai: dict[str, str]) -> None:
        llm = get_llm(provider="openai", model="anthropic/gpt-4o")
        assert llm is not None

    def test_get_llm_with_custom_kwargs(self, mock_env_with_openai: dict[str, str]) -> None:
        llm = get_llm(
            provider="openai",
            model="gpt-4o",
            temperature=0.7,
            max_tokens=1000,
        )
        assert llm is not None

    def test_get_summarization_llm(self, mock_env_with_multiple_providers: dict[str, str]) -> None:
        llm = get_summarization_llm()
        assert llm is not None

    def test_get_summarization_llm_uses_settings(
        self, mock_env_with_openai: dict[str, str]
    ) -> None:
        llm = get_summarization_llm()
        assert llm is not None

    def test_factory_singleton_pattern(self) -> None:
        factory1 = LLMFactory()
        factory2 = LLMFactory()
        assert factory1 is factory2


class TestProviderDetection:
    def test_detect_openai_from_model_name(self) -> None:
        from src.llm.factory import detect_provider_from_model

        assert detect_provider_from_model("gpt-4o") == "openai"
        assert detect_provider_from_model("gpt-4-turbo") == "openai"
        assert detect_provider_from_model("gpt-3.5-turbo") == "openai"
        assert detect_provider_from_model("o1-preview") == "openai"
        assert detect_provider_from_model("o3-mini") == "openai"

    def test_detect_anthropic_from_model_name(self) -> None:
        from src.llm.factory import detect_provider_from_model

        assert detect_provider_from_model("claude-3-5-sonnet-20241022") == "anthropic"
        assert detect_provider_from_model("claude-3-opus-20240229") == "anthropic"
        assert detect_provider_from_model("claude-3-haiku-20240307") == "anthropic"

    def test_detect_google_from_model_name(self) -> None:
        from src.llm.factory import detect_provider_from_model

        assert detect_provider_from_model("gemini-2.0-flash") == "google"
        assert detect_provider_from_model("gemini-1.5-pro") == "google"
        assert detect_provider_from_model("gemini-pro") == "google"

    def test_detect_groq_from_model_name(self) -> None:
        from src.llm.factory import detect_provider_from_model

        assert detect_provider_from_model("llama-3.3-70b-versatile") == "groq"
        assert detect_provider_from_model("mixtral-8x7b-32768") == "groq"

    def test_detect_mistral_from_model_name(self) -> None:
        from src.llm.factory import detect_provider_from_model

        assert detect_provider_from_model("mistral-large-latest") == "mistral"
        assert detect_provider_from_model("codestral-latest") == "mistral"

    def test_detect_deepseek_from_model_name(self) -> None:
        from src.llm.factory import detect_provider_from_model

        assert detect_provider_from_model("deepseek-chat") == "deepseek"
        assert detect_provider_from_model("deepseek-reasoner") == "deepseek"

    def test_unknown_model_returns_none(self) -> None:
        from src.llm.factory import detect_provider_from_model

        assert detect_provider_from_model("unknown-model-xyz") is None
