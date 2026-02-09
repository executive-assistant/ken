# System Meta-Patterns (Quick Reference)

Description: Overview of how the agent learns and adapts (full guide: `load_skill("system_patterns")`)

Tags: core, system, meta, memory, checkin

---

## Quick Overview

The agent improves over time through **system-level patterns** (unlike user-facing patterns in `common_patterns.md`).

### Key Patterns (Current Runtime)

| Pattern | Purpose | Learn More |
|---------|---------|------------|
| **4 Memory Pillars** | Persist user context and behavior state | `load_skill("system_patterns")` |
| **Check-In Loop** | Proactive nudges from journal + goals | `load_skill("system_patterns")` |
| **Token Budget** | Manage context efficiently | `load_skill("system_patterns")` |
| **Middleware Stack** | Execution order matters | Built-in, automatic |
| **Context Propagation** | ThreadContextMiddleware | Built-in, automatic |

---

## Four Memory Pillars

**Concept:** User state is persisted in thread-scoped SQLite stores.

```
Memory (mem.db): preferences/facts/profile/style/context
Journal (journal.db): activity and rollups over time
Goals (goals.db): goal state and progress
Instincts (instincts.db): learned trigger->action behavior
```

Check-ins use journal + goals to produce proactive follow-up messages.

All are active in current runtime.

---

## When to Use

**Load full guide (`load_skill("system_patterns")`) when:**
- Explaining persistence and personalization
- Tuning check-in behavior
- Debugging token usage
- Understanding middleware behavior
- Debugging thread context/tool-scoping issues

---

## Quick Decision Tree

```
Want to understand how agent learns?
└─→ Load `system_patterns` (full guide)

Need to combine tools for a task?
└─→ See `common_patterns.md` (user workflows)

Choosing storage (TDB vs ADB vs VDB)?
└─→ See `decision_tree.md`
```

---

## See Also

- `common_patterns.md` - User-facing workflow patterns
- `decision_tree.md` - Storage decision guide
- `quick_reference.md` - Tool reference
