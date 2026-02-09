# Tool Reference Guide

Description: Complete reference of all available tools organized by category with usage guidance

Tags: core, tools, reference, guide, quickstart

## Overview

This skill provides a complete reference of all available tools. Use it to understand what tools exist and when to use each one.

**Tool Categories:**
- **Storage:** Files, TDB, VDB, ADB, Memories, Goals, Instincts
- **Automation:** Reminders, Check-ins
- **External:** Web Search, Browser, OCR
- **Utility:** Python, Time, Meta

---

## File Operations (10 tools)

Local file storage scoped to your thread (`data/users/{thread_id}/files/`).

| Tool | Purpose | Example |
|------|---------|---------|
| `read_file` | Read text file | `read_file("notes.txt")` |
| `write_file` | Write/create file | `write_file("report.md", "# Title")` |
| `list_files` | List directory contents | `list_files("docs", recursive=True)` |
| `create_folder` | Create directory | `create_folder("projects/2025")` |
| `delete_folder` | Remove directory | `delete_folder("temp")` |
| `delete_file` | Delete file | `delete_file("old.txt")` |
| `rename_folder` | Rename directory | `rename_folder("old", "new")` |
| `move_file` | Move/rename file | `move_file("a.txt", "b.txt")` |
| `glob_files` | Find files by pattern | `glob_files("*.py")` |
| `grep_files` | Search file contents | `grep_files("TODO", "src/")` |

**When to use:** Documents, configs, exports, caching, any file I/O.

---

## TDB - Transactional Database (10 tools)

SQLite-based structured storage for transactional data. Best for: CRUD operations, frequent updates, relational data.

| Tool | Purpose |
|------|---------|
| `create_tdb_table` | Create table from JSON/CSV |
| `insert_tdb_table` | Add rows to table |
| `query_tdb` | Execute SQL queries |
| `list_tdb_tables` | Show all tables |
| `describe_tdb_table` | Get table schema |
| `delete_tdb_table` | Drop table |
| `export_tdb_table` | Export to CSV/JSON/Parquet |
| `import_tdb_table` | Import from file |
| `add_tdb_column` | Add column to table |
| `drop_tdb_column` | Remove column |

**When to use:** Timesheets, expenses, tasks - data that changes frequently.

**Example:**
```python
# Track expenses
create_tdb_table("expenses", data='[{"item": "Coffee", "cost": 5.50}]')
query_tdb("SELECT * FROM expenses WHERE cost > 5")
```

---

## VDB - Vector Database (9 tools)

LanceDB-powered semantic search. Best for: Documents, knowledge base, semantic retrieval.

| Tool | Purpose |
|------|---------|
| `create_vdb_collection` | Create vector collection |
| `add_vdb_documents` | Add documents with auto-chunking |
| `add_file_to_vdb` | Index a file directly |
| `search_vdb` | Semantic search |
| `describe_vdb_collection` | Get collection info |
| `vdb_list` | List collections |
| `update_vdb_document` | Update document |
| `delete_vdb_documents` | Remove documents |
| `drop_vdb_collection` | Delete collection |

**When to use:** Meeting notes, research, documentation - data searched by meaning.

**Example:**
```python
# Build knowledge base
create_vdb_collection("meetings")
add_file_to_vdb("meetings", "notes/standup.md")
search_vdb("what did we decide about API?", "meetings")
```

---

## ADB - Analytics Database (9 tools)

DuckDB-powered analytics. Best for: Complex queries, aggregations, large datasets, joins.

| Tool | Purpose |
|------|---------|
| `list_adb_tables` | Show tables |
| `describe_adb_table` | Get schema |
| `show_adb_schema` | Full database overview |
| `query_adb` | Execute DuckDB SQL |
| `create_adb_table` | Create from JSON/CSV |
| `import_adb_csv` | Import CSV file |
| `export_adb_table` | Export to CSV/JSON/Parquet |
| `drop_adb_table` | Delete table |
| `optimize_adb` | Optimize performance |

**When to use:** Analytics, reports, aggregations, window functions, complex SQL.

**Example:**
```python
# Monthly analysis
query_adb("""
    SELECT 
        strftime('%Y-%m', date) as month,
        SUM(amount) as total,
        AVG(amount) as avg
    FROM expenses
    GROUP BY month
""")
```

---

## Memory System (8 tools)

Store and retrieve user preferences and facts.

| Tool | Purpose |
|------|---------|
| `create_memory` | Save a memory |
| `update_memory` | Edit memory |
| `delete_memory` | Remove memory |
| `forget_memory` | Alias for delete |
| `list_memories` | Show all memories |
| `search_memories` | Find by content |
| `get_memory_by_key` | Get specific (e.g., "timezone") |
| `normalize_or_create_memory` | Update or create keyed memory |

**Memory Types:** profile, preference, fact, constraint, style, context

**When to use:** User preferences, important facts, personalization.

**Example:**
```python
create_memory("User prefers dark mode", "preference", key="theme")
get_memory_by_key("theme")  # Returns: User prefers dark mode
```

---

## Goals (3 tools)

Structured goal management for each user thread.

| Tool | Purpose |
|------|---------|
| `create_goal` | Create goal with priority/importance |
| `list_goals` | List goals (filter by status/category) |
| `update_goal` | Update goal fields and progress |

**When to use:** Plan objectives and track progress over time.

---

## Instincts (13 tools)

Learned behavioral patterns (trigger -> action), persisted per thread.

| Tool | Purpose |
|------|---------|
| `create_instinct` | Create a behavioral rule |
| `list_instincts` | List instincts |
| `get_applicable_instincts` | Retrieve context-matched instincts |
| `adjust_instinct_confidence` | Reinforce/weaken an instinct |
| `enable_instinct` / `disable_instinct` | Toggle instinct status |

**When to use:** Capture durable interaction style and behavior preferences.

---

## Check-ins (6 tools)

Configure proactive follow-ups based on journal + goals.

| Tool | Purpose |
|------|---------|
| `checkin_enable` | Enable check-in with schedule |
| `checkin_disable` | Disable check-in |
| `checkin_show` | Show current config |
| `checkin_schedule` | Change frequency |
| `checkin_hours` | Set active hours/days |
| `checkin_test` | Run one immediate check |

**When to use:** Ongoing coaching, progress nudges, periodic health checks.

---

## Reminders (4 tools)

Schedule notifications for future events.

| Tool | Purpose |
|------|---------|
| `reminder_set` | Create reminder |
| `reminder_list` | View reminders |
| `reminder_cancel` | Cancel reminder |
| `reminder_edit` | Modify reminder |

**Time Formats:** "in 30 minutes", "tomorrow at 9am", "next monday at 10am", "11.22pm tonight", "2025-01-15 14:00"

**Preferred explicit format:** `YYYY-MM-DD HH:MM` (+ timezone when known, e.g. `2026-02-06 23:22 Australia/Sydney`)

**When to use:** Deadlines, follow-ups, scheduled tasks.

**Example:**
```python
reminder_set("Review PR", "in 2 hours")
reminder_set("Weekly report", "every friday at 4pm")
```

---

## Flows & Agents

Flow and agent builder tools are currently disabled in production runtime.
Use reminders + check-ins for scheduling/proactive behavior instead.

---

## Web & External (5 tools)

| Tool | Purpose |
|------|---------|
| `search_web` | Search via SearXNG |
| `firecrawl_scrape` | Scrape single page |
| `firecrawl_crawl` | Crawl entire site |
| `firecrawl_check_status` | Check crawl status |
| `playwright_scrape` | Browser automation |

**When to use:** Research, current information, web data extraction.

**Example:**
```python
search_web("Python 3.12 new features")
firecrawl_scrape("https://docs.python.org/3/whatsnew/3.12.html")
```

---

## OCR - Document Processing (2 tools)

| Tool | Purpose |
|------|---------|
| `ocr_extract_text` | Extract text from image/PDF |
| `ocr_extract_structured` | Extract structured data |

**When to use:** Receipts, scanned documents, screenshots, PDFs.

---

## Utility Tools (4 tools)

| Tool | Purpose |
|------|---------|
| `execute_python` | Run Python code |
| `get_current_time` | Get time in timezone |
| `get_current_date` | Get date in timezone |
| `list_timezones` | Show available timezones |

**Python Sandbox:** json, csv, math, pandas, numpy, urllib, pathlib, etc.

---

## Quick Decision Guide

**What storage should I use?**

| Data Type | Use | Why |
|-----------|-----|-----|
| Documents, exports | Files | Simple I/O |
| Transactional data (frequent updates) | TDB | Row-based, ACID |
| Knowledge, documents (semantic search) | VDB | Vector similarity |
| Analytics, aggregations, large datasets | ADB | Columnar, fast queries |
| User preferences, facts | Memories | Persistent key-value |

Flow/agent builder tools are currently disabled in production runtime.

---

## Tool Selection Quick Reference

**Data Import:**
- CSV → TDB: `import_tdb_table()`
- CSV → ADB: `import_adb_csv()`
- File → VDB: `add_file_to_vdb()`
- Web → File: `firecrawl_scrape()` + `write_file()`

**Data Export:**
- TDB → CSV: `export_tdb_table()`
- ADB → CSV/JSON: `export_adb_table()`
- Any → File: `execute_python()` + pandas

**Search:**
- Semantic (meaning): `search_vdb()`
- Structured (SQL): `query_tdb()` or `query_adb()`
- File contents: `grep_files()`
- Web: `search_web()`

**Automation:**
- One-time future: `reminder_set()`
- Recurring: `reminder_set("...", "every friday at 4pm")`
- Proactive nudges: `checkin_enable()` + `checkin_show()`
- Time window controls: `checkin_hours()`

---

## Related Skills

- **analytics_with_duckdb** - Deep dive into ADB/analytics
- **tool_combinations** - Common workflow patterns
- **data_management** - When to use which storage
- **system_patterns** - Runtime architecture and check-in behavior
