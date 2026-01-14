---
name: telegram-bot
description: Telegram Bot API - Build bots that interact with users on Telegram. Use this skill when creating Telegram bots, handling updates, sending messages, working with inline keyboards, handling callbacks, or implementing bot commands.
---

# Telegram Bot API

## Quick Overview

Telegram Bot API allows you to build bots that:
- **Receive messages** from users via updates (polling or webhooks)
- **Send messages** - text, photos, videos, documents, stickers
- **Interactive features** - inline keyboards, buttons, polls
- **Group management** - Admin functions in groups/channels
- **Payments** - Accept payments via Telegram

## Getting Started

### 1. Create a Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Use `/newbot` command
3. Choose a name and username
4. Get your **bot token** (format: `123456:ABC-DEF...`)

### 2. Make Your First Request

```bash
# Get bot info
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe"

# Send a message
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 123456789, "text": "Hello!"}'
```

### 3. Get Updates

```bash
# Long polling (recommended)
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates"
```

## Getting Updates

### Two Methods

**Polling** (default):
```python
# Long polling - wait for new updates
updates = bot.get_updates(timeout=30, offset=last_update_id + 1)
```

**Webhook** (for production):
```python
# Set webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d 'url=https://your-domain.com/webhook'
```

## Core API Methods

### sendMessage

```python
# Simple text
bot.send_message(chat_id=123, text="Hello!")

# With markdown formatting
bot.send_message(
    chat_id=123,
    text="*Bold* and `code`",
    parse_mode="MarkdownV2"
)

# With reply markup
bot.send_message(
    chat_id=123,
    text="Choose an option:",
    reply_markup=ReplyKeyboardMarkup([["Yes", "No"]])
)
```

### sendPhoto

```python
bot.send_photo(
    chat_id=123,
    photo="https://example.com/image.jpg",
    caption="Check this out!"
)

# From file
with open("photo.jpg", "rb") as f:
    bot.send_photo(chat_id=123, photo=f)
```

### editMessageText

```python
bot.edit_message_text(
    chat_id=123,
    message_id=456,
    text="Updated text"
)
```

### deleteMessage

```python
bot.delete_message(chat_id=123, message_id=456)
```

## Inline Keyboards

### Inline Keyboard Buttons

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

keyboard = [
    [
        InlineKeyboardButton("Option 1", callback_data="opt1"),
        InlineKeyboardButton("Option 2", callback_data="opt2"),
    ],
    [InlineKeyboardButton("Link", url="https://example.com")]
]
reply_markup = InlineKeyboardMarkup(keyboard)

bot.send_message(
    chat_id=123,
    text="Choose:",
    reply_markup=reply_markup
)
```

### Handling Callback Queries

```python
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    query.answer()

    if query.data == "opt1":
        await query.edit_message_text("You chose Option 1!")
```

## Reply Keyboards

### Custom Keyboard

```python
from telegram import ReplyKeyboardMarkup

keyboard = [
    ["Start", "Help"],
    ["Settings", "About"]
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

bot.send_message(
    chat_id=123,
    text="Menu:",
    reply_markup=reply_markup
)
```

### Remove Keyboard

```python
from telegram import ReplyKeyboardRemove

bot.send_message(
    chat_id=123,
    text="Keyboard removed",
    reply_markup=ReplyKeyboardRemove()
)
```

## Handler Types (python-telegram-bot)

```python
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.ext import filters

app = Application.builder().token("TOKEN").build()

# Commands - /start, /help, etc.
app.add_handler(CommandHandler("start", start_command))
app.add_handler(CommandHandler("help", help_command))

# Text messages
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Photos
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# Callback queries (inline buttons)
app.add_handler(CallbackQueryHandler(button_callback))

# Run the bot
app.run_polling()
```

## Update Object

Key fields from incoming updates:

```python
# Message update
update.update_id           # Unique update ID
update.message.message_id  # Message ID
update.message.chat.id     # Chat ID (user/group/channel)
update.message.from.id     # User ID
update.message.text        # Message text
update.message.photo       # Array of photo sizes
update.message.document    # Document
update.message.location    # Location
```

## Chat Types

| Type | Description | chat.id behavior |
|------|-------------|------------------|
| `private` | Direct message with user | User ID |
| `group` | Group chat | Negative group ID |
| `supergroup` | Supergroup (can be public) | Negative or positive |
| `channel` | Channel | Channel username or ID |

## Common Commands

### /start

```python
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "👋 Hi! I'm YourBot\n\n"
        "I can help you with:\n"
        "• Task 1\n"
        "• Task 2\n\n"
        "Use /help for more info."
    )
    await update.message.reply_text(welcome)
```

### /help

```python
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *Help*\n\n"
        "*Commands:*\n"
        "/start - Start the bot\n"
        "/help - Show this message\n"
        "/settings - Configure options\n\n"
        "*Features:*\n"
        "• Feature 1\n"
        "• Feature 2"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")
```

## File Handling

### Getting File Info

```python
# Document
file_id = update.message.document.file_id
file = await bot.get_file(file_id)
await file.download_to_drive("downloaded_file.pdf")

# Photo (largest size)
file_id = update.message.photo[-1].file_id
```

### Uploading Files

```python
# Send document
with open("file.pdf", "rb") as f:
    bot.send_document(chat_id=123, document=f, caption="Here's the file")

# Send photo
with open("image.jpg", "rb") as f:
    bot.send_photo(chat_id=123, photo=f, caption="Photo caption")
```

## User Persistence (Conversation State)

Use thread_id for state management:

```python
# Thread ID pattern
thread_id = f"telegram:{chat_id}"

# In LangGraph with checkpointer
config = {"configurable": {"thread_id": thread_id}}
result = await agent.ainvoke({"messages": [user_message]}, config)
```

## Error Handling

```python
from telegram.error import BadRequest, NetworkError

try:
    bot.send_message(chat_id=123, text="Hello")
except BadRequest as e:
    if "chat not found" in str(e):
        # User blocked bot or deleted chat
        pass
except NetworkError as e:
    # Network issue, retry
    pass
```

## Best Practices

1. **Use long polling** for development, **webhooks** for production
2. **Handle errors** - network issues, blocked users
3. **Rate limiting** - Telegram has limits (30 msgs/sec to different users)
4. **Use webhooks** with HTTPS for production
5. **Validate input** - sanitize user input before processing
6. **Log important events** - errors, new users, crashes
7. **Graceful shutdown** - handle SIGTERM/SIGINT

## Security

1. **Never expose your bot token** - use environment variables
2. **Verify webhook** requests if using webhooks
3. **Sanitize input** - don't execute arbitrary commands
4. **Check user permissions** - for admin operations
5. **Rate limit per user** - prevent abuse

## Common Patterns

### Conversation Handler

```python
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler

FIRST, SECOND = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Let's start! What's your name?")
    return FIRST

async def first_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text(f"Hi {context.user_data['name']}! How old are you?")
    return SECOND

async def second_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Thanks!")
    return ConversationHandler.END

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        FIRST: [MessageHandler(filters.TEXT & ~filters.COMMAND, first_step)],
        SECOND: [MessageHandler(filters.TEXT & ~filters.COMMAND, second_step)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
app.add_handler(conv_handler)
```

## References

- **[Official Docs](https://core.telegram.org/bots/api)** - Complete API reference
- **[python-telegram-bot](https://docs.python-telegram-bot.org/)** - Python library docs
- **[BotFather](https://t.me/BotFather)** - Create and manage bots
