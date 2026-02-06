# Managed Remote MCP Conversion Plan

## Objective
Convert user/admin MCP configuration from direct local stdio execution to managed remote MCP instances, while preserving current user experience (`mcp_add_server`, `mcp_add_remote_server`, `mcp_remove_server`, `mcp_reload`).

## Why
- Reduce latency from repeated local process/session startup.
- Avoid host-level arbitrary command execution risk from user-provided local stdio configs.
- Improve reliability with long-running, health-checked MCP services.
- Centralize observability, secret handling, and lifecycle controls.

## Target Model
- User intent remains: "add MCP server".
- Runtime behavior changes:
  - User local config is treated as provisioning intent.
  - System creates/assigns a managed remote MCP endpoint.
  - Agent only connects through remote HTTP/SSE MCP endpoints.

## Architecture
1. Control Plane
- Validates requested server template and parameters.
- Provisions managed MCP instance (container/process).
- Stores lifecycle metadata and endpoint mapping.

2. MCP Runtime Pool
- Long-running MCP workers per template or per user/thread (policy-based).
- Exposes HTTP/SSE endpoint for tool discovery and execution.
- Has health checks, restart policy, concurrency limits.

3. Data Layer
- Keep user-facing config in `data/users/{thread}/mcp/*.json`.
- Add managed instance registry (new):
  - `data/users/{thread}/mcp/managed_instances.json`.

4. Agent Tool Registry
- Load only remote MCP connections (managed + explicit remote user configs + eligible admin configs).
- Never execute user-provided local command directly in production mode.

## Data Model Changes
Add managed instance record:
- `instance_id`: string
- `source_server_name`: string
- `template`: string (e.g., `clickhouse`)
- `state`: `provisioning | active | draining | stopped | failed`
- `endpoint_url`: string
- `auth_ref`: string (reference to secret/token, not raw secret)
- `created_at`, `updated_at`, `last_health_at`
- `owner_thread_id`
- `ttl_policy`: optional

Add server intent metadata on user local config entries:
- `mode`: `managed_remote` (default for converted local entries)
- `template`: template id
- `parameters`: validated parameter map

## Tooling/API Changes
1. `mcp_add_server`
- Current: stores raw stdio command/args.
- New behavior:
  - If command matches supported template, create managed provisioning request.
  - Persist intent + instance mapping.
  - Return `provisioning` or `active` status.

2. `mcp_add_remote_server`
- Keep as-is for explicit remote endpoints.
- Add optional flag `managed=false` metadata for observability.

3. `mcp_remove_server`
- If server is managed: stop/decommission instance and remove mapping.
- If explicit remote: remove config only.

4. `mcp_reload`
- Rebuild tool cache from active managed remote + explicit remote servers.
- Skip failed/draining instances and surface status summary.

5. New optional tools
- `mcp_instance_status(name)`
- `mcp_start_server(name)` / `mcp_stop_server(name)` for pause/resume without delete.

## Security Model
- Allowlist templates only (no arbitrary command execution for users).
- Secret references stored in config; secret values in secure store/env.
- Per-thread isolation of instances and auth context.
- Network egress policy restricted by template.
- Audit logs for add/remove/start/stop/provision failures.

## Performance Strategy
- Keep instances warm with idle timeout policy.
- Reuse persistent remote sessions where adapter supports it.
- Prefer per-template shared pools when data isolation allows.
- Track p50/p95 for:
  - tool list load
  - first tool call latency
  - subsequent tool call latency

## Rollout Plan
### Phase 1: Foundation
- Add managed instance schema + storage helper.
- Add feature flag: `MCP_MANAGED_REMOTE_ENABLED`.
- Implement template registry and parameter validators.

### Phase 2: Dual Path
- Keep legacy local stdio path behind fallback flag.
- Route `mcp_add_server` through managed path when template recognized.
- Keep `mcp_add_remote_server` unchanged.

### Phase 3: Default Managed
- Enable managed path by default for user-added local servers.
- Emit warnings for unsupported arbitrary local commands.
- Add pause/resume lifecycle controls.

### Phase 4: Harden
- Disable arbitrary user local stdio in production profile.
- Keep admin override for emergency/debug only.

## Migration
- Background migrator scans existing user local entries.
- For known templates:
  - create managed instance
  - rewrite entry metadata to `mode=managed_remote`
  - preserve original command for rollback metadata.
- For unknown commands:
  - mark `legacy_local_unmanaged`
  - require manual admin review.

## Testing Scope
1. Unit tests
- Template validation and parameter coercion.
- Instance lifecycle transitions.
- Tool config render from managed state.

2. Integration tests
- `mcp_add_server` -> provisioning -> `mcp_reload` -> tools available.
- `mcp_remove_server` tears down managed instance.
- Failed health check removes instance from active tool list.

3. E2E tests
- User flow with ClickHouse managed template.
- Latency benchmarks before/after managed conversion.
- Failure injection (crash/restart/reload consistency).

## Acceptance Criteria
- No direct user local stdio execution in managed mode.
- `mcp_reload` success is independent of one bad MCP endpoint.
- p95 first-call latency reduced by agreed target (e.g., 40%+).
- Controlled stop/start/remove lifecycle works and is observable.

## Open Decisions
- Multi-tenant shared worker vs per-thread isolated worker.
- Idle shutdown timeout default.
- Secret backend choice (env, vault, KMS).
- Whether admin configs should also be auto-managed.

## Immediate Next Steps
1. Implement storage schema and feature flag.
2. Add template registry for `clickhouse` first.
3. Refactor `mcp_add_server` to managed provisioning path.
4. Add `mcp_instance_status` and lifecycle controls.
5. Expand weekly test profile with managed MCP lifecycle + latency assertions.
