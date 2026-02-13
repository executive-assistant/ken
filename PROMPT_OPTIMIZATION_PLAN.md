# System Prompt + Skills Optimization Plan (Merged)

**Updated:** 2026-02-13  
**Status:** Plan Only (no code changes in this document)  
**Primary Goal:** Reduce prompt overhead while preserving behavior quality and tool reliability.

---

## 1) Scope and Objectives

This plan merges:
- the existing optimization draft in this file, and
- the latest code-path review proposal.

### Objectives

1. Reduce steady-state system prompt size.
2. Eliminate prompt assembly drift across runtime paths.
3. Keep behavior-critical rules intact (memory, reminders, direct tool execution, task tracking).
4. Make skills truly progressive-disclosure (minimal always-on, load detail on demand).
5. Add measurement + guardrails so prompt growth is detected early.

### Out of Scope (for this plan phase)

- Rewriting core business logic outside prompt/skills pipelines.
- Broad model/provider migration.
- Non-prompt architecture redesign unrelated to context budget.

---

## 2) Current State (Validated)

## Prompt assembly currently has two paths

1. **Request-time path (active message handling)**
   - `src/executive_assistant/channels/base.py:353` calls `get_system_prompt(...)`
   - `src/executive_assistant/agent/prompts.py:140` layers:
     - admin prompt
     - base prompt
     - instincts (or deprecated user prompt fallback)
     - emotional context
     - channel appendix

2. **Startup path (separate assembly path)**
   - `src/executive_assistant/main.py:213-221` builds:
     - `get_default_prompt()`
     - `SkillsBuilder.build_prompt(...)`
     - `get_channel_prompt(...)`

### Key finding

Prompt composition is split across two paths, which creates drift risk and makes token budgeting harder to reason about.

### Additional cleanup finding

`load_user_prompt` is defined twice in `src/executive_assistant/agent/prompts.py` (`:224` and `:264`); second definition overrides the first.

---

## 3) Token Baseline (Estimated)

Tokenizer package was unavailable in this environment; values below are bounded estimates from measured words/chars in repository files.

| Component | Measured Source | Estimated Tokens |
|---|---|---:|
| Base prompt | `prompts.py:get_default_prompt` | ~1,100-1,400 |
| Channel appendix | Telegram/HTTP appendix | ~40-70 |
| Startup skills section (full on_start content) | `skills/content/on_start/*.md` via builder format | ~4,700-6,800 |
| On-demand skills index lines | grouped names only | ~30-80 |
| Instincts section | dynamic | 0-500 |
| Emotional section | dynamic | 0-100 |

### Practical baselines

- **Current request-time baseline** (no heavy skills): ~1,200-1,500 + dynamic sections.
- **If full startup skills are injected**: can exceed ~8,000 before admin/tool metadata effects.

---

## 4) Target Budget

### Budget targets

1. System prompt steady-state: **<= 2,200 tokens**.
2. System prompt with dynamic sections (instinct + emotional + admin): **<= 2,800 tokens**.
3. Always-on skills contribution: **<= 300 tokens**.
4. Instinct section soft cap: **<= 220 tokens**.
5. Emotional section soft cap: **<= 60 tokens**.

### Non-negotiable behavior invariants

- Preference statements still trigger `create_memory` behavior.
- Report/summarization flows still check memory first.
- Reminder scheduling behavior remains explicit and timezone-safe.
- Direct user tool requests still execute tool first.
- Multi-step research still uses progress/todo planning behavior.

---

## 5) Merged Implementation Plan

## Phase 0 - Instrumentation First (No behavior change)

1. Add prompt-size telemetry at composition time (per layer and total).
2. Log hashes/signatures for prompt variants to detect drift.
3. Add warning thresholds (e.g., warn >2,500, error-log >3,000).

**Deliverable:** measurable baseline and ongoing visibility before refactors.

## Phase 1 - Unify Prompt Assembly

1. Create one canonical composer used by all runtime paths.
2. Route both channel request-time and startup paths through the same composition logic.
3. Remove duplicate/legacy composition helpers that are not needed.
4. Remove duplicate `load_user_prompt` definition.

**Why:** prevents split-brain prompt behavior and inconsistent token footprint.

## Phase 2 - Base Prompt Compression (High ROI)

1. Convert verbose prose into compact rule blocks.
2. Remove redundant examples; keep one minimal example only where needed.
3. Collapse repeated "CRITICAL" directives into concise invariant statements.
4. Keep user-facing style constraints concise and non-conflicting.

**Expected savings:** ~300-500 tokens.

## Phase 3 - Skills Strategy: True Progressive Disclosure

1. Keep always-on skills as a compact index only (name + one-line trigger).
2. Move heavy workflow/tutorial content to on-demand loading.
3. Do not delete useful skill content by default; reclassify first.
4. Ensure `load_skill("...")` remains first-class and discoverable.

**Expected savings:** up to several thousand tokens in paths currently loading full startup skill content.

## Phase 4 - Dynamic Context Caps (Instinct + Emotional + Admin)

1. Enforce capped formatting for instincts (limit domains/actions and verbosity).
2. Keep emotional context one-line actionable guidance only.
3. Cap admin override section size or summarize when oversized.
4. Define deterministic truncation order (lowest-priority guidance trimmed first).

**Expected savings:** variable, typically 100-400 tokens in active conversations.

## Phase 5 - Tool Definition Prompt Load Review

1. Standardize tool docstrings for brevity while preserving parameter clarity.
2. Remove verbose narrative text in frequently-used tools.
3. Keep examples only for ambiguity-prone tools.
4. Normalize error-handling language patterns surfaced to model context.

**Expected savings:** moderate, depends on tool serialization layer.

## Phase 6 - Optional Follow-up: Emotional State Persistence

- Keep as optional enhancement, not a blocker for prompt optimization.
- If implemented, maintain strict thread scoping and small prompt rendering.

---

## 6) Concrete File Impact Plan

### Primary files

- `src/executive_assistant/agent/prompts.py`
- `src/executive_assistant/channels/base.py`
- `src/executive_assistant/main.py`
- `src/executive_assistant/skills/builder.py`
- `src/executive_assistant/skills/content/on_start/*.md`
- `src/executive_assistant/instincts/injector.py`
- `src/executive_assistant/instincts/emotional_tracker.py` (if Phase 6 executed)

### Policy for on_start skills

- Prefer trimming/reclassification over deletion.
- Keep onboarding behavior intact.
- Maintain quick-reference discoverability while reducing verbose examples.

---

## 7) Test and Verification Plan

## A) Prompt budget tests

1. Assert steady-state prompt <= target budget.
2. Assert dynamic prompt with simulated instincts/emotion <= max budget.
3. Snapshot tests for layer order and inclusion/exclusion rules.

## B) Behavior regression tests

1. Memory capture on explicit preference language.
2. Memory retrieval prior to report/summarization behavior.
3. Reminder parsing and timezone confirmation behavior.
4. Direct tool invocation compliance.
5. Multi-step planning/todo behavior still triggered appropriately.

## C) Runtime parity tests

1. Startup and request-time paths produce same canonical composition.
2. Channel-specific appendices still applied correctly.
3. No regressions in HTTP and Telegram handlers.

---

## 8) Rollout Strategy

1. Land Phase 0 telemetry first.
2. Land Phase 1 unification next, behind a feature flag if needed.
3. Roll out prompt compression + skills changes incrementally.
4. Monitor token/latency behavior for 24-48 hours.
5. Continue with dynamic caps and tool text trimming.

---

## 9) Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Over-compression drops instruction fidelity | Behavior regressions | Preserve invariants; add behavior tests before and after |
| Path unification introduces hidden coupling | Runtime errors | Incremental rollout + parity tests |
| Skills reclassification hurts discoverability | Lower tool use quality | Keep concise index + explicit `load_skill` guidance |
| Dynamic truncation drops important context | Poor personalization | Priority-ordered truncation, cap only lowest-value text first |

---

## 10) Acceptance Criteria

1. Canonical prompt assembly path is single-source.
2. Prompt token budgets are met in CI/local checks.
3. Core behavioral invariants pass regression tests.
4. No increase in tool-call failure rate attributable to prompt changes.
5. Skills remain discoverable and loadable on demand.

---

## Appendix: Notes on Prior Draft

The prior draft proposed aggressive startup-skill consolidation and emotional persistence changes. This merged version keeps those ideas where useful, but prioritizes:
- architecture unification,
- measurable budget controls,
- and phased low-risk rollout.

This sequencing reduces regression risk and makes optimization impact measurable at each step.
