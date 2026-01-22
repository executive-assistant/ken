"""DuckDB analytics tools (context-scoped)."""

from __future__ import annotations

from typing import Literal

from langchain_core.tools import tool

from executive_assistant.storage.analytics_db_storage import get_analytics_db
from executive_assistant.storage.group_storage import require_permission


Scope = Literal["context"]


def _split_sql_statements(sql: str) -> list[str]:
    """Split SQL string into statements, respecting quotes."""
    statements: list[str] = []
    current: list[str] = []
    in_single_quote = False
    in_double_quote = False

    for ch in sql:
        if ch == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote

        if ch == ";" and not in_single_quote and not in_double_quote:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            continue

        current.append(ch)

    tail = "".join(current).strip()
    if tail:
        statements.append(tail)

    return statements


def _format_query_results(columns: list[str], rows: list[tuple]) -> str:
    if not rows:
        return "Query returned 0 rows"

    col_widths = {col: len(col) for col in columns}
    for row in rows:
        for i, val in enumerate(row):
            val_str = str(val) if val is not None else "NULL"
            col_widths[columns[i]] = max(col_widths[columns[i]], len(val_str))

    output: list[str] = []
    output.append(" | ".join(col.ljust(col_widths[col]) for col in columns))
    output.append("-+-".join("-" * col_widths[col] for col in columns))

    for row in rows:
        vals = [str(row[i]) if row[i] is not None else "NULL" for i in range(len(columns))]
        output.append(" | ".join(val.ljust(col_widths[columns[i]]) for i, val in enumerate(vals)))

    return "\n".join(output)


@tool
@require_permission("read")
def query_analytics_db(sql: str, scope: Scope = "context") -> str:
    """Run DuckDB SQL for analytics (context-scoped). [ANALYTICS_DB]

    USE THIS WHEN: You need fast analytics, joins, or large-file analysis.

    Args:
        sql: DuckDB SQL query to execute.
        scope: "context" (default) for user/group-scoped analytics DB.

    Returns:
        Query results as formatted text.
    """
    try:
        conn = get_analytics_db(scope)
        statements = _split_sql_statements(sql)
        if not statements:
            return "No SQL provided"

        last_cursor = None
        for statement in statements:
            last_cursor = conn.execute(statement)

        if last_cursor is None:
            return "No statements executed"

        if last_cursor.description is None:
            return "Query executed successfully"

        columns = [col[0] for col in last_cursor.description]
        rows = last_cursor.fetchall()
        return _format_query_results(columns, rows)

    except Exception as e:
        return f"Error executing analytics query: {str(e)}"


async def get_analytics_db_tools() -> list:
    return [query_analytics_db]
