# Executive Assistant

Your intelligent assistant that manages tasks, tracks work, stores knowledge, and never forgets a reminder.

## What Executive Assistant Can Do For You

Executive Assistant is a multi-channel AI agent that helps you stay organized and productive. Whether you're tracking timesheets, managing a knowledge base, or automating data analysis, Executive Assistant intelligently selects the right tools for the job.

### Track Your Work
- **Timesheet logging**: Simply tell Executive Assistant what you worked on, and it stores structured data in your private transactional database
- **Time-aware**: Knows the current time in any timezone, perfect for distributed teams
- **Data analysis**: Query your logged work with SQL, export to CSV/JSON, or visualize trends

### Never Forget a Reminder
- **Scheduled notifications**: "Remind me to review PRs at 3pm every weekday"
- **Recurring patterns**: Daily, weekly, or custom schedules with flexible recurrence rules
- **Multi-channel delivery**: Get reminders on Telegram or HTTP webhook

### Build a Knowledge Base
- **Semantic search**: Store documents and find them by meaning, not just keywords
- **Smart retrieval**: Ask "What did we decide about the API pricing?" and get the right answer
- **Shared knowledge**: Store documents and retrieve them semantically across threads (with explicit shared scope)

### Automate Data Work
- **Python execution**: Run calculations, data processing, and file operations in a secure sandbox
- **Web search**: Find current information from the web
- **File operations**: Read, write, search, and organize files with natural language commands

### Intelligent Tool Selection
Executive Assistant uses a skills system to choose the right approach:
- **Analytics Database (ADB)** for fast analytics on large datasets (100K+ rows, joins, aggregations)
- **Transactional Database (TDB)** for structured data and quick lookups (timesheets, logs, configs)
- **Vector Database (VDB)** for semantic search and knowledge retrieval (documents, decisions, conversations)
- **File tools** for raw file operations (codebases, archives, document management)
- **Python** for custom logic, data transformations, and calculations
- **MCP Tools** for extensible external integrations via Model Context Protocol
- **Skills** for contextual knowledge on how to use tools effectively

You don't need to remember which tool does what—Executive Assistant figures it out from context.

### Adaptive Behavior with Instincts
Executive Assistant learns your communication style and preferences automatically:
- **Pattern Detection**: Automatically learns from corrections, repetitions, and preferences
- **Profile Presets**: Quick personality configuration (Concise Professional, Detailed Explainer, etc.)
- **Confidence Scoring**: Behaviors are applied probabilistically based on confidence
- **Evolution**: Learned patterns can evolve into reusable skills

**Example:**
```
You: Be concise
[Assistant learns: user prefers brief responses]

You: Use bullet points
[Assistant learns: user prefers list format]

You: Actually, use JSON for data
[Assistant adjusts: reinforces format preference]
```

## How Executive Assistant Thinks

Executive Assistant is a **ReAct agent** built on LangGraph. Unlike simple chatbots, it:

1. **Reasons** about your request using an LLM
2. **Acts** by calling tools (file operations, transactional database queries, web search, etc.)
3. **Observes** the results and decides what to do next
4. **Responds** with a clear confirmation of what was done

This cycle continues until your task is complete—with safeguards to prevent infinite loops.

### Real-Time Progress Updates
Executive Assistant keeps you informed while working:
- **Normal mode**: Clean status updates edited in place
- **Debug mode**: Detailed timing information (toggle with `/debug`)
- **Per-message limits**: Prevents runaway execution (20 LLM calls, 30 tool calls per message)

## Multi-Channel Access

Executive Assistant works where you work:

### Telegram
- Chat with Executive Assistant in any Telegram conversation
- Commands: `/start`, `/reset`, `/remember`, `/debug`, `/mem`, `/reminder`, `/vdb`, `/tdb`, `/file`, `/meta`, `/user`
- Perfect for mobile quick-tasks and reminders on-the-go

### HTTP API
- Integrate Executive Assistant into your applications
- REST endpoints for messaging and conversation history
- SSE streaming for real-time responses
- **Open access** (authentication handled by your frontend)
- Ideal for workflows, webhooks, and custom integrations

## Storage That Respects Your Privacy

Executive Assistant takes data isolation seriously with a unified `scope` parameter across all storage tools:

### Context-Scoped Storage (Default)
All storage tools support `scope="context"` (default):
- **Thread-only context**: Uses `data/users/{thread_id}/` for private data

```python
# Context-scoped (automatic - uses thread)
create_tdb_table("users", data=[...], scope="context")
write_file("notes.txt", "My notes", scope="context")
create_vdb_collection("knowledge", content="Decisions", scope="context")
```

### Organization-Wide Shared Storage
All storage tools support `scope="shared"` for organization-wide data:
- **Location**: `data/shared/`
- **Accessible by**: All users (read), admins (write)
- **Use cases**: Company-wide knowledge, shared templates, org data

```python
# Organization-wide shared
create_tdb_table("org_users", data=[...], scope="shared")
write_file("policy.txt", "Company policy", scope="shared")
create_vdb_collection("org_knowledge", content="Company processes", scope="shared")
```

### Storage Hierarchy
```
data/
├── shared/              # scope="shared" (organization-wide)
│   ├── files/           # Shared file storage
│   ├── tdb/             # Shared transactional database
│   └── vdb/             # Shared vector database
└── users/               # scope="context" for individual threads
    └── {thread_id}/
        ├── files/
        ├── tdb/
        ├── vdb/
        ├── mem/         # Embedded memories
        └── instincts/   # Learned behavioral patterns
            ├── instincts.jsonl         # Append-only event log
            └── instincts.snapshot.json  # Compacted state
```

### Thread-Scoped Ownership
- Data is stored under `data/users/{thread_id}/`
- Ownership tracking for files, TDB, VDB, and reminders
- Audit log for operations

## Quick Start

```bash
# Setup environment
cp docker/.env.example docker/.env
# Edit docker/.env with your API keys

# Start PostgreSQL
docker compose up -d postgres

# Run migrations (auto-run on first start)
psql $POSTGRES_URL < migrations/001_initial_schema.sql

# Run Executive Assistant (default: Telegram)
uv run executive_assistant

# Run HTTP only
EXECUTIVE_ASSISTANT_CHANNELS=http uv run executive_assistant

# Run both Telegram and HTTP
EXECUTIVE_ASSISTANT_CHANNELS=telegram,http uv run executive_assistant
```

**For local testing**, always use `uv run executive_assistant` instead of Docker. Only build Docker when everything works (see `CLAUDE.md` for testing workflow).

## What Makes Executive Assistant Different

### Unlike Simple Chatbots
- **Tool-using**: Can read files, query databases, search the web, execute Python
- **Persistent**: Remembers context across sessions with PostgreSQL checkpointing
- **Multi-step**: Handles complex tasks that require multiple tool calls
- **Safe**: Sandboxed execution, per-message limits, audit logging

### Unlike Other AI Agents
- **Intelligent storage**: Knows when to use TDB (structured) vs VDB (semantic) vs files (raw)
- **Skills system**: Progressive disclosure of advanced patterns (load with `load_skill`)
- **Instincts system**: Automatically learns behavioral patterns from interactions
- **Privacy-first**: Thread isolation by design, merge only when you request it
- **Multi-channel**: Same agent works on Telegram, HTTP, and more (planned: Email, Slack)
- **All tools available**: All 87 tools available in every conversation
- **Robust error handling**: Comprehensive error logging with full tracebacks at DEBUG level
- **Frontend auth**: HTTP channel delegates authentication to your application layer

### Production-Ready Features
- **Admin customization**: BYO prompt/skills/MCP via `data/admins/` + user allowlist (Telegram only)
- **Middleware stack**: Summarization, retry logic, call limits, todo tracking, context editing, thread context propagation
- **High-precision logging**: Millisecond timestamps for performance analysis
- **Debug mode**: Toggle verbose status updates to understand agent behavior
- **Status updates**: Real-time progress feedback during long-running tasks
- **Thread context middleware**: Ensures thread isolation across async boundaries
- **Enhanced error logging**: All tool errors logged with full traceback at DEBUG level

## Example Workflows

### 🚀 Build a Mini Analytics Dashboard in Seconds
```
You: I have sales.csv with 500K rows. Build me a dashboard showing:
     - Top 10 products by revenue
     - Monthly trend line
     - Category breakdown pie chart
     - Save everything to reports/

Executive Assistant: [Loads ADB for analytics]
     Importing 500K rows to Analytics Database...
     Running queries...
     Generating visualizations...

     ✅ Created 4 reports:
        - top_products.csv (10 rows)
        - monthly_trend.csv (24 rows)
        - category_breakdown.csv (8 rows)
        - sales_dashboard.png (interactive chart)

     💡 Top product: "Widget Pro" - $127,450 revenue
```

### 📊 Ad-Hoc Analytics on Hundreds of MB Data
```
You: Query all logs from 2024, group by endpoint, calculate:
     - Total requests
     - Avg response time
     - P95 response time
     - Error rate
     Export to performance_report.csv

Executive Assistant: [Uses Analytics Database (DuckDB)]
     Scanning logs/2024/*.log (847MB across 12 files)...

     ✅ Analytics complete:
        - 12.4M requests analyzed in 3.2 seconds
        - 2,847 unique endpoints
        - Avg response time: 45ms
        - P95: 180ms
        - Error rate: 0.12%

     💾 Saved to: performance_report.csv
```

### 🧠 Intelligent Knowledge Retrieval
```
You: What did we decide about API rate limits for enterprise customers?
     Also, what was the reasoning behind the GraphQL caching strategy?

Executive Assistant: [Searches Vector Database semantically]
     Found 3 relevant documents:

     1. API Pricing Decision (Jan 15):
        "Enterprise tier: 10,000 req/min, burstable to 50,000"
        Reasoning: "Enterprise customers need burst capacity for...

     2. GraphQL Architecture Discussion (Feb 3):
        "Caching strategy: 5-minute TTL on queries, 1-hour on...
        Reasoning: "Balance freshness vs performance - analytics...

     3. Rate Limit Implementation (Mar 8):
        "Token bucket algorithm with per-IP limits"
        Reasoning: "Prevent abuse while allowing legitimate burst..."
```

### 🔌 Quick Python Data Pipeline
```
You: Download https://api.github.com/repos/langchain-ai/langchain/releases,
     parse the JSON, extract version numbers and publish dates,
     plot a timeline of releases, save to github_releases.png

Executive Assistant: [Uses Python + File tools]
     Fetching releases from GitHub API...
     Parsing 127 releases...
     Generating timeline visualization...

     ✅ Done! Created github_releases.png
     📊 Timeline shows 2.3 releases/week average
     📈 Trend: Increasing release cadence over past 6 months
```

### 🏗️ Build a Multi-Step Workflow App
```
You: Create a daily report that:
     1. Fetches yesterday's sales from PostgreSQL
     2. Enriches with customer data from CRM API
     3. Calculates churn risk using Python
     4. Saves high-risk customers to VDB for follow-up
     5. Emails the summary

Executive Assistant: [Orchestrates TDB + Python + VDB + Web tools]
     Building workflow...

     Step 1: [TDB Query] Retrieved 1,247 transactions
     Step 2: [Web Fetch] Enriched 847 customer profiles
     Step 3: [Python Analysis] Calculated churn scores
              → 73 high-risk (score > 0.7)
              → 231 medium-risk (score > 0.4)
     Step 4: [VDB Store] Indexed high-risk customers for semantic search
     Step 5: [Email Draft] Report generated at reports/daily_churn_2024-01-15.md

     💡 Saved as scheduled flow: "daily_churn_report"
     🕓 Runs daily at 9:00 AM
```

### 🎯 Cross-Reference Multiple Data Sources
```
You: I have:
     - customer_tickets.csv (50K support tickets)
     - product_catalog.json (2K products)
     - usage_logs.parquet (2GB usage data)

     Find me: Products with high churn (>30%) but low usage (<10min/day)
     from customers who filed >5 tickets in the last 30 days

Executive Assistant: [Uses ADB for joins across large datasets]
     Importing datasets to Analytics Database...
     Running complex join query...

     🎯 Found 12 products matching criteria:

        Product           | Churn | Avg Usage | Ticket Count
        ------------------+-------+-----------+-------------
        Legacy Widget     | 47%   | 4min/day  | 8.2 avg
        Enterprise Plan   | 38%   | 7min/day  | 6.1 avg
        Mobile App Basic  | 34%   | 8min/day  | 5.7 avg

     💡 Pattern: All legacy products with poor UX
        → Recommendation: Prioritize UX refresh or deprecation

     💾 Full report: chrun_analysis_report.csv
        Visualization: churn_vs_usage_scatter.png
```

### 📝 Automate Document Analysis
```
You: Read all PDFs in contracts/, extract:
     - Contract value
     - Expiration date
     - Auto-renewal clause
     Store in TDB for querying

Executive Assistant: [Uses OCR + File tools + TDB]
     Processing 47 contracts...

     ✅ Extracted and stored:
        - Total value: $4.2M
        - 15 expiring in next 90 days
        - 32 have auto-renewal
        - 8 require manual renewal (no auto clause)

     💾 Created table: contracts_summary
        Query: SELECT * FROM contracts_summary WHERE days_to_expire < 90
```

### 🔄 Data Migration & Transformation
```
You: Migrate data from MongoDB export (JSON lines) to PostgreSQL:
     - Flatten nested structures
     - Convert timestamps to UTC
     - Deduplicate by email
     - Validate phone numbers
     Report any records that fail validation

Executive Assistant: [Uses Python + TDB tools]
     Reading export.jsonl (1.2GB, 2.8M records)...

     Migration progress:
     ✅ Flattened nested documents: 2.8M → 47 fields
     ✅ Converted timestamps: 2.8M → UTC
     ✅ Deduplicated: 2.8M → 2.34M unique emails
     ⚠️ Validation failures: 12,847 records

     Issues found:
        - Invalid phone: 8,234 (malformed format)
        - Missing email: 3,112 (required field)
        - Future DOB: 1,501 (data entry error)

     💾 Valid records in PostgreSQL: users_import table
        Invalid records saved to: validation_errors.csv
```

## Configuration

Essential environment variables:

```bash
# LLM Provider (choose one)
OPENAI_API_KEY=sk-...           # OpenAI (GPT-4, GPT-4o)
ANTHROPIC_API_KEY=sk-...        # Anthropic (Claude)
ZHIPUAI_API_KEY=...             # Zhipu (GLM-4)

# Channels
EXECUTIVE_ASSISTANT_CHANNELS=telegram,http   # Available channels

# Telegram (if using telegram channel)
TELEGRAM_BOT_TOKEN=...

# PostgreSQL (required for state persistence)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=executive_assistant
POSTGRES_PASSWORD=your_password
POSTGRES_DB=executive_assistant_db
```

See `docker/.env.example` for all available options.

## Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Start conversation / show welcome message |
| `/reset` | Reset the current thread context |
| `/remember` | Save a memory from a single message |
| `/debug` | Toggle verbose status mode (see LLM/tool timing) |
| `/mem` | List/add/update/forget memories |
| `/reminder` | List/set/edit/cancel reminders |
| `/vdb` | Vector store commands |
| `/tdb` | Transactional Database commands |
| `/file` | File commands |
| `/meta` | Show storage summary (files/VDB/TDB/reminders) |
| `/user` | Admin allowlist management |

**Instinct Tools** (available in conversation):
- `list_profiles` - Browse available personality profiles
- `apply_profile` - Apply a profile preset (e.g., "Concise Professional")
- `list_instincts` - Show learned behavioral patterns
- `evolve_instincts` - Cluster patterns into reusable skills

**MCP Tools** (Model Context Protocol - available in conversation):
- `mcp_add_server` - Add an MCP server (stdio or HTTP/SSE)
- `mcp_add_remote_server` - Add a remote MCP server
- `mcp_remove_server` - Remove an MCP server
- `mcp_list_servers` - List all configured MCP servers
- `mcp_show_server` - Show detailed server information
- `mcp_reload` - Reload MCP tools from configuration
- `mcp_export_config` - Export MCP configuration as JSON
- `mcp_import_config` - Import MCP configuration from JSON
- `mcp_list_backups` - List available configuration backups
- `mcp_list_pending_skills` - List skills awaiting approval
- `mcp_approve_skill` - Approve a pending skill proposal
- `mcp_reject_skill` - Reject a pending skill proposal
- `mcp_edit_skill` - Edit skill content before approving
- `mcp_show_skill` - Show detailed skill information

### Debug Mode

Toggle detailed progress tracking:

```bash
/debug           # Show current debug status
/debug on        # Enable verbose mode (see all LLM calls and tools)
/debug off       # Disable (clean mode, status edited in place)
/debug toggle    # Toggle debug mode
```

**Normal mode:** Status messages are edited in place (clean UI)
**Verbose mode:** Each update sent as separate message with LLM timing

Example verbose output:
```
🤔 Thinking...
✅ Done in 12.5s | LLM: 2 calls (11.8s)
```

## HTTP API

When `EXECUTIVE_ASSISTANT_CHANNELS=http`, a FastAPI server starts on port 8000:

```bash
# Send message (streaming)
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"content": "hello", "user_id": "user123", "conversation_id": "myconv", "stream": true}'

# Send message (non-streaming)
curl -X POST http://localhost:8000/message \
  -H "Content-Type: application/json" \
  -d '{"content": "hello", "user_id": "user123", "conversation_id": "myconv", "stream": false}'

# Get conversation history
curl http://localhost:8000/conversations/myconv

# Health check
curl http://localhost:8000/health
```

**Endpoints:**
- `POST /message` - Send message (supports SSE streaming with `stream: true`)
- `GET /conversations/{id}` - Get conversation history
- `GET /health` - Health check

**Authentication:**
- HTTP channel has **open access** - your frontend handles authentication
- Provide any `user_id` and `conversation_id` to identify the session
- Data isolation is enforced per-thread via unique conversation IDs
- Telegram channel uses allowlist (managed via `/user` command)

## Tool Capabilities

### Analytics Database (ADB) - DuckDB Powerhouse
**For serious analytics on medium-to-large datasets (100K to 100M+ rows)**

- **Blazing fast**: Columnar storage, vectorized execution, parallel queries
- **Direct file queries**: Query CSV/Parquet/JSON without importing
- **Complex analytics**: Window functions, CTEs, nested aggregations
- **Multi-way joins**: Combine datasets effortlessly
- **Scalable**: Handles hundreds of MB to GB of data efficiently
- **Use cases**:
  - Sales analytics and reporting
  - Log analysis and aggregation
  - Time-series data processing
  - Data science and ML prep work
  - Business intelligence queries

| Operation | TDB | ADB |
|-----------|-----|-----|
| CRUD operations | ✅ Excellent | ⚠️ Limited |
| Complex queries | ❌ Slow | ✅ Blazing fast |
| Large joins | ❌ Timeout | ✅ Optimized |
| 100M+ rows | ❌ Struggles | ✅ Handles well |
| Frequent updates | ✅ Good | ⚠️ Append-better |

### Transactional Database (TDB) - SQLite Powerhouse
**For structured data and transactional workloads**

- **Instant startup**: No import needed, works immediately
- **ACID compliant**: Reliable transactions and rollbacks
- **SQLite compatible**: Familiar SQL syntax
- **Thread-scoped**: Each conversation gets isolated database
- **Import/Export**: CSV, JSON, Parquet support
- **Use cases**:
  - Timesheets and task tracking
  - Configuration storage
  - Quick data lookups
  - Temporary working data
  - Small-to-medium datasets (<100K rows)

### Vector Database (VDB) - Semantic Search
**For knowledge retrieval and semantic understanding**

- **Meaning-based search**: Find documents by intent, not keywords
- **Hybrid search**: Combines vector similarity with full-text search
- **Persistent**: Survives thread resets
- **Thread-scoped**: Private knowledge per conversation
- **Use cases**:
  - Meeting notes and decisions
  - Documentation lookup
  - Conversational memory
  - Knowledge base management

### Python Execution - Custom Logic Engine
**For calculations, transformations, and automation**

- **Sandboxed**: 30s timeout, path traversal protection
- **Rich libraries**: pandas, numpy, json, csv, datetime, statistics
- **File I/O**: Read/write within thread-scoped directories
- **Data viz**: matplotlib for charts and graphs
- **Use cases**:
  - Data transformations
  - Calculations and simulations
  - API integrations
  - File format conversions
  - Custom business logic

### MCP Integration (Model Context Protocol)
Executive Assistant supports extensible tool integration via MCP servers:
- **User-Managed Servers**: Add your own MCP servers per conversation
- **Auto-Detection**: Automatically suggests relevant skills when adding servers
- **Human-in-the-Loop**: Review and approve skills before loading
- **Hot-Reload**: Add/remove servers without restarting
- **Tiered Loading**: User tools override admin tools for customization
- **Backup/Restore**: Automatic backups with manual restore options

**Example Workflow:**
```bash
# Add fetch MCP server
You: Add the fetch MCP server from GitHub
Assistant: ✅ Added 'fetch' server with 1 tool
        📚 Auto-loaded 2 helper skills:
          • web_scraping
          • fetch_content

# Review and approve skills
You: Show pending skills
You: Approve web_scraping
You: Reload

# Now agent knows how to use fetch effectively!
You: Fetch https://example.com and extract the main heading
Assistant: [Uses web_scraping skill + fetch tool]
        Successfully fetched and extracted heading...
```

**Supported MCP Servers:**
- **Fetch**: Web content extraction (`uvx mcp-server-fetch`)
- **GitHub**: Repository operations and code search (`npx @modelcontextprotocol/server-github`)
- **ClickHouse**: Analytics database queries (`uv run --with mcp-clickhouse`)
- **Filesystem**: File operations (requires paths argument)
- **Brave Search**: Web search integration
- **Puppeteer**: Browser automation
- **And more**: Any MCP server can be added!

### File Operations
- **Read/write**: Create, edit, and organize files
- **Search**: Find files by pattern (`*.py`, `**/*.json`) or search contents with regex
- **Secure**: Thread-scoped paths prevent access to other users' data

### Transactional Database (TDB, per-thread)
- **Create tables**: From JSON/CSV with automatic schema inference
- **Query**: SQLite-compatible SQL (thread/shared scoped)
- **Import/Export**: CSV, JSON, Parquet formats
- **Use case**: Temporary working data (timesheets, logs, analysis results)

### Vector Database (VDB, per-thread)
- **Semantic search**: Find documents by meaning, not just keywords
- **Hybrid search**: Combines full-text + vector similarity
- **Persistent**: Survives thread resets (thread-scoped)
- **Use case**: Long-term knowledge base (meeting notes, decisions, docs)

### Python Execution
- **Sandboxed**: 30s timeout, path traversal protection, thread-scoped I/O
- **Modules**: json, csv, math, datetime, random, statistics, urllib, etc.
- **Use case**: Calculations, data processing, file transformations

### Web Search
- **Firecrawl integration**: Premium web search API with high-quality results
- **Content extraction**: Optional full content scraping from search results
- **Advanced filters**: Location, time-based, categories (web, news, images)
- **Playwright fallback**: JS-heavy pages can be scraped with the browser tool

### Time & Reminders
- **Timezone-aware**: Current time/date in any timezone
- **Flexible scheduling**: One-time or recurring reminders
- **Multi-thread**: Trigger reminders across multiple conversations

### OCR (optional, local)
- **Image/PDF text extraction**: PaddleOCR or Tesseract
- **Structured extraction**: OCR + LLM for JSON output
- **Use case**: Extract data from screenshots, scans, receipts

## Token Usage & Cost Monitoring

Executive Assistant tracks token usage automatically when using supported LLM providers (OpenAI, Anthropic):

```
CH=http CONV=http_user123 TYPE=token_usage | message tokens=7581+19=7600
```

**Note**: Token tracking depends on LLM provider support:
- **OpenAI/Anthropic**: ✅ Full tracking (input + output + total)
- **Ollama**: ❌ No metadata provided (usage not tracked)

**Token Breakdown** (typical conversation):
- System prompt + 87 tools: ~8,100 tokens (fixed overhead)
- Conversation messages: Grows with each turn
- Total input = overhead + messages (e.g., 8,600 tokens by turn 5)

## Architecture Overview

Executive Assistant uses a **LangChain agent** with middleware stack:

1. **User message** → Channel (Telegram/HTTP)
2. **Channel** → LangChain agent with middleware stack
3. **Middleware** → Status updates, summarization, retry logic, call limits
4. **Agent** → ReAct loop (Think → Act → Observe)
5. **Tools** → Storage (files, TDB, VDB), external APIs
6. **Response** → Channel → User

### Storage Hierarchy

```
data/
├── shared/             # Organization-wide (scope="shared")
│   ├── files/          # Shared files
│   ├── tdb/            # Shared transactional database
│   ├── adb/            # Shared analytics database (DuckDB)
│   └── vdb/            # Shared vector database
└── users/              # Thread-scoped (scope="context")
    └── {thread_id}/
        ├── files/      # Private files
        ├── tdb/        # Working transactional database
        ├── adb/        # Thread analytics database (auto-created)
        ├── vdb/        # Thread vector database
        └── mem/        # Embedded memories
```

### PostgreSQL Schema

| Table | Purpose |
|-------|---------|
| `checkpoints` | LangGraph state snapshots (conversation history) |
| `conversations` | Conversation metadata per thread |
| `messages` | Message audit log |
| `file_paths` | File ownership per thread |
| `tdb_paths` | Transactional Database ownership per thread |
| `vdb_paths` | Vector database ownership per thread |
| `adb_paths` | Analytics DB ownership per thread |
| `reminders` | Scheduled reminder notifications |

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_http.py -v
```

Integration tests (live LLM + VCR cassettes):

```bash
# Record live cassettes (requires API key + RUN_LIVE_LLM_TESTS=1)
RUN_LIVE_LLM_TESTS=1 uv run pytest -m "langchain_integration and vcr" --record-mode=once -v

# Or use the helper script
./scripts/pytest_record_cassettes.sh
```

## Project Structure

```
executive_assistant/
├── src/executive_assistant/
│   ├── channels/       # Telegram, HTTP
│   ├── storage/        # File sandbox, TDB, VDB, reminders
│   ├── tools/          # LangChain tools (file, TDB, time, Python, search, OCR)
│   ├── agent/          # LangChain agent runtime + middleware
│   ├── scheduler.py    # APScheduler integration
│   └── config/         # Settings
├── migrations/         # SQL migrations
├── tests/              # Unit tests
├── features/           # Feature tests
├── scripts/            # Utility scripts
├── pyproject.toml
├── TODO.md
└── README.md
```

## License

Apache License 2.0 - see LICENSE file for details.

**Why Apache 2.0?**
- ✅ Explicit patent grant (protects users from patent litigation)
- ✅ Patent termination clause (license ends if you sue over patents)
- ✅ Corporate-friendly (preferred by large companies)
- ✅ Requires stating changes (better provenance tracking)

## Contributing

Contributions welcome! Please read `CLAUDE.md` for development workflow and testing guidelines.

**Remember**: Always test locally with `uv run executive_assistant` before building Docker. See `CLAUDE.md` for details.
