# Heartbeat Plan (Executive Assistant)

## Goal
Add a lightweight, configurable heartbeat that can run periodic checks and optionally send a brief update without interrupting active conversations.

## Behavior
- **Runs on schedule** (cron/interval) regardless of chat activity.
- **Suppresses output** if there’s nothing to report (e.g., returns `HEARTBEAT_OK`).
- **Avoids interrupting active chats** by:
  - delaying send if user is actively typing or within a recent activity window
  - optionally routing to a preferred channel

## Configuration (Suggested)
- `heartbeat.enabled` (default: false)
- `heartbeat.every` (e.g., "30m")
- `heartbeat.activeHours` (e.g., "08:00-20:00")
- `heartbeat.idleMinutes` (minimum inactivity before sending)
- `heartbeat.target` (last channel | specific channel | none)
- `heartbeat.prompt` (short system prompt for checkups)

## Execution Flow
1) Scheduler triggers heartbeat
2) Check active hours + idleMinutes
3) Run heartbeat prompt
4) If response is `HEARTBEAT_OK`, do nothing
5) Else, send a short update to target channel

## Implementation Plan
1) Add heartbeat settings to config
2) Add a scheduler job (interval/cron)
3) Implement heartbeat run in agent runtime
4) Add activity tracking to suppress sends during active chat
5) Add `/heartbeat` commands to enable/disable/inspect

## Success Criteria
- Heartbeat runs without user complaints
- No spam: sends only when there is useful output
- Respects idle window and quiet hours
