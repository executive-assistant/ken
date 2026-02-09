# System Patterns

Description: Runtime architecture patterns for memory, personalization, check-ins, and execution safety.

Tags: core, system, meta, memory, checkin, middleware

---

## Overview

These are system-level patterns (not user task workflows). They explain how the assistant stores context over time, adapts behavior, and runs safely across channels.

---

## Pattern 1: Four Memory Pillars

The assistant uses four persistent, thread-scoped pillars:

| Pillar | Purpose | Storage |
|------|---------|---------|
| **Memory** | user preferences, facts, constraints, style/context | `data/users/{thread_id}/mem/mem.db` |
| **Journal** | time-based activity log and rollups | `data/users/{thread_id}/journal/journal.db` |
| **Goals** | goal state, progress updates, milestones | `data/users/{thread_id}/goals/goals.db` |
| **Instincts** | learned trigger -> action behavior rules | `data/users/{thread_id}/instincts/instincts.db` |

Primary tools by pillar:
- Memory: `create_memory`, `get_memory_by_key`, `search_memories`, `normalize_or_create_memory`
- Goals: `create_goal`, `list_goals`, `update_goal`
- Instincts: `create_instinct`, `list_instincts`, `get_applicable_instincts`, `adjust_instinct_confidence`
- Journal: internal runtime subsystem (not a public user toolset yet)

Memory type values are:
- `profile`, `fact`, `preference`, `constraint`, `style`, `context`

Correct example:
```python
create_memory(
    content="User prefers concise replies.",
    memory_type="preference",
    key="response_style"
)
```

---

## Pattern 2: Check-In Loop

Check-in is proactive monitoring that analyzes recent journal + goals and nudges only when needed.

Core check-in tools:
- `checkin_enable(every, lookback)`
- `checkin_disable()`
- `checkin_show()`
- `checkin_schedule(every)`
- `checkin_hours(start, end, days)`
- `checkin_test()`

Operational flow:
1. User enables check-in with cadence and lookback.
2. Scheduler runs check-ins in active windows.
3. Runner evaluates journal activity and goal health.
4. Assistant sends a concise proactive message only for meaningful findings.

---

## Pattern 3: Token Budget Management

Context is dynamically trimmed to keep turns reliable under larger histories.

Main mechanisms:
- Summarization middleware compresses long history while preserving decisions and state.
- Context-edit middleware removes redundant tool traces.
- Retrieval prioritizes high-value memories over low-signal records.

---

## Pattern 4: Middleware Stack Order

Middleware order affects behavior:
- Thread context first, so tools receive the correct `thread_id`.
- Todo/status middlewares for progress visibility.
- Summarization/context editing later for prompt efficiency.

If order is wrong, you can get missing context, noisy prompts, or stale status behavior.

---

## Pattern 5: Context Propagation

`ContextVar` state can be lost across async boundaries unless it is explicitly preserved.

The runtime preserves thread context before and after tool execution so thread-scoped storage (mem/goals/instincts/files) stays isolated per user conversation.

---

## Quick Reference

| Pattern | Purpose | Status |
|---------|---------|--------|
| **Four Memory Pillars** | Persistent personalization + state | Active |
| **Check-In Loop** | Proactive follow-up from journal/goals | Active |
| **Token Budget** | Context control and stability | Active |
| **Middleware Stack** | Correct execution semantics | Active |
| **Context Propagation** | Thread-safe tool execution | Active |

---

## See Also

- `common_patterns.md` - User-facing workflow patterns
- `quick_reference.md` - Tool inventory
- `decision_tree.md` - Storage decision guide
