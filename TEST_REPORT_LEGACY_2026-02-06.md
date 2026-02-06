# Ken Executive Assistant Unified Test Report

**Status:** IN PROGRESS (Scope Migrated to Deterministic Runner)

## 1) Environment

- **Date (Local):** 2026-02-06
- **Date (UTC):** 2026-02-06
- **Commit:** _fill on run_
- **Provider/Model Mode:** _fill on run (expected: ollama cloud)_
- **Channel:** HTTP
- **Base URL:** `http://127.0.0.1:8000`
- **Runner:** `scripts/run_http_scope_tests.sh`

---

## 2) Scope Coverage (Unified)

This report now tracks the full unified scope from `TEST.md`, including:

- Core release gates (`S1`-`R2`)
- Weekly resilience (`W1A`-`W6`)
- Extended breadth (persona/onboarding, skills/instincts/profiles, learning tools, adhoc app-build workflows)

Legacy phase-oriented notes are preserved in:
`docs/archive/TEST_REPORT_LEGACY_2026-02-06.md`

---

## 3) Profile Summary

| Profile | Status | Pass | Fail | Skip | Notes |
|---|---|---:|---:|---:|---|
| `core` | ✅ PASS | 20 | 0 | 0 | Latest deterministic smoke run passed (`S1`-`R2`) |
| `weekly` | ⚠️ PARTIAL | _fill_ | _fill_ | _fill_ | Includes optional restart automation (`W6`) |
| `extended` | ⚠️ PENDING | _fill_ | _fill_ | _fill_ | Persona/skills/learning/app-build breadth |

---

## 4) Latest Core Results (`S1`-`R2`)

- `S1` PASS
- `S2` PASS
- `S3` PASS
- `P1` PASS
- `P2` PASS
- `T1` PASS
- `T2` PASS
- `T3` PASS
- `T4` PASS
- `T5` PASS
- `C1` PASS
- `C2` PASS
- `C3` PASS
- `E1` PASS
- `E2` PASS
- `E3` PASS
- `I1` PASS
- `I2` PASS
- `R1` PASS
- `R2` PASS

Evidence source: deterministic run output (`/tmp/ken_full_test_results.txt`) captured on 2026-02-06.

---

## 5) Weekly Results (`W1A`-`W6`)

Record latest run here:

- `W1A` _pending_
- `W1B` _pending_
- `W1C` _pending_
- `W1D` _pending_
- `W2` _pending_
- `W3` _pending_
- `W4` _pending_
- `W5` _pending_
- `W6_PRE` _pending_
- `W6` _pending or skip with reason_

---

## 6) Extended Results

### Persona/Onboarding Matrix

- 16 persona acknowledgment cases: _pending_

### Skills/Instincts/Profiles

- `X_SKILLS_LIST`: _pending_
- `X_INSTINCTS_LIST`: _pending_
- `X_PROFILES_LIST`: _pending_

### Learning Tools

- `X_LEARNING_STATS`: _pending_
- `X_LEARNING_VERIFY`: _pending_
- `X_LEARNING_PATTERNS`: _pending_

### Adhoc App-Build Workflows

- `X_APP_CRM`: _pending_
- `X_APP_FILE`: _pending_

---

## 7) Known Issues / Risks

1. Multi-step single-prompt workflows can still end after partial tool execution if not decomposed.
2. Automated restart validation (`W6`) depends on process-control environment and may require explicit restart command.
3. Weekly concurrency checks should prefer DB/file assertions rather than assistant prose to avoid false negatives.

---

## 8) Final Verdict

- **Current verdict:** `PASS WITH RISKS`
- **Reason:** Core reliability is passing; full weekly + extended deterministic runs are still being completed under unified scope.

