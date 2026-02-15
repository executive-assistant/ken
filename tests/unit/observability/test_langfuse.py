from unittest.mock import MagicMock, patch

from src.observability.langfuse import (
    LangfuseClient,
    LangfuseNoopClient,
    get_langfuse_client,
    is_langfuse_enabled,
    trace_llm_call,
)


class TestLangfuseNoopClient:
    def test_noop_client_trace_returns_context_manager(self) -> None:
        client = LangfuseNoopClient()
        with client.trace(name="test-trace") as trace:
            assert trace is not None

    def test_noop_client_span_returns_context_manager(self) -> None:
        client = LangfuseNoopClient()
        with client.span(name="test-span") as span:
            assert span is not None

    def test_noop_client_generation_returns_context_manager(self) -> None:
        client = LangfuseNoopClient()
        with client.generation(name="test-gen") as gen:
            assert gen is not None

    def test_noop_client_is_enabled_returns_false(self) -> None:
        client = LangfuseNoopClient()
        assert client.is_enabled() is False

    def test_noop_client_flush_does_nothing(self) -> None:
        client = LangfuseNoopClient()
        client.flush()

    def test_noop_client_update_trace_does_nothing(self) -> None:
        client = LangfuseNoopClient()
        client.update_trace(trace_id="test", metadata={"key": "value"})


class TestLangfuseClient:
    def test_client_enabled_when_configured(self, mock_env_with_langfuse: dict[str, str]) -> None:
        with patch("src.observability.langfuse.Langfuse") as mock_langfuse:
            mock_instance = MagicMock()
            mock_langfuse.return_value = mock_instance
            client = LangfuseClient(
                public_key="pk-test",
                secret_key="sk-test",
                host="https://cloud.langfuse.com",
            )
            assert client.is_enabled() is True

    def test_client_disabled_when_keys_missing(self) -> None:
        client = LangfuseClient(
            public_key=None,
            secret_key=None,
            host="https://cloud.langfuse.com",
        )
        assert client.is_enabled() is False

    def test_client_creates_trace(self, mock_env_with_langfuse: dict[str, str]) -> None:
        with patch("src.observability.langfuse.Langfuse") as mock_langfuse:
            mock_instance = MagicMock()
            mock_trace = MagicMock()
            mock_instance.trace.return_value = mock_trace
            mock_langfuse.return_value = mock_instance

            client = LangfuseClient(
                public_key="pk-test",
                secret_key="sk-test",
                host="https://cloud.langfuse.com",
            )

            trace = client.trace(name="test-trace", metadata={"user_id": "123"})
            assert trace is not None

    def test_client_flush_calls_langfuse_flush(
        self, mock_env_with_langfuse: dict[str, str]
    ) -> None:
        with patch("src.observability.langfuse.Langfuse") as mock_langfuse:
            mock_instance = MagicMock()
            mock_langfuse.return_value = mock_instance

            client = LangfuseClient(
                public_key="pk-test",
                secret_key="sk-test",
                host="https://cloud.langfuse.com",
            )
            client.flush()

            mock_instance.flush.assert_called_once()


class TestGetLangfuseClient:
    def test_returns_noop_when_disabled(self, mock_env_with_openai: dict[str, str]) -> None:
        from src.config import settings as settings_module

        settings_module._settings = None
        client = get_langfuse_client()
        assert isinstance(client, LangfuseNoopClient)
        settings_module._settings = None

    def test_returns_client_when_enabled(self, mock_env_with_langfuse: dict[str, str]) -> None:
        from src.config import settings as settings_module

        settings_module._settings = None
        with patch("src.observability.langfuse.Langfuse"):
            client = get_langfuse_client()
            assert isinstance(client, LangfuseClient)
        settings_module._settings = None


class TestIsLangfuseEnabled:
    def test_returns_false_when_disabled(self, mock_env_with_openai: dict[str, str]) -> None:
        from src.config import settings as settings_module

        settings_module._settings = None
        assert is_langfuse_enabled() is False
        settings_module._settings = None

    def test_returns_true_when_enabled(self, mock_env_with_langfuse: dict[str, str]) -> None:
        from src.config import settings as settings_module

        settings_module._settings = None
        assert is_langfuse_enabled() is True
        settings_module._settings = None


class TestTraceLLMCall:
    def test_trace_llm_call_creates_context(self, mock_env_with_langfuse: dict[str, str]) -> None:
        with (
            patch("src.observability.langfuse.Langfuse"),
            trace_llm_call(
                provider="openai",
                model="gpt-4o",
                user_id="user-123",
            ) as trace,
        ):
            assert trace is not None

    def test_trace_llm_call_with_noop_when_disabled(
        self, mock_env_with_openai: dict[str, str]
    ) -> None:
        from src.config import settings as settings_module

        settings_module._settings = None
        with trace_llm_call(
            provider="openai",
            model="gpt-4o",
        ) as trace:
            assert trace is not None
        settings_module._settings = None
