from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from src.config.settings import get_settings, parse_model_string
from src.llm import get_llm
from src.llm.errors import LLMError

if TYPE_CHECKING:
    from telegram import Update

logger = logging.getLogger(__name__)


class TelegramBot:
    """
    Telegram bot for interacting with the Ken deep agent.

    Supports:
    - /start - Start conversation
    - /help - Show help
    - /model - Set model for conversation
    - /clear - Clear conversation history
    - Text messages - Chat with agent
    """

    def __init__(
        self,
        token: str,
        default_provider: str = "openai",
        default_model: str = "gpt-4o",
    ) -> None:
        self.token = token
        self.default_provider = default_provider
        self.default_model = default_model
        self._application: Application | None = None
        self._user_models: dict[int, tuple[str, str]] = {}

    @property
    def application(self) -> Application:
        if self._application is None:
            self._application = Application.builder().token(self.token).build()
            self._setup_handlers()
        return self._application

    def _setup_handlers(self) -> None:
        """Set up command and message handlers."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("model", self.model_command))
        self.application.add_handler(CommandHandler("clear", self.clear_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not update.effective_message:
            return

        user = update.effective_user
        user_name = user.first_name if user else "there"

        settings = get_settings()
        agent_name = settings.agent_name

        await update.effective_message.reply_text(
            f"Hello {user_name}! I'm {agent_name}, your AI assistant.\n\n"
            "Commands:\n"
            "/model <provider/model> - Set model (e.g., /model openai/gpt-4o)\n"
            "/clear - Clear conversation history\n"
            "/help - Show this message\n\n"
            "Just send me a message to start chatting!"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        if not update.effective_message:
            return

        await update.effective_message.reply_text(
            "Ken - Executive Assistant Agent\n\n"
            "Commands:\n"
            "/start - Start conversation\n"
            "/model <provider/model> - Change model\n"
            "/clear - Clear history\n"
            "/help - Show this message\n\n"
            "Supported providers: openai, anthropic, google, groq, mistral, cohere, ollama"
        )

    async def model_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /model command to change the model."""
        if not update.effective_message or not update.effective_user:
            return

        user_id = update.effective_user.id

        if not context.args:
            current = self._user_models.get(user_id, (self.default_provider, self.default_model))
            await update.effective_message.reply_text(
                f"Current model: {current[0]}/{current[1]}\n\n"
                "Usage: /model <provider/model>\n"
                "Example: /model anthropic/claude-3-5-sonnet-20241022"
            )
            return

        model_string = " ".join(context.args)
        try:
            provider, model = parse_model_string(model_string)
            self._user_models[user_id] = (provider, model)
            await update.effective_message.reply_text(f"Model changed to: {provider}/{model}")
        except ValueError as e:
            await update.effective_message.reply_text(
                f"Invalid model format. Use: provider/model\nError: {e}"
            )

    async def agent_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /agent command to switch to deep agent mode."""
        if not update.effective_message or not update.effective_user:
            return

        user_id = update.effective_user.id
        self._user_agent_mode[user_id] = True
        context.user_data["messages"] = []
        await update.effective_message.reply_text(
            "Switched to deep agent mode.\n\n"
            "Features: Planning, memory persistence, web search, subagents.\n"
            "Thread ID will be: telegram-{user_id}"
        )

    async def simple_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /simple command to switch to simple LLM mode."""
        if not update.effective_message or not update.effective_user:
            return

        user_id = update.effective_user.id
        self._user_agent_mode[user_id] = False
        await update.effective_message.reply_text(
            "Switched to simple LLM mode.\n\nJust chat - no planning, tools, or persistent memory."
        )

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /clear command to clear conversation history."""
        if not update.effective_message:
            return

        context.user_data["messages"] = []
        await update.effective_message.reply_text("Conversation history cleared.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages."""
        if not update.effective_message or not update.effective_user:
            return

        user_id = update.effective_user.id
        user_message = update.effective_message.text

        await self._handle_deep_agent(update, context, user_id, user_message)

    async def _handle_deep_agent(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        user_message: str,
    ) -> None:
        """Handle message using deep agent."""
        from langchain_core.messages import HumanMessage

        from src.agent import create_ken_agent

        provider, model = self._user_models.get(
            user_id, (self.default_provider, self.default_model)
        )

        try:
            settings = get_settings()
            thread_id = f"telegram-{user_id}"

            async with create_ken_agent(settings, user_id=str(user_id)) as agent:
                result = await agent.ainvoke(
                    {"messages": [HumanMessage(content=user_message)]},
                    config={"configurable": {"thread_id": thread_id}},
                )

            last_message = result["messages"][-1]
            content = (
                last_message.content if hasattr(last_message, "content") else str(last_message)
            )

            await update.effective_message.reply_text(content)

        except LLMError as e:
            logger.error(f"LLM error: {e}")
            await update.effective_message.reply_text(f"Sorry, I encountered an error: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await update.effective_message.reply_text(
                "Sorry, an unexpected error occurred. Please try again."
            )

    async def start(self) -> None:
        """Start the bot."""
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

    async def stop(self) -> None:
        """Stop the bot."""
        if self.application.updater:
            await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()

    async def run(self) -> None:
        """Run the bot (blocking)."""
        await self.start()
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()


_bot: TelegramBot | None = None


def get_bot() -> TelegramBot | None:
    """Get the Telegram bot singleton."""
    return _bot


def create_bot() -> TelegramBot | None:
    """Create and return the Telegram bot if configured."""
    global _bot

    settings = get_settings()

    if not settings.is_telegram_configured:
        logger.info("Telegram bot not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_ENABLED.")
        return None

    provider, model = parse_model_string(settings.llm.default_model)

    _bot = TelegramBot(
        token=settings.telegram_bot_token or "",
        default_provider=provider,
        default_model=model,
    )

    return _bot


async def run_bot() -> None:
    """Run the Telegram bot."""
    bot = create_bot()
    if bot:
        logger.info("Starting Telegram bot...")
        await bot.run()


def run_bot_sync() -> None:
    """Run the Telegram bot synchronously."""
    asyncio.run(run_bot())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_bot_sync()
