# Workflow Design: APScheduler + Postgres (Scheduled Flows)

## Goal

Keep a lightweight, durable workflow/flow scheduler without introducing Temporal. Store **flows** in Postgres and use **APScheduler** to scan and act on them. This aligns with the current runtime and avoids a separate orchestration stack.

## Current Implementation (as of Jan 2026)

- **Storage**: `scheduled_flows` table in Postgres.
- **Scheduler**: APScheduler runs every minute (second 0).
- **Behavior**:
  - Reminders are sent normally.
  - **Flows are executed**: due flows run executor chains in-process (APScheduler).

This keeps the schema and scheduler active while preventing execution of worker chains.

## Feasibility

- **High**: APScheduler already exists and runs in the app runtime.
- **Low operational overhead**: no extra services.
- **Durability**: Postgres holds state.

## Implementation Complexity

- **Low/Medium**:
  - Rename scheduled flows → flows across code/tests/docs.
  - Maintain schema and CRUD in `scheduled_flows` storage module.
  - Scheduler polling logic is simple (select due flows, execute executor chains).

## Tests

Recommended coverage:
- Postgres integration: `scheduled_flows` table exists.
- CRUD: create/list/update status for flows (already mirrored from former jobs tests).
- Scheduler: due flows execute executor chains (mock DB or integration).

## Verdict

**Proceed with APScheduler + Postgres flows.**

- It is feasible and matches current architecture.
- It avoids the complexity of Temporal while keeping an upgrade path.
- If we later add a dedicated orchestrator, we can swap in that runner behind the same scheduler.

## Next Steps (If/When Re-enabling Flows)

- Define safe worker execution boundaries.
- Reintroduce flow execution pipeline (orchestrator/worker).
- Add per-flow retries, metrics, and observability.

