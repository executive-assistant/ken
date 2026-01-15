"""Orchestrator tools for spawning workers and scheduling jobs.

The Orchestrator is a specialized agent that:
1. Receives task & flow descriptions from Cassey
2. Spawns worker agents with appropriate tools
3. Schedules jobs at specific times (with cron support)
4. Manages job lifecycle

Workers are task-specific agents that execute the actual work.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, tool
from langchain_core.runnables import RunnableConfig

from cassey.config import create_model
from cassey.config.settings import settings
from cassey.storage.file_sandbox import get_thread_id, set_thread_id
from cassey.storage.scheduled_jobs import ScheduledJob, get_scheduled_job_storage
from cassey.storage.workers import Worker, get_worker_storage
from cassey.tools.registry import get_all_tools

logger = logging.getLogger(__name__)

# ============================================================================
# Cron Expression Utilities
# ============================================================================


def parse_cron_next(cron: str, after: datetime) -> datetime:
    """Calculate next run time from a cron expression.

    Supports standard 5-field cron: minute hour day month weekday
    Also supports common shortcuts:
    - "@hourly" or "hourly" -> every hour
    - "@daily" or "daily" or "0 0 * * *" -> every day at midnight
    - "@weekly" or "weekly" or "0 0 * * 0" -> every week at midnight Sunday
    - "@monthly" or "monthly" or "0 0 1 * *" -> every month on 1st at midnight
    - "daily at 9am" -> daily at 9am
    - "daily at 9pm" -> daily at 9pm

    Args:
        cron: Cron expression or shortcut
        after: Calculate next time after this datetime

    Returns:
        Next run datetime

    Raises:
        ValueError: If cron expression is invalid
    """
    now = after

    # Handle shortcuts
    cron_lower = cron.lower().strip()
    if cron_lower in ("@hourly", "hourly"):
        return now + timedelta(hours=1)
    if cron_lower in ("@daily", "daily"):
        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    if cron_lower in ("@weekly", "weekly"):
        # Next Sunday at midnight
        days_ahead = 6 - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_week = now + timedelta(days=days_ahead)
        return next_week.replace(hour=0, minute=0, second=0, microsecond=0)
    if cron_lower in ("@monthly", "monthly"):
        # Next month on 1st at midnight
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)
        return next_month.replace(hour=0, minute=0, second=0, microsecond=0)

    # Handle "daily at 9am" / "daily at 9pm" format
    match = re.match(r"daily\s+at\s+(\d{1,2})(:(\d{2}))?\s*(am|pm)?", cron_lower)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(3)) if match.group(3) else 0
        meridiem = match.group(4)
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0

        result = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if result <= now:
            result = result + timedelta(days=1)
        return result

    # Remove @ prefix if present
    if cron_lower.startswith("@"):
        cron_lower = cron_lower[1:]

    # Parse standard 5-field cron
    # Format: minute hour day month weekday
    parts = cron_lower.strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"Invalid cron expression '{cron}'. "
            "Expected 5 fields (minute hour day month weekday) or a shortcut."
        )

    minute_part, hour_part, day_part, month_part, weekday_part = parts

    # For simplicity, handle common patterns
    # This is a basic implementation - for full cron support, use croniter

    try:
        # Handle "0 9 * * *" (daily at 9am)
        if minute_part == "0" and hour_part.isdigit() and day_part == "*" and month_part == "*" and weekday_part == "*":
            hour = int(hour_part)
            if hour < 0 or hour > 23:
                raise ValueError("Hour must be 0-23")
            result = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if result <= now:
                result = result + timedelta(days=1)
            return result

        # Handle "0 */6 * * *" (every 6 hours)
        if minute_part == "0" and hour_part.startswith("*/") and day_part == "*" and month_part == "*" and weekday_part == "*":
            interval = int(hour_part[2:])
            if interval < 1 or interval > 23:
                raise ValueError("Hour interval must be 1-23")
            result = now.replace(minute=0, second=0, microsecond=0)
            # Find next interval
            current_hour = result.hour
            # Calculate hours to add to reach next interval
            hours_to_add = (interval - (current_hour % interval)) % interval
            if hours_to_add == 0 and result <= now:
                hours_to_add = interval
            result = result + timedelta(hours=hours_to_add)
            return result

        # Handle "*/30 * * * *" (every 30 minutes)
        if minute_part.startswith("*/") and hour_part == "*" and day_part == "*" and month_part == "*" and weekday_part == "*":
            interval = int(minute_part[2:])
            if interval < 1 or interval > 59:
                raise ValueError("Minute interval must be 1-59")
            result = now.replace(second=0, microsecond=0)
            # Round up to next interval
            minute = (result.minute // interval + 1) * interval
            if minute >= 60:
                result = result + timedelta(hours=1)
                minute = 0
            result = result.replace(minute=minute)
            if result <= now:
                result = result + timedelta(minutes=interval)
            return result

        # Handle "0 9 * * 1-5" (daily at 9am, weekdays only)
        if (
            minute_part == "0"
            and hour_part.isdigit()
            and day_part == "*"
            and month_part == "*"
            and "-" in weekday_part
        ):
            hour = int(hour_part)
            result = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            # Find next weekday
            while True:
                result = result + timedelta(days=1)
                if result.weekday() < 5:  # Monday=0, Friday=4
                    return result

        # Default: add 1 day (fallback)
        logger.warning(f"Cron pattern '{cron}' not fully supported, treating as daily")
        return (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)

    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid cron expression '{cron}': {e}") from e


def validate_tools(tool_names: list[str], available_tools: dict[str, BaseTool]) -> list[str]:
    """Validate that requested tool names exist.

    Args:
        tool_names: List of tool names to validate
        available_tools: Dictionary of available tools

    Returns:
        List of valid tool names

    Raises:
        ValueError: If any tool name is invalid
    """
    invalid = [name for name in tool_names if name not in available_tools]
    if invalid:
        raise ValueError(f"Unknown tool names: {invalid}. Available tools: {list(available_tools.keys())}")
    return tool_names


# ============================================================================
# Orchestrator Tools (used by the Orchestrator agent)
# ============================================================================


@tool
async def spawn_worker(name: str, tools: str, prompt: str) -> str:
    """Create a new worker agent for a specific task.

    Only the Orchestrator can spawn workers. Workers cannot spawn other workers.

    Args:
        name: Name for this worker (e.g., "price_checker")
        tools: Comma-separated list of tool names (e.g., "web_search,execute_python")
        prompt: System prompt defining the worker's behavior

    Returns:
        Confirmation message with worker ID

    Examples:
        >>> await spawn_worker("price_checker", "web_search,execute_python",
        ...              "You check prices and alert when under threshold")
        "Worker 'price_checker' created with ID 123"
    """
    # Get context
    thread_id = get_thread_id()
    if not thread_id:
        return "Error: No thread_id context. Cannot spawn worker."

    # Parse tools
    tool_names = [t.strip() for t in tools.split(",") if t.strip()]

    # Get user_id from thread_id (format: "channel:user_id" or "channel:user_id:thread")
    parts = thread_id.split(":")
    user_id = parts[1] if len(parts) > 1 else thread_id

    # Validate tools against available tools
    try:
        all_tools_dict = {t.name: t for t in await get_all_tools()}
        validated = validate_tools(tool_names, all_tools_dict)
        storage = await get_worker_storage()
        worker = await storage.create(
            user_id=user_id,
            thread_id=thread_id,
            name=name,
            tools=validated,
            prompt=prompt,
        )
        return f"Worker '{name}' created with ID {worker.id} and tools: {', '.join(validated)}"
    except ValueError as e:
        return f"Error creating worker: {e}"
    except Exception as e:
        return f"Error creating worker: {e}"


@tool
async def schedule_job(
    name: str,
    task: str,
    flow: str,
    schedule: str,
    worker_id: int | None = None,
) -> str:
    """Schedule a job to run at a specific time.

    Args:
        name: Name for this job
        task: Concrete task description (e.g., "Check Amazon price for B08X12345")
        flow: Execution flow with conditions/loops (e.g., "fetch → if < $100 notify")
        schedule: When to run. Cron expression (e.g., "0 9 * * *") or:
            - "hourly" or "@hourly"
            - "daily" or "@daily" or "daily at 9am"
            - "weekly" or "@weekly"
            - "monthly" or "@monthly"
            - Cron: "minute hour day month weekday"
        worker_id: Optional worker ID to execute the job

    Returns:
        Confirmation message with job ID and scheduled time

    Examples:
        >>> await schedule_job("daily_price", "Check price", "fetch and alert", "daily at 9am")
        "Job 'daily_price' scheduled for 2025-01-16 09:00:00 with ID 456"
    """
    thread_id = get_thread_id()
    if not thread_id:
        return "Error: No thread_id context. Cannot schedule job."

    # Get user_id from thread_id
    parts = thread_id.split(":")
    user_id = parts[1] if len(parts) > 1 else thread_id

    # Parse schedule
    try:
        # Parse the schedule string
        cron_expr = schedule
        # Handle "daily at 9am" format
        match = re.match(r"daily\s+at\s+(\d{1,2}):(\d{2})", schedule.lower())
        if match:
            hour, minute = match.groups()
            cron_expr = f"{minute} {hour} * * *"
        elif "daily at" in schedule.lower():
            # Extract time like "9am" or "9:00am"
            time_match = re.search(r"(\d{1,2}):(\d{2})?\s*(am|pm)?", schedule.lower())
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                meridiem = time_match.group(3)
                if meridiem == "pm" and hour < 12:
                    hour += 12
                elif meridiem == "am" and hour == 12:
                    hour = 0
                cron_expr = f"{minute} {hour} * * *"
            else:
                cron_expr = "0 9 * * *"  # Default to 9am
        elif "hourly" in schedule.lower():
            cron_expr = "hourly"
        elif "weekly" in schedule.lower():
            cron_expr = "weekly"
        elif "monthly" in schedule.lower():
            cron_expr = "monthly"

        # Calculate due time
        now = datetime.now()
        if cron_expr == "now" or cron_expr == "immediately":
            due_time = now + timedelta(seconds=5)  # Small delay for processing
        else:
            due_time = parse_cron_next(cron_expr, now)

        storage = await get_scheduled_job_storage()
        job = await storage.create(
            user_id=user_id,
            thread_id=thread_id,
            task=task,
            flow=flow,
            due_time=due_time,
            worker_id=worker_id,
            name=name,
            cron=cron_expr,
        )
        return (
            f"Job '{name}' scheduled for {due_time.strftime('%Y-%m-%d %H:%M:%S')} "
            f"with ID {job.id} (cron: {cron_expr})"
        )
    except ValueError as e:
        return f"Error scheduling job: {e}"
    except Exception as e:
        return f"Error scheduling job: {e}"


@tool
async def list_jobs(status: str = "") -> str:
    """List scheduled jobs for the current thread.

    Args:
        status: Optional status filter (pending, running, completed, failed, cancelled)

    Returns:
        Formatted list of jobs

    Examples:
        >>> await list_jobs()
        "Jobs:\n1. daily_price (pending) at 2025-01-16 09:00:00\n..."

        >>> await list_jobs("pending")
        "Pending jobs:\n1. daily_price..."
    """
    thread_id = get_thread_id()
    if not thread_id:
        return "Error: No thread_id context."

    try:
        storage = await get_scheduled_job_storage()
        jobs = await storage.list_by_thread(thread_id, status or None)

        if not jobs:
            status_str = status or "all"
            return f"No {status_str} jobs found for this thread."

        lines = [f"Jobs for {thread_id}:"]
        for job in jobs:
            status_emoji = {
                "pending": "⏳",
                "running": "▶️",
                "completed": "✅",
                "failed": "❌",
                "cancelled": "🚫",
            }.get(job.status, "❓")

            lines.append(
                f"  {status_emoji} {job.name or f'Job {job.id}'} "
                f"({job.status}) at {job.due_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            lines.append(f"      Task: {job.task[:80]}...")

            if job.error_message:
                lines.append(f"      Error: {job.error_message}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error listing jobs: {e}"


@tool
async def cancel_job(job_id: int) -> str:
    """Cancel a pending scheduled job.

    Args:
        job_id: ID of the job to cancel

    Returns:
        Confirmation message

    Examples:
        >>> await cancel_job(456)
        "Job 456 cancelled"
    """
    thread_id = get_thread_id()
    if not thread_id:
        return "Error: No thread_id context."

    try:
        storage = await get_scheduled_job_storage()
        success = await storage.cancel(job_id)
        if success:
            return f"Job {job_id} cancelled"
        else:
            return f"Job {job_id} not found or not in pending status"
    except Exception as e:
        return f"Error cancelling job: {e}"


# ============================================================================
# Orchestrator Agent
# ============================================================================

ORCHESTRATOR_SYSTEM_PROMPT = """You are an Orchestrator specializing in task automation and scheduling.

Your responsibilities:
- Understand the user's task and flow requirements
- Create appropriate workers with specific tools and prompts
- Set up schedules (daily, hourly, weekly, monthly, or cron expressions)
- Handle job dependencies and workflows
- Report back clearly what you've set up

When creating workers:
- Give them clear, descriptive names
- Provide specific prompts that define their behavior
- Only assign tools they actually need
- Consider error cases in your prompts

Available tools:
- spawn_worker(name, tools, prompt): Create a new worker
- schedule_job(name, task, flow, schedule, worker_id): Schedule execution
- list_jobs(status): Show all scheduled jobs
- cancel_job(job_id): Cancel a pending job

Schedule format examples:
- "daily at 9am" or "0 9 * * *" -> Every day at 9am
- "hourly" or "@hourly" -> Every hour
- "weekly" or "@weekly" -> Every week
- "monthly" or "@monthly" -> Every month
- "0 */6 * * *" -> Every 6 hours
- "*/30 * * * *" -> Every 30 minutes

You execute tasks efficiently. Report what you've done concisely."""


async def create_orchestrator_agent(model: BaseChatModel | None = None):
    """Create the Orchestrator agent.

    Args:
        model: Optional LLM model (defaults to create_model())

    Returns:
        Compiled agent graph for the Orchestrator
    """
    from cassey.agent.graph import create_graph

    if model is None:
        model = create_model()

    # Tools available to the Orchestrator
    orchestrator_tools = [
        spawn_worker,
        schedule_job,
        list_jobs,
        cancel_job,
    ]

    # Create the agent graph
    agent = create_graph(
        model=model,
        tools=orchestrator_tools,
        checkpointer=None,  # No checkpointer needed for stateless calls
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
    )

    return agent


async def invoke_orchestrator(
    message: str,
    thread_id: str,
    model: BaseChatModel | None = None,
) -> str:
    """Invoke the Orchestrator agent with a message.

    Args:
        message: User message/task for the Orchestrator
        thread_id: Thread ID for context
        model: Optional LLM model

    Returns:
        Orchestrator's response
    """
    # Set thread_id context for tools
    set_thread_id(thread_id)

    agent = await create_orchestrator_agent(model)

    # Create state
    state = {
        "messages": [HumanMessage(content=message)],
        "summary": "",
        "iterations": 0,
        "user_id": thread_id.split(":")[1] if ":" in thread_id else thread_id,
        "channel": "orchestrator",
    }

    # Create config (no checkpointer needed)
    config = RunnableConfig(configurable={"thread_id": f"orchestrator_{thread_id}"})

    # Invoke agent
    result = await agent.ainvoke(state, config)

    # Extract response
    messages = result.get("messages", [])
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, AIMessage):
            return last_message.content
        return str(last_message.content)

    return "Orchestrator: No response generated."


# ============================================================================
# Cassey's Tool: Delegate to Orchestrator
# ============================================================================

@tool
async def delegate_to_orchestrator(task: str, flow: str, schedule: str = "") -> str:
    """Delegate a complex task and flow to the Orchestrator.

    The Orchestrator will:
    - Create appropriate workers for the task
    - Set up schedules if needed
    - Handle dependencies and workflows

    NOTE: Requirements & goals should already be agreed with the user.
    This tool is for the actual execution plan.

    Args:
        task: Concrete task to execute (e.g., "Check Amazon price for B08X12345")
        flow: Execution flow with conditions/loops, e.g.:
            - "fetch price → if < $100 notify, else log to database"
            - "check API → if error retry 3x, else continue"
            - "for each product: fetch price → if < $100 add to alerts"
        schedule: Optional schedule (e.g., "daily at 9am", "hourly", "0 9 * * *")
            If empty, the Orchestrator will advise on scheduling.

    USE THIS FOR:
    - Recurring/automated tasks with clear execution flow
    - Multi-step workflows with dependencies
    - Tasks requiring specialized workers

    DO NOT USE FOR:
    - Simple one-off questions (use tools directly)
    - Gathering requirements (talk to user instead)

    Examples:
        >>> await delegate_to_orchestrator(
        ...     "Check Amazon price for B08X12345",
        ...     "fetch price → if < $100 send notification",
        ...     "daily at 9am"
        ... )
    """
    thread_id = get_thread_id()
    if not thread_id:
        return "Error: No thread_id context. Cannot delegate to Orchestrator."

    # Build the message for the Orchestrator
    if schedule:
        message = f"""Task: {task}

Flow: {flow}

Schedule: {schedule}

Please set up the appropriate workers and schedule for this task."""
    else:
        message = f"""Task: {task}

Flow: {flow}

Please advise on the best schedule and set up the appropriate workers."""

    try:
        # This is now an async function, so we can properly await
        return await asyncio.wait_for(invoke_orchestrator(message, thread_id), timeout=60)
    except asyncio.TimeoutError:
        logger.error(f"Timeout invoking Orchestrator after 60 seconds")
        return "Error delegating to Orchestrator: Operation timed out (60s)"
    except Exception as e:
        logger.error(f"Error invoking Orchestrator: {e}")
        return f"Error delegating to Orchestrator: {e}"


# ============================================================================
# Worker Execution
# ============================================================================

async def execute_worker(
    worker: Worker,
    task: str,
    flow: str,
    thread_id: str,
    timeout: int = 30,
) -> tuple[str, str | None]:
    """Execute a worker's task.

    Args:
        worker: The Worker instance to execute
        task: The task to execute
        flow: The execution flow
        thread_id: Thread context for execution
        timeout: Maximum execution time in seconds

    Returns:
        Tuple of (result: str, error: str | None)
    """
    from cassey.agent.graph import create_graph

    # Get the worker's assigned tools
    all_tools = await get_all_tools()
    all_tools_dict = {t.name: t for t in all_tools}
    worker_tools = [all_tools_dict[name] for name in worker.tools if name in all_tools_dict]

    # Create the worker agent
    model = create_model()
    worker_agent = create_graph(
        model=model,
        tools=worker_tools,
        checkpointer=None,
        system_prompt=worker.prompt,
    )

    # Build the task message
    task_message = f"""Task: {task}

Flow: {flow}

Execute this task now. Report your results clearly."""

    # Set thread_id context
    set_thread_id(thread_id)

    # Create state
    state = {
        "messages": [HumanMessage(content=task_message)],
        "summary": "",
        "iterations": 0,
        "user_id": worker.user_id,
        "channel": "worker",
    }

    config = RunnableConfig(configurable={"thread_id": f"worker_{worker.id}_{thread_id}"})

    # Execute with timeout
    try:
        result = await asyncio.wait_for(
            worker_agent.ainvoke(state, config),
            timeout=timeout,
        )

        # Extract response
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            if isinstance(last_message, AIMessage):
                return last_message.content, None
            return str(last_message.content), None

        return "Worker completed with no output", None

    except asyncio.TimeoutError:
        return None, f"Worker execution timed out after {timeout} seconds"
    except Exception as e:
        return None, f"Worker execution failed: {e}"


# ============================================================================
# Tool Getter
# ============================================================================

def get_orchestrator_tools() -> list[BaseTool]:
    """Get orchestrator-related tools for Cassey.

    Returns:
        List of tools including delegate_to_orchestrator
    """
    return [delegate_to_orchestrator]
