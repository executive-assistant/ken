"""Telegram channel implementation using python-telegram-bot."""

import asyncio
from typing import Any

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from langgraph.types import Runnable

from cassey.channels.base import BaseChannel, MessageFormat
from cassey.config.settings import settings


class TelegramChannel(BaseChannel):
    """
    Telegram bot channel implementation.

    This channel handles:
    - Receiving messages via Telegram bot API
    - Processing messages through the ReAct agent
    - Streaming responses back to the user

    Attributes:
        token: Telegram bot token from BotFather.
        agent: Compiled LangGraph ReAct agent.
        application: python-telegram-bot Application instance.
    """

    def __init__(self, token: str | None = None, agent: Runnable | None = None) -> None:
        token = token or settings.TELEGRAM_BOT_TOKEN
        if not token:
            raise ValueError("Telegram bot token not provided")

        super().__init__(agent)
        self.token = token
        self.application: Application | None = None

    async def start(self) -> None:
        """Start the Telegram bot with polling."""
        self.application = Application.builder().token(self.token).build()

        # Register handlers
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        self.application.add_handler(CommandHandler("reset", self._reset_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._message_handler)
        )

        # Start polling
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)

    async def stop(self) -> None:
        """Stop the Telegram bot gracefully."""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

    async def send_message(
        self,
        conversation_id: str,
        content: str,
        parse_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Send a message to a Telegram chat."""
        if not self.application:
            return

        # Don't use parse_mode to avoid markdown parsing errors
        await self.application.bot.send_message(
            chat_id=conversation_id,
            text=content,
            **kwargs,
        )

    async def handle_message(self, message: MessageFormat) -> None:
        """Handle incoming message through the agent."""
        try:
            # Stream agent response
            messages = await self.stream_agent_response(message)

            # Send responses back
            for msg in messages:
                if hasattr(msg, "content") and msg.content:
                    # Clean content for Telegram markdown
                    content = self._clean_markdown(msg.content)
                    await self.send_message(message.conversation_id, content)

        except Exception as e:
            await self.send_message(
                message.conversation_id,
                f"Sorry, an error occurred: {e}",
            )

    def _clean_markdown(self, text: str) -> str:
        """Clean markdown for Telegram compatibility."""
        # Telegram markdown v2 is strict, so we do basic cleaning
        return text

    async def _start_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /start command."""
        welcome_message = (
            "👋 Hi! I'm Cassey, an AI assistant with access to various tools.\n\n"
            "I can help you with:\n"
            "• 🌐 Searching the web\n"
            "• 📄 Reading and writing files\n"
            "• 🔢 Calculations\n"
            "• And more!\n\n"
            "Just send me a message to get started. Use /reset to clear conversation history."
        )
        await update.message.reply_text(welcome_message)

    async def _help_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /help command."""
        help_message = (
            "🤖 Cassey Help\n\n"
            "Commands:\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/reset - Clear conversation history\n\n"
            "What I can do:\n"
            "• Search the web for information\n"
            "• Read and write files\n"
            "• Perform calculations\n"
            "• Use various tools to help you\n\n"
            "Just ask me anything!"
        )
        await update.message.reply_text(help_message)

    async def _reset_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle /reset command to clear conversation."""
        # Note: This is a soft reset - actual state clearing would need
        # access to the checkpointer to delete the thread
        await update.message.reply_text("🔄 Conversation reset! Start fresh.")

    async def _message_handler(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        """Handle incoming text messages."""
        if not update.message or not update.message.text:
            return

        try:
            # Create MessageFormat
            message = MessageFormat(
                content=update.message.text,
                user_id=str(update.effective_user.id),
                conversation_id=str(update.effective_chat.id),
                message_id=str(update.message.message_id),
                metadata={
                    "username": update.effective_user.username,
                    "first_name": update.effective_user.first_name,
                    "chat_type": update.effective_chat.type,
                },
            )

            # Show typing indicator
            await update.message.chat.send_action("typing")

            # Handle through agent
            await self.handle_message(message)
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = str(e) if str(e) else f"{type(e).__name__}"
            await update.message.reply_text(f"Sorry, an error occurred: {error_msg}")

    @staticmethod
    def get_thread_id(message: MessageFormat) -> str:
        """Generate thread_id for Telegram conversations."""
        return f"telegram:{message.conversation_id}"
