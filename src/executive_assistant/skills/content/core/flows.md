# Flows (Scheduled/Immediate Multi-Step Runs)

Use flows when you want the assistant to execute a structured sequence of steps now or on a schedule. Flows do **not** require MCP.

## Flow tools
- `create_flow(...)`
- `list_flows(status=None)`
- `run_flow(flow_id)`
- `cancel_flow(flow_id)`
- `delete_flow(flow_id)`

## AgentSpec (required fields)
Each agent in a flow must include all required fields:
- `agent_id` (string)
- `description` (string)
- `model` (string)
- `tools` (list of tool names)
- `system_prompt` (string)

## Minimal example (immediate)
```json
{
  "name": "test_flow",
  "description": "Test flow",
  "schedule_type": "immediate",
  "agents": [
    {
      "agent_id": "runner_1",
      "description": "Run a quick python snippet",
      "model": "gpt-oss:20b",
      "tools": ["execute_python"],
      "system_prompt": "You are a lightweight flow agent. Run the code and return its output."
    }
  ],
  "run_mode": "normal"
}
```

## Scheduled example (cron)
```json
{
  "name": "daily_brief",
  "description": "Daily 9am summary",
  "schedule_type": "cron",
  "cron_expression": "0 9 * * *",
  "agents": [
    {
      "agent_id": "summarizer",
      "description": "Summarize updates",
      "model": "gpt-oss:20b",
      "tools": ["query_db", "search_vs", "write_file"],
      "system_prompt": "Summarize key updates from DB and VS, write to a report file."
    }
  ],
  "run_mode": "normal"
}
```

## Notes
- If flow creation fails with missing AgentSpec fields, add the missing fields above.
- Flow agents cannot call flow tools (no nesting).
