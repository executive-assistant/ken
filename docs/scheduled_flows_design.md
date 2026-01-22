# Scheduled Flows System Design (APScheduler)

## Goal

Track and schedule **flows** (formerly “jobs”) in Postgres, and scan them on a schedule with APScheduler. The current implementation **archives** flows (no worker execution), but keeps the schema and scheduler in place for future orchestration.

## Current Behavior

- Flows are stored in Postgres in `scheduled_flows`.
- APScheduler runs every minute (second 0) to:
  - send due reminders
  - **execute due flows** (executor chains run in-process).

This keeps the data model intact while the worker system is off.

## Architecture

```
Executive Assistant
  ├─ reminder scheduler (APScheduler)
  └─ flow scheduler (APScheduler)

Postgres
  ├─ reminders
  └─ scheduled_flows
```

## Table Schema (Current)

```sql
CREATE TABLE scheduled_flows (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255) NOT NULL,
    worker_id INTEGER,
    name VARCHAR(255),
    task TEXT NOT NULL,
    flow TEXT NOT NULL,
    due_time TIMESTAMP NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    cron VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    result TEXT
);
```

## Scheduler Loop

1. Fetch due flows: `status = 'pending' AND due_time <= now`.
2. Execute each flow chain (executor specs).

## Notes

- Recurrence (`cron`) is kept for compatibility with future orchestration.
- This design intentionally avoids executing arbitrary worker code while the worker/orchestrator system is paused.

