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

## Important
- There is no separate create_agent tool. Define agents inline in the flow using AgentSpec.
- If create_flow fails with missing fields, supply all required AgentSpec fields listed above.

## Notes
- schedule_type aliases: `once` → `scheduled`, `cron` → `recurring`.
- If flow creation fails with missing AgentSpec fields, add the missing fields above.
- Flow agents cannot call flow tools (no nesting).


## Examples (progressive)

### 1) Single-step, immediate
```json
{
  "name": "ping",
  "description": "Quick sanity run",
  "schedule_type": "immediate",
  "agents": [
    {
      "agent_id": "ping_agent",
      "description": "Return a short confirmation",
      "model": "gpt-oss:20b",
      "tools": [],
      "system_prompt": "Reply with a brief OK and current date."
    }
  ],
  "run_mode": "normal"
}
```

### 2) Single-step, scheduled (cron)
```json
{
  "name": "daily_checkin",
  "description": "Daily status note",
  "schedule_type": "cron",
  "cron_expression": "0 9 * * *",
  "agents": [
    {
      "agent_id": "checkin",
      "description": "Create a short check-in note",
      "model": "gpt-oss:20b",
      "tools": ["write_file"],
      "system_prompt": "Write a 3-bullet daily check-in and save to files/daily_checkin.md."
    }
  ],
  "run_mode": "normal"
}
```



### 2b) Single-step, one-off at a specific time
```json
{
  "name": "one_off_reminder_flow",
  "description": "Run once at a specific time",
  "schedule_type": "once",
  "schedule_time": "2026-02-01 09:30",
  "agents": [
    {
      "agent_id": "notifier",
      "description": "Write a quick note",
      "model": "gpt-oss:20b",
      "tools": ["write_file"],
      "system_prompt": "Write a short note to files/one_off_note.md."
    }
  ],
  "run_mode": "normal"
}
```

### 3) Two-step, immediate (handoff)
```json
{
  "name": "summary_and_report",
  "description": "Summarize DB data and write a report",
  "schedule_type": "immediate",
  "agents": [
    {
      "agent_id": "summarizer",
      "description": "Summarize DB data",
      "model": "gpt-oss:20b",
      "tools": ["query_db"],
      "system_prompt": "Query key tables and return a concise summary in JSON with fields: summary, highlights."
    },
    {
      "agent_id": "writer",
      "description": "Write report",
      "model": "gpt-oss:20b",
      "tools": ["write_file"],
      "system_prompt": "Use the previous agent JSON to write a markdown report to files/report.md."
    }
  ],
  "run_mode": "normal"
}
```

### 4) Multi-step with web + VS + file output
```json
{
  "name": "weekly_market_watch",
  "description": "Collect, store, and summarize weekly market notes",
  "schedule_type": "cron",
  "cron_expression": "0 8 * * 1",
  "agents": [
    {
      "agent_id": "collector",
      "description": "Search and collect notes",
      "model": "gpt-oss:20b",
      "tools": ["search_web", "create_vs_collection", "add_vs_documents"],
      "system_prompt": "Find 3 relevant articles, extract key points, and store them in VS collection weekly_notes."
    },
    {
      "agent_id": "summarizer",
      "description": "Summarize stored notes",
      "model": "gpt-oss:20b",
      "tools": ["search_vs", "write_file"],
      "system_prompt": "Query weekly_notes and write a 1-page summary to files/weekly_summary.md."
    }
  ],
  "run_mode": "normal"
}
```


## Troubleshooting
- If the assistant says an agent must be registered first, that is incorrect for this system. Agents are defined inline in `create_flow`.
- If you see “Field required” errors, it means one or more AgentSpec fields are missing. Provide all of:
  `agent_id`, `description`, `model`, `tools`, `system_prompt`.
- There is no create_agent tool.


### AgentSpec is part of create_flow
When calling `create_flow`, you MUST include `agents` inline. There is no separate agent registry step. The AgentSpec fields belong inside the `create_flow` payload.

Example snippet:
```json
{
  "name": "my_flow",
  "description": "Demo",
  "schedule_type": "immediate",
  "agents": [
    {
      "agent_id": "demo_agent",
      "description": "Do the task",
      "model": "gpt-oss:20b",
      "tools": ["execute_python"],
      "system_prompt": "Run the task and return the output."
    }
  ]
}
```
