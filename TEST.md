# Ken Executive Assistant Unified Test Plan

**Last Updated:** 2026-02-06  
**Purpose:** A single, deterministic scope that merges current release gates and legacy breadth coverage so agent reliability is assessed end-to-end.

## 1) Scope Principles

1. Scope must include all critical capability areas from both prior plans:
- Core runtime reliability (`S1`-`R2`)
- Weekly resilience (`W1`-`W6`)
- Persona/onboarding behavior
- Skills/instinct/profile discovery and adaptation
- Learning-pattern tools (Teach/Verify, Reflect/Improve, Predict/Prepare)
- App-build and cross-tool workflows
- Full registered-tool execution coverage (all runtime tools)

2. Assertions must be deterministic whenever possible:
- Prefer DB/file/state verification over checking natural-language wording.
- Keep text-based assertions only for unavoidable conversational outcomes.

3. One source of truth:
- This file defines required test scope.
- `TEST_REPORT.md` must report results against this exact scope.

---

## 2) Execution Profiles

### Profile `core` (Release Blocking)
Run on every change.

- Startup and API health: `S1`-`S3`
- Preflight provider compatibility: `PRE_PROVIDER_COMPAT`
- Persistence/context: `P1`-`P2`
- Tool family behavior: `T1`-`T5`
- Check-in/scheduler commands: `C1`-`C3`
- Error handling: `E1`-`E3`
- Isolation: `I1`-`I2`
- Streaming contract: `R1`-`R2`
- Onboarding instinct creation: `ONBOARDING_INSTINCT`
- Tool registry completeness: `Z1`-`Z3` (tool-e2e included in core)

### Profile `weekly` (Stability and Resilience)
Run weekly (or before major release).

- `W1A`-`W1D`: decomposed multi-step workflow reliability
- `W2`: transient/invalid web dependency behavior
- `W3`: recurring reminders and recurrence metadata
- `W4`: proactive check-in/scheduler path verification
- `W5`: parallel conversation/thread isolation under concurrency
- `W6_PRE` + `W6`: persistence across process restart

### Profile `extended` (Breadth Coverage)
Run nightly or pre-release.

- Persona and onboarding matrix (16 personas)
- Skills/instincts/profiles discoverability
- Learning tool flows: `learning_stats`, `verify_preferences`, `show_patterns`
- Adhoc app-build style workflows (cross-tool artifact creation)

### Profile `tool-e2e` (Registry Completeness)
Run nightly or pre-release.

- `Z1`: invoke every runtime-registered tool once (dynamic count via `get_all_tools()`)
- `Z2`: enforce non-empty, unique tool names in registry
- `Z3`: embedded tool-call parsing coverage for JSON `<tools>` and XML `<function_calls>` formats

Note: `core` now already includes `Z1`-`Z3`. Use `tool-e2e` when you want this subset by itself.

### Profile `all`
Run `core + weekly + extended`.

---

## 3) Deterministic Assertion Rules

1. Prefer artifact assertions:
- SQLite rows (`tdb/db.sqlite`), file existence/content under `data/users/...`, reminder/check-in persisted state.

2. Reminder assertions must prove real persistence:
- Do not accept assistant text alone.
- Require `reminders` table row existence for the active `thread_id` and `reminder_list` visibility.
- Include natural-language time phrasing coverage (for example `11.22pm tonight`).

2. Use conversation-text assertions only when artifact checks are not available:
- Role acknowledgment, graceful error messaging, SSE envelope markers.

3. Use isolated run IDs per execution:
- Conversation IDs are suffixed with a run timestamp to prevent cross-run contamination.

4. Restart tests:
- `W6` can be automated only when an explicit restart command is provided.
- Without restart command, mark `W6` as `SKIP` (not `PASS`).

---

## 4) Preflight (Required)

1. Start PostgreSQL:
```bash
docker compose -f docker/docker-compose.yml up -d postgres
```

2. Verify Ollama Cloud mode and models from `docker/.env`:
```bash
rg -n "^(DEFAULT_LLM_PROVIDER|OLLAMA_MODE|OLLAMA_DEFAULT_MODEL|OLLAMA_FAST_MODEL)=" docker/.env
```

3. Start assistant in HTTP mode:
```bash
EXECUTIVE_ASSISTANT_CHANNELS=http UV_CACHE_DIR=.uv-cache uv run executive_assistant
```

4. Health check:
```bash
curl -sS http://127.0.0.1:8000/health
```

5. **Provider compatibility gate** (NEW):
```bash
# Verify tool calling works with configured provider
# This catches issues like deepseek-reasoner not supporting tools
curl -s http://127.0.0.1:8000/message \
  -H "Content-Type: application/json" \
  -d '{"content":"What is 2+2?","user_id":"preflight_test"}'
```

---

## 5) Runner Commands

Use deterministic runner:

```bash
scripts/run_http_scope_tests.sh --profile core
scripts/run_http_scope_tests.sh --profile weekly
scripts/run_http_scope_tests.sh --profile extended
scripts/run_http_scope_tests.sh --profile tool-e2e
scripts/run_http_scope_tests.sh --profile all
```

Run pytest tests in parallel (NEW):

```bash
# Run pytest after HTTP scope tests with automatic parallelization
scripts/run_http_scope_tests.sh --profile core --with-pytest

# Specify number of parallel workers
scripts/run_http_scope_tests.sh --profile all --with-pytest --pytest-parallel 4
```

Standalone pytest commands:

```bash
# Onboarding instinct tests (verifies create_instinct bug fix)
uv run pytest -q tests/test_onboarding_instinct.py

# Tool E2E tests (dynamic tool count, validates all 117+ tools)
uv run pytest -q tests/test_all_tools_end_to_end.py

# Embedded tool call parsing tests
uv run pytest -q tests/test_embedded_tool_call_parsing.py
```

Restart-enabled weekly run:

```bash
scripts/run_http_scope_tests.sh \
  --profile weekly \
  --allow-restart \
  --restart-cmd 'set -a; source docker/.env; set +a; EXECUTIVE_ASSISTANT_CHANNELS=http UV_CACHE_DIR=.uv-cache .venv/bin/executive_assistant >/tmp/ken_http.log 2>&1 &'
```

Optional flags:

```bash
--base-url http://127.0.0.1:8000
--output /tmp/ken_scope_test_results.txt
--pytest-parallel <n|auto>    # Number of parallel pytest workers (default: auto)
```

---

## 6) Capability Mapping (Legacy Coverage Included)

| Capability Area | Included in Unified Scope | Profile |
|---|---|---|
| HTTP startup and message flow | Yes | `core` |
| Memory/context continuity | Yes | `core`, `extended` |
| Tool families (TDB/ADB/VDB/file/reminders/time) | Yes | `core`, `extended` |
| Proactive check-in and scheduler | Yes | `core`, `weekly` |
| Streaming semantics | Yes | `core` |
| Error handling | Yes | `core` |
| Cross-user/thread isolation | Yes | `core`, `weekly` |
| Multi-step workflows | Yes (decomposed + integrated behavior) | `weekly`, `extended` |
| Persona onboarding matrix | Yes | `extended` |
| Skills/instinct/profile flows | Yes | `extended` |
| Learning pattern tools | Yes | `extended` |
| Adhoc app-build scenarios | Yes | `extended` |
| Full runtime tool inventory (117 tools) | Yes | `core`, `tool-e2e` |
| Restart persistence | Yes | `weekly` |

---

## 7) Acceptance Gates

Release candidate is acceptable when:

1. `core` profile has zero failures.
2. `weekly` profile has zero failures for enabled checks.
3. If `W6` restart automation is not enabled, report `W6` explicitly as `SKIP` with reason.
4. No unhandled exceptions in server logs during executed profiles.
5. LLM provider/mode in use is recorded in report metadata.
6. `Z1`-`Z3` pass in `core` (or are explicitly documented with per-tool reasons).

---

## 8) Reporting Contract (`TEST_REPORT.md`)

Each report must include:

1. Environment metadata:
- Date/time (UTC and local)
- Commit SHA
- Model/provider mode (for example, `ollama cloud`)
- Channel and base URL

2. Profile-level summary:
- `core`, `weekly`, `extended` run status and totals (`PASS/FAIL/SKIP`)

3. Case-level results:
- Each case ID with status and concise failure reason/repro prompt

4. Known issues and risks:
- Open defects, flaky cases, and mitigation

5. Final verdict:
- `PASS`, `PASS WITH RISKS`, or `FAIL`
