"""Telegram bot integration test.

This test sends a real message to Telegram and verifies the bot is working.
Run with: pytest tests/test_telegram_integration.py -v
"""

import asyncio
import os

import pytest
from telegram import Bot
from telegram.error import TelegramError


@pytest.fixture
def bot_token():
    """Get the bot token from environment."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        pytest.skip("TELEGRAM_BOT_TOKEN not set")
    return token


@pytest.fixture
def chat_id():
    """Get the test chat ID from environment."""
    # Default to Eddy's chat ID for testing
    return int(os.getenv("TEST_CHAT_ID", "6282871705"))


@pytest.mark.asyncio
async def test_send_message(bot_token, chat_id):
    """Test sending a message to Telegram."""
    bot = Bot(token=bot_token)

    # Send a test message
    test_message = "🧪 Integration test message from Cassey bot"
    response = await bot.send_message(chat_id=chat_id, text=test_message)

    # Verify the message was sent
    assert response.message_id > 0
    assert response.text == test_message
    print(f"✓ Message sent successfully (msg_id: {response.message_id})")


@pytest.mark.asyncio
async def test_get_bot_info(bot_token):
    """Test getting bot information."""
    bot = Bot(token=bot_token)
    bot_info = await bot.get_me()

    assert bot_info.username is not None
    assert bot_info.is_bot is True
    print(f"✓ Bot info: @{bot_info.username} (ID: {bot_info.id})")


@pytest.mark.asyncio
async def test_get_updates(bot_token):
    """Test getting pending updates."""
    bot = Bot(token=bot_token)
    updates = await bot.get_updates(timeout=1)

    print(f"✓ Pending updates: {len(updates)}")
    for update in updates:
        if update.message and update.message.chat:
            print(f"  - From {update.message.chat.id}: {update.message.text}")


if __name__ == "__main__":
    # Run tests directly
    async def main():
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            print("TELEGRAM_BOT_TOKEN not set")
            return

        chat_id = int(os.getenv("TEST_CHAT_ID", "6282871705"))

        bot = Bot(token=token)

        # Test 1: Get bot info
        print("Test 1: Get bot info")
        bot_info = await bot.get_me()
        print(f"  ✓ Bot: @{bot_info.username}")

        # Test 2: Send message
        print("\nTest 2: Send message")
        response = await bot.send_message(
            chat_id=chat_id,
            text="🧪 Cassey bot integration test - message sent successfully!"
        )
        print(f"  ✓ Message sent (msg_id: {response.message_id})")

        # Test 3: Get updates
        print("\nTest 3: Get updates")
        updates = await bot.get_updates(timeout=1)
        print(f"  ✓ Pending updates: {len(updates)}")

        print("\n✅ All tests passed!")

    asyncio.run(main())
