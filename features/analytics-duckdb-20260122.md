# Analytics DuckDB (Context-Scoped)

## Plan
1) Add a distinct DuckDB analytics tool to avoid confusion with SQLite /db tools.
2) Store DuckDB files per user_id (context scope), or per group_id when in group context.
3) Register tool in tool registry and add prompt guidance for analytics usage.
4) Document in TECHNICAL_ARCHITECTURE.
5) Run tests.

## Implementation
- Added storage: `src/executive_assistant/storage/analytics_db_storage.py`
  - Resolves analytics DB path based on user_id > group_id > thread_id→user_id.
  - File path: `data/users/{user_id}/analytics/duckdb.db` (or group).
- Added tool: `src/executive_assistant/storage/analytics_db_tools.py`
  - `query_analytics_db(sql, scope="context")` for analytics queries.
- Registered tool: `src/executive_assistant/tools/registry.py`.
- Prompt guidance updated: `src/executive_assistant/agent/prompts.py`.
- Tech doc updated: `TECHNICAL_ARCHITECTURE.md`.

## Tests
- `python3 -m pytest -q`
  - **Failed**: pytest not installed in environment.
  - Error: `No module named pytest`.

## Notes
- DuckDB dependency already present in `pyproject.toml`.
- Scope is context-only (no shared analytics).
