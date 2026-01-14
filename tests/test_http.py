"""Unit tests for HTTP channel."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from cassey.channels.http import HttpChannel, MessageRequest, MessageChunk, HealthResponse
from cassey.channels.base import MessageFormat


class TestMessageRequest:
    """Test MessageRequest model."""

    def test_valid_request(self):
        """Test creating a valid message request."""
        req = MessageRequest(
            content="Hello",
            user_id="user_123",
            conversation_id="conv_123",
            stream=False,
        )

        assert req.content == "Hello"
        assert req.user_id == "user_123"
        assert req.conversation_id == "conv_123"
        assert req.stream is False

    def test_request_with_defaults(self):
        """Test request with default values."""
        req = MessageRequest(content="Hello", user_id="user_123")

        assert req.conversation_id is None
        assert req.stream is True  # Default
        assert req.metadata is None


class TestMessageChunk:
    """Test MessageChunk model."""

    def test_chunk_creation(self):
        """Test creating a message chunk."""
        chunk = MessageChunk(content="Hello", role="assistant", done=False)

        assert chunk.content == "Hello"
        assert chunk.role == "assistant"
        assert chunk.done is False


class TestHealthResponse:
    """Test HealthResponse model."""

    def test_health_response(self):
        """Test creating a health response."""
        response = HealthResponse(status="healthy", channel="http")

        assert response.status == "healthy"
        assert response.channel == "http"
        assert response.version == "1.0.0"


@pytest.fixture
def http_channel():
    """Create an HTTP channel instance."""
    agent = AsyncMock()
    agent.astream = AsyncMock()
    return HttpChannel(agent=agent, host="127.0.0.1", port=8765)


class TestHttpChannel:
    """Test HttpChannel class."""

    def test_channel_name(self, http_channel):
        """Test channel name."""
        assert http_channel.channel_name == "http"

    def test_initialization(self):
        """Test channel initialization."""
        agent = AsyncMock()
        channel = HttpChannel(agent=agent, host="0.0.0.0", port=9000)

        assert channel.host == "0.0.0.0"
        assert channel.port == 9000
        assert channel.agent == agent
        assert channel.app is not None

    def test_get_thread_id(self, http_channel):
        """Test thread ID generation."""
        message = MessageFormat(
            content="Hello",
            user_id="user_123",
            conversation_id="conv_456",
            message_id="msg_1",
        )

        thread_id = http_channel.get_thread_id(message)
        assert thread_id == "http:conv_456"

    @pytest.mark.asyncio
    async def test_send_message_no_op(self, http_channel):
        """Test that send_message is a no-op for basic HTTP."""
        # Should not raise any errors
        await http_channel.send_message("conv_123", "Hello")

    @pytest.mark.asyncio
    async def test_stream_response(self, http_channel):
        """Test streaming response generator."""
        from langchain_core.messages import AIMessage

        # Mock the stream_agent_response to return messages
        http_channel.stream_agent_response = AsyncMock(
            return_value=[AIMessage(content="Hello there!")]
        )

        message = MessageFormat(
            content="Hi",
            user_id="user_123",
            conversation_id="conv_123",
            message_id="msg_1",
        )

        chunks = []
        async for chunk in http_channel._stream_response(message):
            chunks.append(chunk)

        # Should have at least the message chunk plus done signal
        assert len(chunks) >= 2
        assert '{"done": true}' in chunks[-1]

    def test_routes_setup(self, http_channel):
        """Test that routes are properly set up."""
        routes = [route.path for route in http_channel.app.routes]

        assert "/" in routes
        assert "/message" in routes
        assert "/health" in routes
        assert "/conversations/{conversation_id}" in routes

    @pytest.mark.asyncio
    async def test_handle_message(self, http_channel):
        """Test handle_message implementation."""
        from langchain_core.messages import AIMessage

        http_channel.stream_agent_response = AsyncMock(
            return_value=[AIMessage(content="Response")]
        )

        message = MessageFormat(
            content="Hi",
            user_id="user_123",
            conversation_id="conv_123",
            message_id="msg_1",
        )

        # Should not raise any errors
        await http_channel.handle_message(message)
        http_channel.stream_agent_response.assert_called_once()


@pytest.mark.asyncio
async def test_http_endpoints(http_channel):
    """Test HTTP endpoints integration."""
    from langchain_core.messages import AIMessage

    # Mock agent response
    async def mock_stream(*args, **kwargs):
        """Mock streaming events."""
        yield {"messages": [AIMessage(content="Hello!")]}

    http_channel.agent.astream = mock_stream

    # Create transport for testing FastAPI app
    transport = ASGITransport(app=http_channel.app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test health endpoint
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["channel"] == "http"

        # Test root endpoint
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
