# Improvement Plan (Items 1, 2, 5)

**Context:** Post-test hardening plan for reliability and latency diagnostics.

## 1) Completion Gate After Tool-Call Runs

### Goal
Prevent partial runs where tools are invoked but no real completion outcome is returned.

### Plan
1. Add a post-run completion validator:
- Detect: tool calls occurred, but no final user-facing completion artifact/message.
2. Add one bounded continuation attempt:
- Force one extra completion turn before failing.
3. If still incomplete:
- Return controlled error with clear recovery guidance.

### Acceptance
- No silent partial completions in core deterministic tests.
- Failures are explicit and actionable.

---

## 2) Auto-Continue Retry for Partial Executions

### Goal
Improve resilience for multi-step prompts that stop mid-execution.

### Plan
1. Add bounded auto-continue (`max_recover_turns=1..2`).
2. Add idempotency guards for mutating tools:
- Prevent duplicate writes/inserts/reminders on recovery turn.
3. Add structured logging:
- Mark recovery attempts and terminal outcomes.

### Acceptance
- Weekly resilience cases (especially `W1`-style decompositions) show fewer incomplete runs.
- No duplicated side effects from retries.

---

## 5) Request-Stage Timing Instrumentation

### Goal
Pinpoint latency bottlenecks across simple/medium/complex requests.

### Plan
1. Instrument per-stage timing:
- request intake/validation
- agent construction
- model call time
- tool execution aggregate and per-tool
- post-processing/serialization
2. Emit structured timing logs for each request.
3. Add report summarization:
- avg/p50/p95 per stage and by scenario class.

### Acceptance
- Test report includes stage-level timing breakdown.
- Clear bottleneck attribution for high-latency requests.

