# Flow + Agent Builder Guide

This skill teaches how to design **mini‑agents** and **flows** that actually run tools, return structured outputs, and pass clean inputs between steps. Use this when creating agents or troubleshooting flow failures.

## Available tools (common)
Web:
- `search_web` (search results)
- `firecrawl_scrape` (single page → markdown)
- `firecrawl_crawl` (site crawl → job id)
- `firecrawl_check_status` (poll crawl)
- `playwright_scrape` (JS-heavy pages; requires Playwright install)

Files/DB/VS:
- `write_file`, `read_file`, `list_files`
- `query_db`, `create_db_table`, `list_db_tables`
- `create_vs_collection`, `add_vs_documents`, `search_vs`

## Quick test (single agent)
Use `run_agent` to test a mini‑agent without creating a flow:
```
run_agent(agent_id="web_crawl_agent", flow_input={"url":"https://example.com"})
```

## Level 1 — Minimal working flow
**Goal:** single agent that calls one tool and returns a single value.

**Mini‑agent prompt template:**
```
You are the crawl agent.
Call firecrawl_scrape with url=$flow_input.url.
Return only the markdown string.
```

**Flow requirements:**
- `flow_input` must include required fields (e.g., `url`).
- First agent prompt must reference `$flow_input` if you pass `flow_input`.

## Level 2 — Structured output + chaining
**Goal:** multi‑agent flow with defined JSON outputs.

**AgentSpec rules:**
- `output_schema` must describe the JSON keys you return.
- Prompt must say “Return JSON matching output_schema.”
- Use `$previous_output` only when needed.

**Example (extract → summarize):**
```
You are the summary agent.
Summarize $previous_output in 3 bullets.
Return JSON matching output_schema with key `summary`.
```

## Level 3 — Test‑driven flow design (framework)
Use this framework for complex flows:
1) Clarify & recap goal, scope, constraints, success criteria.
2) Research unknowns (use tools) before designing.
3) Decompose into stages with explicit inputs/outputs.
4) Propose 1–3 designs; recommend one.
5) Define output_schema + small test cases per stage.
6) Validate each stage output before chaining.
7) If blocked, suggest alternatives or simplified path.

## Common failures + fixes
- **Unknown tool(s):** use tool names exactly as registered (see list above).
- **Empty outputs:** prompt did not explicitly call a tool.
- **Recursion limit:** model kept “thinking” without tool call → fix prompt.
- **Wrong inputs:** use `$flow_input.<field>` not `{field}`.

## Quick checklist (before running)
- Agent tools list ≤ 5 (max 10).
- Prompt contains explicit tool call.
- First agent uses `$flow_input` if payload provided.
- Later agents use `$previous_output` if needed.
- output_schema is defined and referenced.
