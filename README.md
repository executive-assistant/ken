# Cassey

Multi-channel AI agent platform with LangGraph ReAct agent.

## Features

- **ReAct Agent** - Tool-using agent with LangGraph
- **Multi-Channel** - Telegram, HTTP, Email (planned)
- **Thread/User Isolation** - Per-thread file and database storage
- **Merge Operations** - Merge threads into persistent user identity
- **Audit Logging** - Message and conversation tracking
- **Time Tools** - Current time/date in any timezone
- **Reminders** - Scheduled notifications with recurrence
- **Web Search** - SearXNG integration
- **Python Execution** - Sandboxed code execution for calculations and data processing
- **File Search** - Glob patterns and grep content search

## Architecture

### Storage
- `conversations` - Conversation metadata per thread/channel
- `messages` - Full message audit log
- `file_paths` - File ownership tracking per thread
- `db_paths` - Database ownership tracking per thread
- `user_registry` - Operation audit log (merge/split/remove)
- `reminders` - Scheduled reminder notifications

### Tools

**File Operations:**
- `read_file` - Read file contents
- `write_file` - Write files
- `list_files` - Browse directory contents
- `create_folder` / `delete_folder` / `rename_folder` - Folder management
- `move_file` - Move/rename files
- `glob_files` - Find files by pattern (`*.py`, `**/*.json`)
- `grep_files` - Search file contents with regex

**Database Operations:**
- `create_table` - Create table with column definitions
- `query_table` - Execute SQL queries
- `insert_table` - Insert rows
- `update_table` / `delete_table` - Modify data
- `list_tables` - Show all tables
- `describe_table` - Show table schema
- `export_table` / `import_table` - Data export/import

**Time & Reminders:**
- `get_current_time` - Current time in any timezone
- `get_current_date` - Current date
- `list_timezones` - Available timezones
- `set_reminder` - Create reminders with recurrence
- `list_reminders` - Show active reminders
- `cancel_reminder` - Cancel pending reminders
- `edit_reminder` - Modify existing reminders

**Code Execution:**
- `execute_python` - Sandboxed Python for calculations, data processing, file I/O
  - Thread-scoped file access
  - Allowed modules: json, csv, math, datetime, random, statistics, urllib, etc.
  - 30s timeout, path traversal protection

**Web Search:**
- `web_search` - Search via SearXNG

**Other:**
- Calculator tool

### Thread vs User Isolation

- **Anonymous users**: Identified by `thread_id` (e.g., `telegram:123456789`)
- **Merged users**: Have persistent `user_id` with ownership across threads
- **Files & Database**: Each stored in sanitized thread-specific directories
- **Merge**: Updates ownership records only (no checkpoint migration)

## Quick Start

```bash
# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Start PostgreSQL
docker-compose up -d

# Run migrations (auto-run on first start)
psql $POSTGRES_URL < migrations/001_initial_schema.sql

# Run bot (default: Telegram)
uv run cassey

# Run HTTP only
CASSEY_CHANNELS=http uv run cassey

# Run both Telegram and HTTP
CASSEY_CHANNELS=telegram,http uv run cassey
```

## HTTP API

When `CASSEY_CHANNELS=http`, a FastAPI server starts on port 8000:

```bash
# Send message (streamed by default)
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"content": "hello", "user_id": "user123", "stream": false}'

# Get conversation history
curl http://localhost:8000/conversations/http_user123

# Health check
curl http://localhost:8000/health
```

**Endpoints:**
- `POST /message` - Send message (supports SSE streaming)
- `GET /conversations/{id}` - Get conversation history
- `GET /health` - Health check

## Database Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| checkpoints | LangGraph state snapshots |
| conversations | Conversation metadata per thread |
| messages | Message audit log |
| file_paths | File ownership per thread |
| db_paths | Database ownership per thread |
| user_registry | Operation audit (merge/split/remove) |
| reminders | Scheduled reminder notifications |

### Key Columns

- `conversations.user_id` - NULL for anonymous, set after merge
- `file_paths.thread_id` - Maps to sanitized directory name
- `db_paths.thread_id` - Maps to .db file name
- `reminders.user_id` - Owner of the reminder
- `reminders.thread_ids` - Threads that can trigger the reminder

## Merge Operations

Merge threads into a persistent user identity:

```python
from cassey.storage.user_registry import UserRegistry

registry = UserRegistry()
result = await registry.merge_threads(
    source_thread_ids=["telegram:123456", "http:abc123"],
    target_user_id="user@example.com"
)
# Returns: {conversations_updated, file_paths_updated, db_paths_updated}
```

**Important**: This updates ownership records only. LangGraph checkpoints remain separate.

## File Operations

Files are stored in per-thread directories:

```
data/files/
  telegram_123456789/
    notes.txt
    data.csv
  http_abc123/
    report.md
```

Sanitized thread_id used as directory name (replaces `:`, `/`, `@`, `\` with `_`).

### File Search

```python
# Find files by pattern
glob_files("*.py")           # All Python files
glob_files("**/*.json")       # Recursive JSON search
glob_files("test_*")          # Files starting with test_

# Search file contents
grep_files("TODO", output_mode="files")     # Which files contain TODO
grep_files("API_KEY", output_mode="content") # Show matching lines
grep_files("error", output_mode="count")     # Count matches
```

## Database Operations

Each thread gets its own database:

```
data/db/
  telegram_123456789.db
  http_abc123.db
```

Available tools:
- `create_table(name, columns)` - Create table with column definitions
- `create_table_from_data(name, data)` - Create from Python data
- `query_table(sql)` - Execute SQL query
- `insert_table(name, data)` - Insert rows
- `update_table(name, data, condition)` - Update rows
- `delete_table(name, condition)` - Delete rows
- `list_tables()` - Show all tables
- `describe_table(name)` - Show table schema

## Knowledge Base Storage

KB files follow the same per-thread layout as databases, but live under a separate root:

```
data/kb/
  telegram_123456789.db
  http_abc123.db
```

## Python Code Execution

The `execute_python` tool allows sandboxed Python execution:

```python
# Math calculations
execute_python("print(2 + 2)")
# "4"

# Data processing
execute_python("""
import csv, json
with open('data.csv') as f:
    data = list(csv.DictReader(f))
print(json.dumps(data))
""")

# File I/O (thread-scoped)
execute_python("""
with open('output.json', 'w') as f:
    json.dump({'result': 42}, f)
""")
```

**Security:**
- 30 second timeout
- Path traversal protection
- File extension whitelist
- Max file size: 10MB
- Thread-scoped directories

## Configuration

Environment variables:

```bash
# Required
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=...
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=cassey
POSTGRES_PASSWORD=cassey_password
POSTGRES_DB=cassey_db

# Channels
CASSEY_CHANNELS=telegram  # Options: telegram, http (comma-separated)

# Optional
DEFAULT_LLM_PROVIDER=openai  # Options: openai, anthropic, zhipu
SEARXNG_HOST=https://searxng.example.com  # Web search
HTTP_HOST=0.0.0.0   # HTTP server host (default: 0.0.0.0)
HTTP_PORT=8000      # HTTP server port (default: 8000)
FILES_ROOT=./data/files  # Default file storage
DB_ROOT=./data/db        # Default DuckDB database storage
KB_ROOT=./data/kb        # Default KB DuckDB storage
```

## Project Structure

```
cassey/
├── src/cassey/
│   ├── channels/       # Telegram, HTTP
│   ├── storage/        # User registry, file sandbox, database, reminders
│   ├── tools/          # LangChain tools (file, database, time, python, search, etc.)
│   ├── agent/          # LangGraph agent graph
│   ├── scheduler.py    # APScheduler integration
│   └── config/         # Settings
├── migrations/         # SQL migrations
├── tests/              # Unit tests
├── pyproject.toml
├── TODO.md
└── README.md
```

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_http.py -v
```
