# Mini Agents & Flows Feature - Comprehensive Removal Plan

**Date:** 2026-02-11
**Purpose:** Complete removal of the mini agents & flows feature from the codebase

---

## Overview

The mini agents & flows feature allows creating scheduled/recurring workflows with multiple mini-agents. This plan removes all related code, storage, tests, documentation, and skills.

---

## Files to DELETE (Complete Removal)

### 1. Core Implementation Files

| File Path | Purpose |
|-----------|---------|
| `src/executive_assistant/tools/flow_tools.py` | Flow scheduling/execution tools (create_flow, list_flows, run_flow, cancel_flow, delete_flow) |
| `src/executive_assistant/tools/flow_project_tools.py` | Flow project workspace tools (create_flow_project) |
| `src/executive_assistant/tools/agent_tools.py` | Mini-agent CRUD tools (create_agent, list_agents, get_agent, update_agent, delete_agent, run_agent) |
| `src/executive_assistant/storage/agent_registry.py` | Storage backend for mini agents |
| `src/executive_assistant/storage/scheduled_flows.py` | Storage backend for scheduled flows |
| `src/executive_assistant/flows/runner.py` | Flow execution engine |
| `src/executive_assistant/flows/spec.py` | Flow specification models |
| `src/executive_assistant/agent/flow_mode.py` | Flow mode configuration (FLOW_MODE environment variable, /flow command) |

### 2. Skill Files

| File Path | Purpose |
|-----------|---------|
| `src/executive_assistant/skills/content/on_demand/flows/flows.md.disabled` | Flows & Agent Builder Guide skill (already disabled) |
| `src/executive_assistant/skills/content/on_demand/flows/` | Entire flows skills directory |

### 3. Test Files

| File Path | Purpose |
|-----------|---------|
| `tests/test_agent_tools.py` | Agent tools tests |
| `tests/test_agent.py` | Agent-related tests |
| `tests/test_flow_agent_registry.py` | Agent registry tests |
| `tests/test_flow_agent_runner.py` | Flow runner tests |
| `tests/test_flow_integration_stub.py` | Flow integration tests |
| `tests/test_flow_tools.py` | Flow tools tests |
| `tests/test_scheduled_flows.py` | Scheduled flows storage tests |

### 4. Documentation Files

| File Path | Purpose |
|-----------|---------|
| `docs/kb/gorules/flow-agents-integration.md` | Flow agents integration guide |
| `docs/kb/langchain/langgraph-multi-agents.md` | Multi-agent patterns (likely flows-related) |
| `docs/kb/langchain/langgraph_workflows_agents.md` | Workflow patterns (likely flows-related) |

---

## Files to MODIFY (Remove Flow References)

### 1. `src/executive_assistant/tools/registry.py`

**Line 285-294:** Remove `get_flow_tools()` function
```python
# DELETE this entire function:
async def get_flow_tools() -> list[BaseTool]:
    """Get flow scheduling/execution tools."""
    from executive_assistant.tools.flow_tools import (
        create_flow,
        list_flows,
        run_flow,
        cancel_flow,
        delete_flow,
    )
    return [create_flow, list_flows, run_flow, cancel_flow, delete_flow]
```

**Lines 365-390:** Remove commented-out flow/agent tools registration
```python
# DELETE these commented blocks:
# DISABLED: Flow tools - not production-ready yet
# all_tools.extend(await get_flow_tools())

# DISABLED: Agent tools - not production-ready yet
# from executive_assistant.tools.agent_tools import (
#     create_agent,
#     list_agents,
#     get_agent,
#     update_agent,
#     delete_agent,
#     run_agent,
# )
# all_tools.extend([create_agent, list_agents, get_agent, update_agent, delete_agent, run_agent])

# DISABLED: Flow project tools - not production-ready yet
# from executive_assistant.tools.flow_project_tools import create_flow_project
# all_tools.append(create_flow_project)
```

**Lines 472-484:** Remove flow mode conditional logic in `get_tools_for_request()`
```python
# DELETE this entire if block:
if flow_mode or _text_has_any(message_text, ["flow", "flows", "agent", "agents"]):
    from executive_assistant.tools.agent_tools import (
        create_agent,
        list_agents,
        get_agent,
        update_agent,
        delete_agent,
        run_agent,
    )
    tools.extend([create_agent, list_agents, get_agent, update_agent, delete_agent, run_agent])
    tools.extend(await get_flow_tools())
    from executive_assistant.tools.flow_project_tools import create_flow_project
    tools.append(create_flow_project)
```

**Line 452:** Remove `flow_mode` parameter from `get_tools_for_request()` signature
```python
# BEFORE:
async def get_tools_for_request(
    message_text: str,
    *,
    flow_mode: bool = False,
) -> list[BaseTool]:

# AFTER:
async def get_tools_for_request(
    message_text: str,
) -> list[BaseTool]:
```

### 2. `src/executive_assistant/scheduler.py`

**Line 18:** Remove scheduled flows import
```python
# DELETE:
from executive_assistant.storage.scheduled_flows import get_scheduled_flow_storage
```

**Lines 143-172:** Remove `_process_pending_flows()` function
```python
# DELETE entire function:
async def _process_pending_flows():
    """Check for and process pending scheduled flows.

    This is called periodically by the scheduler.
    Scheduled flows are executed in-process.
    """
    # ... entire function
```

**Lines 243-248:** Remove scheduled flows job from scheduler in `start_scheduler()`
```python
# DELETE this job registration:
_scheduler.add_job(
    _process_pending_flows,
    CronTrigger(second=0),
    id="check_pending_flows",
    replace_existing=True,
)
```

**Line 260:** Update scheduler start log message (remove "scheduled flows enabled")
```python
# BEFORE:
logger.info(f"{ctx} started (reminders; check-ins; scheduled flows enabled)")

# AFTER:
logger.info(f"{ctx} started (reminders; check-ins)")
```

### 3. `src/executive_assistant/channels/management_commands.py`

**Lines 46-57:** Remove flow tools imports and flow mode function references
```python
# Check what's imported and remove flow-related imports
# Likely includes: from executive_assistant.tools.flow_tools import ...
# Also remove any flow_mode parameter handling
```

### 4. `src/executive_assistant/channels/base.py`

**Flow-related references:** Search for and remove any flow mode detection/handling
- Look for `flow_mode` parameter passing
- Remove any flow detection in message handlers

### 5. `src/executive_assistant/channels/telegram.py`

**Flow-related references:** Search for and remove any flow mode handling
- Look for `/flow` command handlers
- Remove flow mode toggle logic

### 6. `src/executive_assistant/agent/status_middleware.py`

**Flow-related references:** Check for and remove any flow status handling

---

## Database Cleanup (Optional)

If the flows feature created database tables, consider:

```sql
-- Drop agent_registry table if exists
DROP TABLE IF EXISTS agent_registry CASCADE;

-- Drop scheduled_flows table if exists
DROP TABLE IF EXISTS scheduled_flows CASCADE;

-- Drop flow_projects table if exists
DROP TABLE IF EXISTS flow_projects CASCADE;
```

**Note:** Check actual table names in the storage files before running.

---

## Additional Cleanup

1. **Remove `flows` directory:** `src/executive_assistant/flows/`
2. **Remove `__pycache__` entries:** Python bytecode will be regenerated automatically
3. **Update imports:** Search for any remaining imports of deleted modules:
   ```bash
   grep -r "from executive_assistant.tools.flow_tools" src/
   grep -r "from executive_assistant.tools.agent_tools" src/
   grep -r "from executive_assistant.tools.flow_project_tools" src/
   grep -r "from executive_assistant.storage.agent_registry" src/
   grep -r "from executive_assistant.storage.scheduled_flows" src/
   grep -r "from executive_assistant.flows" src/
   grep -r "from executive_assistant.agent.flow_mode" src/
   ```

---

## Verification Steps

After removal, verify:

1. **No import errors:**
   ```bash
   uv run python -c "import executive_assistant"
   ```

2. **No broken tests:**
   ```bash
   uv run pytest tests/ -v
   ```

3. **Tool registry loads correctly:**
   ```bash
   uv run python -c "from executive_assistant.tools.registry import get_all_tools; import asyncio; tools = asyncio.run(get_all_tools()); print(f'Loaded {len(tools)} tools')"
   ```

4. **Scheduler starts without errors:**
   ```bash
   uv run python -c "from executive_assistant.scheduler import start_scheduler; import asyncio; asyncio.run(start_scheduler())"
   ```

5. **Application starts successfully:**
   ```bash
   uv run executive_assistant
   ```

---

## Implementation Order

### Phase 1: Delete Files (Low Risk)
1. Delete test files first
2. Delete skill files
3. Delete documentation files

### Phase 2: Delete Core Implementation (Medium Risk)
1. Delete storage backends
2. Delete flow implementation files
3. Delete agent tools

### Phase 3: Modify Integration Points (High Risk)
1. Update `registry.py` - remove flow references
2. Update `scheduler.py` - remove flow job
3. Update `management_commands.py` - remove flow imports
4. Update channel files - remove flow mode handling

### Phase 4: Verify & Test
1. Run import verification
2. Run application
3. Check for any remaining references

---

## Rollback Plan

If issues arise after removal:

1. **Git revert:** `git revert <commit-hash>` to undo the removal commit
2. **Partial revert:** Restore specific files from git history: `git checkout <commit-hash> -- <file-path>`

---

## Estimated Impact

- **Lines of code removed:** ~2,500+ (estimated)
- **Files deleted:** ~20 files
- **Files modified:** ~6 files
- **Test coverage impact:** ~7 test files removed
- **Documentation impact:** ~4 docs removed
