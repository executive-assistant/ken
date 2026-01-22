# Flows: Executor Chain Design (Extracted)

Source: discussions/user-level-reminders-todos-notes-plan.md

## Feature 4: Workflows (Temporal - Multi-Step Automation)

### Concept

Workflows are **multi-agent automation chains**:
- **Each agent:** `create_agent()` with specific tools + prompt
- **Flow:** Sequential chain, previous output → next input
- **Scheduling:** Immediate, scheduled (due time), or recurring (cron)
- **Storage:** PostgreSQL `workflows` table + Temporal execution tracking

### Data Models

```python
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime

class AgentSpec(BaseModel):
    """Definition of a single agent (Temporal Activity)."""

    agent_id: str
    name: str
    description: str

    # Agent configuration
    model: str  # e.g., "gpt-4o", "gpt-4o-mini"
    tools: list[str]  # Tool names from Executive Assistant's registry
    system_prompt: str

    # Structured output schema
    output_schema: dict

    # Temporal activity configuration
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_backoff: int = 60

class WorkflowSpec(BaseModel):
    """Workflow definition (passed to Temporal)."""

    workflow_id: str
    name: str
    description: str

    # Chain of agents
    agents: list[AgentSpec]

    # Scheduling
    schedule_type: Literal["immediate", "scheduled", "recurring"]
    schedule_time: Optional[datetime] = None
    cron_expression: Optional[str] = None

    # Notification
    notify_on_complete: bool = False
    notify_on_failure: bool = True
    notification_channel: Literal["telegram", "email", "web", "none"] = "telegram"
```

### Temporal Workflow (Multi-Step)

```python
"""src/executive_assistant/temporal_workflows.py"""

@workflow.defn
class Executive AssistantWorkflow:
    """Multi-step workflow that executes a chain of agents."""

    @workflow.run
    async def run(self, spec: WorkflowSpec) -> dict:
        """Execute the workflow agent by agent."""

        # Calculate delay if scheduled
        if spec.schedule_type == "scheduled" and spec.schedule_time:
            delay = (spec.schedule_time - datetime.now()).total_seconds()
            if delay > 0:
                await workflow.sleep(timedelta(seconds=delay))

        # Shared context across agents
        agent_outputs = {}
        results = []

        # Execute each agent as an activity
        for i, agent_spec in enumerate(spec.agents):
            try:
                # Execute the activity with retry policy
                output = await workflow.execute_activity(
                    run_agent_activity,
                    args=[agent_spec, agent_outputs],
                    retry_policy=RetryPolicy(
                        max_attempts=agent_spec.max_retries,
                        initial_retry=timedelta(seconds=agent_spec.retry_backoff)
                    ),
                    start_to_close_timeout=timedelta(seconds=agent_spec.timeout_seconds)
                )

                # Store output for next agent
                agent_outputs[agent_spec.agent_id] = output
                results.append({
                    "agent_id": agent_spec.agent_id,
                    "status": "success",
                    "output": output
                })

            except Exception as e:
                # Activity failed after retries
                results.append({
                    "agent_id": agent_spec.agent_id,
                    "status": "failed",
                    "error": str(e)
                })

                # Notify on failure if requested
                if spec.notify_on_failure:
                    await workflow.execute_activity(
                        send_notification_activity,
                        args=[spec.notification_channel, f"Workflow failed: {spec.name}"]
                    )

                raise  # Stop workflow execution

        # All agents completed successfully
        if spec.notify_on_complete:
            await workflow.execute_activity(
                send_notification_activity,
                args=[spec.notification_channel, f"Workflow completed: {spec.name}"]
            )

        return {
            "workflow_id": spec.workflow_id,
            "status": "completed",
            "agent_results": results
        }


@activity.defn
def run_agent_activity(agent_spec: AgentSpec, previous_outputs: dict) -> dict:
    """Execute a single agent (agent with tools)."""
    from executive_assistant.tools.registry import get_tools_by_name

    # Build prompt with previous outputs
    prompt = agent_spec.system_prompt
    if previous_outputs:
        prompt = prompt.replace(
            "$previous_output",
            json.dumps(previous_outputs, indent=2)
        )

    # Get tools for this agent
    tools = get_tools_by_name(agent_spec.tools)

    # Create and invoke the agent
    from langchain.agents import create_agent
    from langchain_core.messages import HumanMessage

    agent = create_agent(
        model=agent_spec.model,
        tools=tools,
        prompt=prompt
    )

    result = await agent.ainvoke({
        "messages": [HumanMessage(content="Execute your task.")]
    })

    # Extract and validate structured output
    structured_output = extract_structured_output(
        result,
        agent_spec.output_schema
    )

    return structured_output


@activity.defn
def send_notification_activity(channel: str, message: str) -> bool:
    """Send notification to user via specified channel."""
    if channel == "telegram":
        # Send via Telegram
        pass
    elif channel == "email":
        # Send via email
        pass
    return True
```

### Example: Price Monitoring Workflow

```python
workflow_spec = {
    "workflow_id": "daily_price_monitor",
    "name": "Daily Competitor Price Monitor",
    "description": "Check competitor prices and alert on changes",

    "agents": [
        {
            "agent_id": "fetch_prices",
            "name": "Price Fetcher",
            "model": "gpt-4o-mini",
            "tools": ["search_web"],
            "system_prompt": """Fetch prices for:
- Apple iPhone 15 Pro
- Samsung Galaxy S24

Search Amazon and Walmart. Return JSON:
{
    "prices": [
        {"product": "str", "competitor": "str", "price": "float", "url": "str"}
    ]
}""",
            "output_schema": {
                "prices": [{"product": "str", "competitor": "str", "price": "float", "url": "str"}]
            }
        },
        {
            "agent_id": "compare_prices",
            "name": "Price Comparator",
            "model": "gpt-4o",
            "tools": ["query_db"],
            "system_prompt": """Previous output: $previous_output

Compare with historical data. Flag changes > 10%. Return:
{
    "alerts": [
        {"product": "str", "old_price": "float", "new_price": "float", "change_percent": "float"}
    ],
    "summary": "str"
}""",
            "output_schema": {
                "alerts": [{"product": "str", "old_price": "float", "new_price": "float", "change_percent": "float"}],
                "summary": "str"
            }
        },
        {
            "agent_id": "send_alerts",
            "name": "Alert Sender",
            "model": "gpt-4o-mini",
            "tools": ["send_message"],
            "system_prompt": """Previous output: $previous_output

Send message with summary. Return:
{
    "status": "str",
    "message_count": "int"
}""",
            "output_schema": {"status": "str", "message_count": "int"}
        }
    ],

    "schedule_type": "recurring",
    "cron_expression": "0 9 * * MON-FRI",  # Weekdays at 9am
    "notify_on_complete": False,
    "notify_on_failure": True
}
```

### Workflow Tools

```python
"""src/executive_assistant/tools/workflow_tools.py"""

from temporalio.client import Client

@tool
async def create_workflow(
    name: str,
    description: str,
    agents: list[dict],
    schedule_type: str = "immediate",
    schedule_time: str = None,
    cron_expression: str = None,
    notify_on_complete: bool = False,
    notify_on_failure: bool = True,
    notification_channel: str = "telegram"
) -> str:
    """Create a workflow from a chain of agents (backed by Temporal).

    Each agent is a create_agent() with:
    - agent_id: Unique ID
    - name: Display name
    - model: Which LLM to use
    - tools: List of tool names
    - system_prompt: What this agent does (use $previous_output for injection)
    - output_schema: Expected structured output (JSON schema)

    Args:
        name: Workflow name
        description: What this workflow does
        agents: List of agent specifications
        schedule_type: 'immediate', 'scheduled', or 'recurring'
        schedule_time: For 'scheduled', when to run (natural language or ISO datetime)
        cron_expression: For 'recurring', cron like "0 9 * * MON-FRI"
        notify_on_complete: Send notification when workflow completes
        notify_on_failure: Send notification when workflow fails
        notification_channel: 'telegram', 'email', 'web', or 'none'

    Returns:
        workflow_id for tracking/cancellation

    Example:
        agents = [
            {
                "agent_id": "fetch",
                "name": "Fetcher",
                "model": "gpt-4o-mini",
                "tools": ["search_web"],
                "system_prompt": "Search for prices. Return JSON.",
                "output_schema": {"prices": [{"product": "str", "price": "float"}]}
            }
        ]
        await create_workflow("Price Monitor", agents, "recurring", cron_expression="0 9 * * *")
    """
    from datetime import datetime

    client = await Client.connect("temporal.vm2.internal:7233")

    # Parse schedule time if provided
    parsed_time = None
    if schedule_time:
        parsed_time = parse_natural_time(schedule_time)

    # Build WorkflowSpec
    spec = WorkflowSpec(
        workflow_id=str(uuid.uuid4()),
        name=name,
        description=description,
        agents=[AgentSpec(**e) for e in agents],
        schedule_type=schedule_type,
        schedule_time=parsed_time,
        cron_expression=cron_expression,
        notify_on_complete=notify_on_complete,
        notify_on_failure=notify_on_failure,
        notification_channel=notification_channel
    )

    # Save to PostgreSQL
    db_id = await save_workflow_to_db(spec)

    # Start Temporal workflow
    if spec.schedule_type == "immediate":
        handle = await client.start_workflow(
            Executive AssistantWorkflow.run,
            args=[spec],
            id=f"workflow-{spec.workflow_id}",
            task_queue="executive_assistant-workflows"
        )
    elif spec.schedule_type == "scheduled":
        delay_seconds = (spec.schedule_time - datetime.now()).total_seconds()
        handle = await client.start_workflow(
            Executive AssistantWorkflow.run,
            args=[spec],
            id=f"workflow-{spec.workflow_id}",
            task_queue="executive_assistant-workflows",
            start_delay=timedelta(seconds=delay_seconds)
        )
    elif spec.schedule_type == "recurring":
        handle = await client.start_workflow(
            Executive AssistantRecurringWorkflow.run,
            args=[spec],
            id=f"workflow-{spec.workflow_id}-cron",
            task_queue="executive_assistant-workflows",
            cron_expression=spec.cron_expression
        )

    return spec.workflow_id


@tool
async def list_workflows(status: str = None) -> str:
    """List your workflows.

    Args:
        status: Filter by 'active', 'paused', or 'archived'

    Returns:
        List of workflows with scheduling info.
    """
    workflows = await get_workflows_by_user(get_workspace_id(), status)

    if not workflows:
        return "No workflows found."

    lines = [f"{'ID':<10} {'Name':<25} {'Schedule':<20} {'Status'}"]
    lines.append("-" * 80)

    for wf in workflows:
        schedule = f"{wf['schedule_type']}"
        if wf.get('cron_expression'):
            schedule = f"{wf['cron_expression']}"
        elif wf.get('schedule_time'):
            schedule = f"{wf['schedule_time']}"
        lines.append(f"{wf['workflow_id']:<10} {wf['name']:<25} {schedule:<20} {wf['status']}")

    return "\n".join(lines)


@tool
async def cancel_workflow(workflow_id: str) -> str:
    """Cancel a workflow.

    Args:
        workflow_id: Workflow ID from create_workflow

    Returns:
        Cancellation status.
    """
    client = await Client.connect("temporal.vm2.internal:7233")
    handle = client.get_workflow_handle(f"workflow-{workflow_id}")
    await handle.cancel()

    await set_workflow_status(workflow_id, "paused")
    return f"Cancelled workflow {workflow_id}"
```

---
