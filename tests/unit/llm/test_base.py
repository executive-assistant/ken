from langchain_core.language_models.chat_models import BaseChatModel

from src.llm.base import BaseLLMProvider
from src.llm.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMError,
    LLMModelNotFoundError,
    LLMProviderNotFoundError,
    LLMRateLimitError,
)


class TestLLMErrors:
    def test_llm_error_basic(self) -> None:
        error = LLMError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert isinstance(error, Exception)

    def test_llm_configuration_error(self) -> None:
        error = LLMConfigurationError("Missing API key", provider="openai")
        assert str(error) == "Missing API key"
        assert error.provider == "openai"
        assert isinstance(error, LLMError)

    def test_llm_provider_not_found_error(self) -> None:
        error = LLMProviderNotFoundError(provider="unknown")
        assert "unknown" in str(error)
        assert error.provider == "unknown"
        assert isinstance(error, LLMError)

    def test_llm_authentication_error(self) -> None:
        error = LLMAuthenticationError("Invalid API key", provider="anthropic")
        assert str(error) == "Invalid API key"
        assert error.provider == "anthropic"
        assert isinstance(error, LLMError)

    def test_llm_rate_limit_error(self) -> None:
        error = LLMRateLimitError("Rate limit exceeded", provider="openai", retry_after=60)
        assert str(error) == "Rate limit exceeded"
        assert error.provider == "openai"
        assert error.retry_after == 60
        assert isinstance(error, LLMError)

    def test_llm_model_not_found_error(self) -> None:
        error = LLMModelNotFoundError("Model not found", provider="openai", model="gpt-5")
        assert str(error) == "Model not found"
        assert error.provider == "openai"
        assert error.model == "gpt-5"
        assert isinstance(error, LLMError)


class ConcreteLLMProvider(BaseLLMProvider):
    def create_chat_model(self, model: str, **kwargs) -> BaseChatModel:
        from unittest.mock import MagicMock

        return MagicMock(spec=BaseChatModel)

    def is_available(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "test_provider"


class TestBaseLLMProvider:
    def test_provider_name(self) -> None:
        provider = ConcreteLLMProvider(api_key="test-key")
        assert provider.provider_name == "test_provider"

    def test_is_available(self) -> None:
        provider = ConcreteLLMProvider(api_key="test-key")
        assert provider.is_available() is True

    def test_create_chat_model(self) -> None:
        provider = ConcreteLLMProvider(api_key="test-key")
        model = provider.create_chat_model("test-model")
        assert model is not None

    def test_provider_with_no_api_key(self) -> None:
        provider = ConcreteLLMProvider()
        assert provider.api_key is None

    def test_provider_with_custom_kwargs(self) -> None:
        provider = ConcreteLLMProvider(
            api_key="test-key",
            base_url="https://custom.api.com",
            timeout=30,
        )
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://custom.api.com"
        assert provider.timeout == 30
