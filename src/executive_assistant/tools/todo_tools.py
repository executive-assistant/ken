"""Todo list tool for tracking agent execution steps.

This tool integrates with TodoListMiddleware to display task progress to users.
"""

from langchain_core.tools import tool


@tool
def write_todos(todos: list[dict]) -> str:
    """Create and manage a structured task list for your current work session.

    This tool helps you track your progress and shows the user what you're working on.
    Use this for EVERY task - simple or complex.

    Args:
        todos: List of todo items with content and status fields.
               Each todo should have: {"content": "task description", "status": "pending|in_progress|completed"}

    Returns:
        Formatted todo list that will be shown to the user.

    Examples:
        >>> write_todos([{"content": "Calculate 2+2", "status": "in_progress"}])
        "📋 Agent Task List (0/1 complete):\\n  ⏳ Calculate 2+2"

        >>> write_todos([
        ...     {"content": "Create table", "status": "completed"},
        ...     {"content": "Add data", "status": "in_progress"},
        ...     {"content": "Generate report", "status": "pending"}
        ... ])
        "📋 Agent Task List (1/3 complete):\\n  ✅ Create table\\n  ⏳ Add data\\n  ⏳ Generate report"
    """
    if not todos:
        return ""

    # Count completed tasks
    completed = sum(1 for t in todos if t.get("status") == "completed")
    total = len(todos)

    # Format todo list
    lines = [f"📋 Agent Task List ({completed}/{total} complete):"]

    for todo in todos[:10]:  # Max 10 todos
        status = todo.get("status", "pending")
        content = todo.get("content", "")

        if status == "completed":
            lines.append(f"  ✅ {content}")
        elif status == "in_progress":
            lines.append(f"  ⏳ {content}")
        else:  # pending
            lines.append(f"  ⏳ {content}")

    if len(todos) > 10:
        remaining = len(todos) - 10
        lines.append(f"  ... and {remaining} more")

    return "\n".join(lines)
