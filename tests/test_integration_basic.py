"""Basic integration tests for tools via HTTP API.

These tests verify that tools work correctly when called through the agent,
which is how they're actually used in production.
"""

import asyncio
import uuid

import asyncpg
import pytest
import httpx

from executive_assistant.config import settings


def _pg_count_reminders(thread_id: str, message_substr: str) -> int:
    async def _run() -> int:
        conn = await asyncpg.connect(settings.POSTGRES_URL)
        try:
            return int(
                await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM reminders
                    WHERE thread_id = $1
                      AND message ILIKE $2
                    """,
                    thread_id,
                    f"%{message_substr}%",
                )
            )
        finally:
            await conn.close()

    return asyncio.run(_run())


@pytest.fixture(scope="module")
def base_url():
    """Base URL for the HTTP API."""
    return "http://localhost:8000"


@pytest.fixture(scope="module")
def client():
    """HTTP client for testing."""
    return httpx.Client(timeout=60.0)


class TestTDBToolsIntegration:
    """Integration tests for TDB tools via HTTP API."""

    def test_tdb_create_and_query(self, client, base_url):
        """Test creating a table and querying it via HTTP API."""
        response = client.post(
            f"{base_url}/message",
            json={
                "content": "Create a TDB table called 'test_users' with data: [{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}]. Then query all data from test_users.",
                "user_id": "test_tdb_integration",
                "stream": False
            }
        )

        assert response.status_code == 200
        result = response.json()
        assert len(result) > 0
        # Should have created table and queried data
        response_text = str(result)
        assert "test_users" in response_text or "alice" in response_text.lower()

    def test_tdb_list_tables(self, client, base_url):
        """Test listing tables via HTTP API."""
        response = client.post(
            f"{base_url}/message",
            json={
                "content": "List all TDB tables.",
                "user_id": "test_tdb_list",
                "stream": False
            }
        )

        assert response.status_code == 200


class TestVDBToolsIntegration:
    """Integration tests for VDB tools via HTTP API."""

    def test_vdb_create_and_search(self, client, base_url):
        """Test creating a VDB collection and searching via HTTP API."""
        response = client.post(
            f"{base_url}/message",
            json={
                "content": "Create a VDB collection called 'test_knowledge' with documents: [{'id': '1', 'text': 'Python is a programming language'}, {'id': '2', 'text': 'JavaScript is for web development'}]. Then search for 'programming'.",
                "user_id": "test_vdb_integration",
                "stream": False
            }
        )

        assert response.status_code == 200
        result = response.json()
        assert len(result) > 0


class TestADBToolsIntegration:
    """Integration tests for ADB tools via HTTP API."""

    def test_adb_create_and_query(self, client, base_url):
        """Test creating an ADB table and querying via HTTP API."""
        response = client.post(
            f"{base_url}/message",
            json={
                "content": "Create an ADB table called 'sales' with data: [{'product': 'Laptop', 'price': 999.99}, {'product': 'Mouse', 'price': 29.99}]. Then run a query to get total price by product.",
                "user_id": "test_adb_integration",
                "stream": False
            }
        )

        assert response.status_code == 200


class TestFileToolsIntegration:
    """Integration tests for File tools via HTTP API."""

    def test_file_write_and_read(self, client, base_url):
        """Test writing and reading a file via HTTP API."""
        response = client.post(
            f"{base_url}/message",
            json={
                "content": "Write a file called 'test.txt' with content 'Hello, World!'. Then read the file to confirm.",
                "user_id": "test_file_integration",
                "stream": False
            }
        )

        assert response.status_code == 200
        result = response.json()
        assert len(result) > 0
        response_text = str(result)
        assert "hello" in response_text.lower() or "written" in response_text.lower()


class TestReminderToolsIntegration:
    """Integration tests for Reminder tools via HTTP API."""

    def test_reminder_set_and_list(self, client, base_url):
        """Reminder set must persist to DB and show up in list."""
        reminder_message = f"test_integration_reminder_{uuid.uuid4().hex[:8]}"
        conversation_id = f"test_reminder_integration_{uuid.uuid4().hex[:8]}"

        set_response = client.post(
            f"{base_url}/message",
            json={
                "content": f"Set a reminder in 10 minutes with message {reminder_message}",
                "user_id": "test_reminder_integration",
                "conversation_id": conversation_id,
                "stream": False
            }
        )

        assert set_response.status_code == 200
        set_text = str(set_response.json())
        assert "error:" not in set_text.lower()

        thread_id = f"http:{conversation_id}"
        persisted = _pg_count_reminders(thread_id, reminder_message)
        assert persisted >= 1

        list_response = client.post(
            f"{base_url}/message",
            json={
                "content": "List my reminders",
                "user_id": "test_reminder_integration",
                "conversation_id": conversation_id,
                "stream": False,
            },
        )
        assert list_response.status_code == 200
        list_text = str(list_response.json())
        assert reminder_message.lower() in list_text.lower()


class TestMemoryToolsIntegration:
    """Integration tests for Memory tools via HTTP API."""

    def test_memory_create_and_search(self, client, base_url):
        """Test creating and searching memories via HTTP API."""
        response = client.post(
            f"{base_url}/message",
            json={
                "content": "Create a memory: 'User prefers dark mode'. Then search for memories about 'preferences'.",
                "user_id": "test_memory_integration",
                "stream": False
            }
        )

        assert response.status_code == 200
