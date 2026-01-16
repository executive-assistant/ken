# User-First Workspace Redesign (Three Workspace Types + Roles)

## Objective
Redesign identity, storage, and sharing around **user-first** ownership with **three workspace types**:
- **Individual** - Personal workspace (one owner)
- **Group** - Team workspace (multiple members)
- **Public** - Company workspace (everyone can read)

Threads are secondary; all tools route through **workspace_id**. Merge is simplified to **identity mapping only** (no data copying).

---

## Core Principles
- **user_id is the primary identity**
- **workspace_id is the storage owner** (files/KB/DB/reminders/workflows)
- **thread_id is just a conversation handle**
- **Three workspace types** with different access models
- **Role-based permissions**: admin, editor, reader
- **No data migration on merge/upgrade** (only identity mapping changes)

---

## Workspace Types

| Type | Owner | Default Access | Use Case |
|------|-------|----------------|----------|
| **Individual** | One user | Owner only | Personal files, KB, DB |
| **Group** | Multiple users | Members only | Team collaboration, group chats |
| **Public** | System | Read-only for all | Company resources, docs |

### Role Permissions

| Role | Can Read | Can Edit | Can Write | Can Manage Members |
|------|----------|----------|-----------|-------------------|
| **admin** | ✅ | ✅ | ✅ | ✅ |
| **editor** | ✅ | ✅ | ✅ | ❌ |
| **reader** | ✅ | ❌ | ❌ | ❌ |

---

## ID Strategy

### user_id
Stable, channel-prefixed:
- `tg:{telegram_user_id}`
- `email:{email_hash}` (or normalized email)
- `anon:{uuid}` (web guest)

### group_id
Generated for group workspaces:
- `group:{uuid}`

### thread_id
Channel + chat context:
- `telegram:{chat_id}` or `telegram:{user_id}:{chat_id}`
- `http:{uuid}`

### workspace_id
Generated once, tied to owner:
- `ws:{uuid}` (preferred format)

---

## Storage Layout
```
data/workspaces/
  {workspace_id}/
    files/
    kb/
    db/
    mem/
    reminders/
    workflows/

data/threads/
  {thread_id}/
    checkpoints/
```

---

## Complete Schema

### 1) Users
```sql
CREATE TABLE users (
  user_id TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'active',  -- active, suspended
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 2) Groups (for group workspaces)
```sql
CREATE TABLE groups (
  group_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE group_members (
  group_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'member',  -- admin, member
  joined_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (group_id, user_id),
  FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

### 3) Workspaces (supports 3 types via ownership)
```sql
CREATE TABLE workspaces (
  workspace_id TEXT PRIMARY KEY,
  type TEXT NOT NULL,  -- individual | group | public
  name TEXT NOT NULL,  -- Display name

  -- Ownership: exactly one should be set
  owner_user_id TEXT NULL,     -- For individual workspaces
  owner_group_id TEXT NULL,    -- For group workspaces
  owner_system_id TEXT NULL,   -- For public workspace (e.g., "public")

  created_at TIMESTAMP DEFAULT NOW(),

  -- Ensure exactly one owner is set
  CONSTRAINT has_exactly_one_owner CHECK (
    (owner_user_id IS NOT NULL AND owner_group_id IS NULL AND owner_system_id IS NULL) OR
    (owner_user_id IS NULL AND owner_group_id IS NOT NULL AND owner_system_id IS NULL) OR
    (owner_user_id IS NULL AND owner_group_id IS NULL AND owner_system_id IS NOT NULL)
  ),

  -- FKs (nullable because not all apply to all types)
  FOREIGN KEY (owner_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (owner_group_id) REFERENCES groups(group_id) ON DELETE CASCADE
);
```

### 4) User → Workspace (individual workspaces)
```sql
CREATE TABLE user_workspaces (
  user_id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

### 5) Group → Workspace (group workspaces)
```sql
CREATE TABLE group_workspaces (
  group_id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE
);
```

### 6) Thread → Workspace (routing)
```sql
CREATE TABLE thread_workspaces (
  thread_id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE
);
```

### 7) Workspace Members (role-based access)
```sql
CREATE TABLE workspace_members (
  workspace_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  role TEXT NOT NULL,  -- admin | editor | reader
  granted_by TEXT NULL,     -- Who granted this role
  granted_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (workspace_id, user_id),
  FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (granted_by) REFERENCES users(user_id),
  CHECK (role IN ('admin', 'editor', 'reader'))
);
```

### 8) User Aliases (for merges/upgrades)
```sql
CREATE TABLE user_aliases (
  alias_id TEXT PRIMARY KEY,  -- e.g., anon:{uuid}
  user_id TEXT NOT NULL,      -- canonical user_id
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

### 9) ACL (for sharing specific resources externally)
```sql
CREATE TABLE workspace_acl (
  id SERIAL PRIMARY KEY,
  workspace_id TEXT NOT NULL,
  resource_type TEXT NOT NULL,  -- file_folder | kb_collection | db_table | reminder | workflow
  resource_id TEXT NOT NULL,
  target_user_id TEXT NULL,
  target_group_id TEXT NULL,
  permission TEXT NOT NULL,     -- read | write (admin via workspace_members only)
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NULL,

  FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE,
  FOREIGN KEY (target_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (target_group_id) REFERENCES groups(group_id) ON DELETE CASCADE,

  -- Exactly one target (user OR group)
  CONSTRAINT has_exactly_one_target CHECK (
    (target_user_id IS NOT NULL AND target_group_id IS NULL) OR
    (target_user_id IS NULL AND target_group_id IS NOT NULL)
  ),

  -- Valid permissions (admin via workspace_members only)
  CONSTRAINT acl_valid_permission CHECK (permission IN ('read', 'write')),

  -- No duplicate grants
  UNIQUE (workspace_id, resource_type, resource_id, target_user_id, target_group_id)
);
```

---

## Access Control

### Default Access by Workspace Type

| Workspace Type | Who Can Access | Default Role |
|----------------|----------------|--------------|
| **Individual** | Owner only | admin (implicit) |
| **Group** | Group members | From group_members table |
| **Public** | Everyone | reader (implicit) |

### Access Check Logic

```python
ROLE_PERMISSIONS = {
    "admin": {"read": True, "write": True, "admin": True},
    "editor": {"read": True, "write": True, "admin": False},
    "reader": {"read": True, "write": False, "admin": False}
}

def can_access(user_id: str, workspace_id: str, action: str) -> bool:
    """
    action: read | write | admin
    """
    workspace = get_workspace(workspace_id)

    # Workspace owner is always admin
    if workspace.owner_user_id == user_id:
        return True

    # Check explicit workspace membership
    member = get_workspace_member(workspace_id, user_id)
    if member:
        return ROLE_PERMISSIONS[member.role].get(action, False)

    # Group workspace: check group membership
    if workspace.owner_group_id:
        group_role = get_group_member_role(workspace.owner_group_id, user_id)
        if group_role:
            # Group admins are workspace admins, members are readers
            return group_role == "admin" or action == "read"

    # Public workspace: everyone can read
    if workspace.type == "public" and action == "read":
        return True

    # Check ACL for external grants
    return has_acl_grant(user_id, workspace_id, action)
```

---

## Request Identity Resolution

### How user_id is Derived

The `user_id` is the canonical identifier for all access control. It must be **server-issued** and **immutable from clients**.

```python
def resolve_request_user(request) -> str:
    """
    Derive canonical user_id from incoming request.
    Channel-specific implementations extract identity and resolve aliases.
    """
    channel = get_channel_type(request)  # 'telegram', 'http', etc.

    if channel == 'telegram':
        # Extract from Telegram update
        raw_id = f"tg:{request.message.from_user.id}"

    elif channel == 'http':
        # Extract from session/token
        session = get_session(request)
        if not session or not session.user_id:
            # Create new anonymous user
            raw_id = f"anon:{uuid4()}"
            session.user_id = raw_id
        else:
            raw_id = session.user_id

    else:
        raise ValueError(f"Unknown channel: {channel}")

    # Resolve to canonical user_id (follow alias chain)
    return resolve_user_id(raw_id)  # Implemented in workspace_storage.py
```

### Channel-Specific user_id Format

| Channel | user_id Format | Source |
|---------|---------------|--------|
| **Telegram** | `tg:{telegram_user_id}` | `message.from_user.id` (server-verified) |
| **HTTP (logged in)** | `email:{normalized_email}` | Server session, verified on login |
| **HTTP (anonymous)** | `anon:{uuid}` | Server-generated session ID |

### Security Requirements

1. **Server-issued only**: `user_id` is never accepted from request headers/cookies
2. **Channel verification**: Each channel verifies identity via its own auth mechanism
3. **Immutable**: Once assigned, `user_id` for a session never changes
4. **Alias resolution**: Final `user_id` is always canonical (alias chain resolved)

---

## Routing Rules

### Resolve workspace for a request
```python
def resolve_workspace_id(thread_id: str) -> str:
    """Get workspace_id from thread_id."""
    return db.fetchval(
        "SELECT workspace_id FROM thread_workspaces WHERE thread_id = $1",
        thread_id
    )
```

### Accessible workspaces for a user
```python
def accessible_workspaces(user_id: str) -> list[dict]:
    """
    Return all workspaces the user can access.
    """
    results = []

    # 1. Individual workspace (if owner)
    own = get_user_workspace(user_id)
    if own:
        results.append({"workspace_id": own, "role": "admin", "type": "individual"})

    # 2. Group workspaces (via group membership)
    for group in get_user_groups(user_id):
        ws = get_group_workspace(group.group_id)
        if ws:
            role = "admin" if group.role == "admin" else "reader"
            results.append({"workspace_id": ws, "role": role, "type": "group"})

    # 3. Workspaces where user is explicit member
    for member in get_workspace_memberships(user_id):
        ws = get_workspace(member.workspace_id)
        results.append({"workspace_id": ws, "role": member.role, "type": "explicit"})

    # 4. Public workspace (everyone has read access)
    results.append({"workspace_id": "public", "role": "reader", "type": "public"})

    return results
```

### Tool routing
- File/KB/DB/reminders/workflows always hit `workspace_id` derived from thread_id
- Access checked via `can_access()` before each operation
- Public workspace is read-only unless explicit member with higher role

---

## Identity Flows

### 1) First-time Web User (Individual Workspace)
```python
user_id = "anon:{uuid}"
workspace_id = "ws:{uuid}"
thread_id = "http:{uuid}"

# 1. Create user
INSERT INTO users (user_id) VALUES (user_id);

# 2. Create workspace
INSERT INTO workspaces (workspace_id, type, name, owner_user_id)
VALUES (workspace_id, 'individual', 'My Workspace', user_id);

# 3. Map user to workspace
INSERT INTO user_workspaces (user_id, workspace_id)
VALUES (user_id, workspace_id);

# 4. Map thread to workspace
INSERT INTO thread_workspaces (thread_id, workspace_id)
VALUES (thread_id, workspace_id);
```

### 2) First-time Telegram User (Individual Workspace)
```python
user_id = "tg:{telegram_user_id}"
workspace_id = "ws:{uuid}"
thread_id = "telegram:{chat_id}"

# Same flow as above
```

### 3) Create Group Workspace
```python
group_id = "group:{uuid}"
workspace_id = "ws:{uuid}"

# 1. Create group
INSERT INTO groups (group_id, name) VALUES (group_id, 'Team Alpha');

# 2. Add members
INSERT INTO group_members (group_id, user_id, role) VALUES
  (group_id, 'tg:123', 'admin'),
  (group_id, 'tg:456', 'member');

# 3. Create workspace
INSERT INTO workspaces (workspace_id, type, name, owner_group_id)
VALUES (workspace_id, 'group', 'Team Alpha', group_id);

# 4. Map group to workspace
INSERT INTO group_workspaces (group_id, workspace_id)
VALUES (group_id, workspace_id);

# 5. Telegram group chat routes to this workspace
INSERT INTO thread_workspaces (thread_id, workspace_id)
VALUES ('telegram:group_chat_789', workspace_id);
```

### 4) Create Public Workspace
```python
# One-time setup
INSERT INTO workspaces (workspace_id, type, name, owner_system_id)
VALUES ('public', 'public', 'Public', 'public');

# Everyone can read by default (see access check logic)
# Add editors/admins via workspace_members:
INSERT INTO workspace_members (workspace_id, user_id, role)
VALUES ('public', 'tg:admin_user', 'admin');
```

---

## Merge / Upgrade Flows

### Merge Policy

**Primary goal**: Identity merges are **identity-only** - no data copying.

When merging two identities:
1. **If target has no workspace**: Use source's workspace (identity reassignment only)
2. **If target has a workspace**: Keep target's workspace, archive source's workspace
3. **Never merge two workspaces with data**: Require explicit user decision

Data movement (merging two workspaces) is **out of scope** for automated identity merges. If users want to combine data from two workspaces, this must be an explicit manual operation with user confirmation.

---

### Key Principle: Merge = Identity Mapping Only (No Data Copy)

| Merge Type | What Happens | Data Moved? |
|------------|--------------|-------------|
| **Web anon → Email** | Add alias, keep workspace | ❌ No |
| **Web → Telegram** | Add alias, reassign workspace | ❌ No |
| **Into group workspace** | Add user to group_members | ❌ No |
| **Out of group (unmerge)** | Create new workspace, copy data | ✅ Yes (unavoidable) |
| **Into public workspace** | ❌ Not recommended | — |

### Flow 1: Web Anon Upgrades to Email
```python
# User has: anon:abc123 → ws:xyz789
# User wants to upgrade to email account

new_user_id = "email:user@example.com"
old_user_id = "anon:abc123"

# 1. Create new user
INSERT INTO users (user_id) VALUES (new_user_id);

# 2. Create alias (anon → email)
INSERT INTO user_aliases (alias_id, user_id)
VALUES (old_user_id, new_user_id);

# 3. Reassign workspace ownership
UPDATE user_workspaces
SET user_id = new_user_id
WHERE user_id = old_user_id;

# Result: Email user now owns the workspace, anon is an alias
# All data remains in ws:xyz789
```

### Flow 2: Merge Web into Telegram
```python
# Web user: anon:abc123 → ws:xyz789
# Telegram user: tg:456 → (may or may not have workspace)

# 1. Create alias
INSERT INTO user_aliases (alias_id, user_id)
VALUES ('anon:abc123', 'tg:456');

# 2a. If Telegram has no workspace, adopt anon's workspace
UPDATE user_workspaces
SET user_id = 'tg:456'
WHERE user_id = 'anon:abc123'
  AND workspace_id = 'ws:xyz789';

# 2b. If Telegram HAS a workspace, keep Telegram's workspace
# Archive anon's workspace (user can manually migrate data later if needed)
UPDATE workspaces
SET status = 'archived'
WHERE workspace_id = 'ws:xyz789';

# Result: anon:abc123 now resolves to tg:456
# User accesses tg:456's workspace; anon's workspace is archived
```

### Flow 3: Join Group Workspace
```python
# User wants to join existing group workspace

group_id = "group:existing"
workspace_id = (SELECT workspace_id FROM group_workspaces WHERE group_id = group_id)
user_id = "tg:new_user"

# 1. Add user to group
INSERT INTO group_members (group_id, user_id, role)
VALUES (group_id, user_id, 'member');

# 2. User's threads now have access to group workspace
# (Optional) Move user's thread to group workspace:
UPDATE thread_workspaces
SET workspace_id = workspace_id
WHERE thread_id = 'telegram:user_thread';
```

### Flow 4: Unmerge (Split)
```python
# User wants to separate their data from a group workspace

old_workspace_id = "ws:group_shared"
new_workspace_id = "ws:new:{uuid}"
user_id = "tg:user"

# 1. Create new individual workspace
INSERT INTO workspaces (workspace_id, type, name, owner_user_id)
VALUES (new_workspace_id, 'individual', 'My New Workspace', user_id);

INSERT INTO user_workspaces (user_id, workspace_id)
VALUES (user_id, new_workspace_id);

# 2. Copy data (only way to separate)
# - Files: cp -r data/workspaces/ws:group_shared/files/* data/workspaces/ws:new/files/
# - KB: Copy collections
# - DB: Export/import relevant tables

# 3. Update user's threads to new workspace
# Note: This requires tracking which threads belong to which users.
# In a group workspace, threads may be shared by multiple users.
# Consider adding user_thread ownership tracking if splits are common.

# Alternative: Create new threads for the user in their new workspace
# instead of trying to reassign shared group threads.
```

---

## Migration Note

**This is a clean-slate redesign.** Since there's no production environment with legacy data, no migration from the old `data/users/{thread_id}` structure is required.

Fresh deployments use:
```bash
docker compose down -v  # Clean volumes
docker compose up -d    # Auto-runs migrations/001_initial_schema.sql
```

**OPTIONAL - Importing from external systems:**
If importing data from another system:
1. Derive `user_id` from existing identity
2. Create appropriate workspace(s)
3. Import files/KB/DB data to workspace paths
4. Create `thread_workspaces` routing entries for each conversation

---

## Implementation Checklist

- [ ] Create migration script with all tables
- [ ] Implement WorkspaceStorage abstraction layer
- [ ] Implement access control logic (`can_access()`)
- [ ] Update FileSandbox to use workspace routing
- [ ] Update DBStorage to use workspace routing
- [ ] Update KB tools to use workspace routing
- [ ] Implement merge flows (alias + reassign)
- [ ] Create management CLI for workspace/group operations
- [ ] Add tests for all three workspace types
- [ ] Add tests for role-based permissions
- [ ] Add tests for merge/unmerge flows

---

## Why This Design Works

1. **Three workspace types** - Clear mental model for personal, team, and company data
2. **Role-based permissions** - Simple hierarchy (admin > editor > reader)
3. **Merge is identity-only** - No data copying, just alias updates
4. **Group workspaces** - Multiple users can share a workspace (for group chats)
5. **Public workspace** - Company-wide resources with read-default access
6. **Clean schema** - Proper FKs, constraints, and no ambiguity
7. **Extensible** - ACL allows external sharing beyond members

---

## Peer Review Notes (2026-01-16)

### Strengths
- User-first ownership removes routing ambiguity and makes tool access deterministic.
- Identity upgrades via aliases avoid data copying and keep UX smooth.
- Shared workspace + ACL remains simple and extensible.

### Concerns / Questions
1. **~~Alias resolution precedence~~**: ~~Define whether `user_id` in request is canonical or may be an alias~~ — **FIXED**: Added "Request Identity Resolution" section documenting server-issued user_id and alias resolution via `resolve_user_id()`.
2. **~~Thread ownership drift~~**: ~~If `thread_users.thread_id` is never updated on upgrade~~ — **N/A**: `thread_users` table doesn't exist; routing uses `thread_workspaces` which is stable after merge.
3. **Workspace creation timing**: Decide whether to create workspace eagerly on first interaction or lazily on first tool call (affects storage layout and error paths).
4. **Reminders/workflows scope**: Specify whether these are per-workspace **and** per-thread (e.g., tied to conversation context) or workspace-wide only.
5. **~~Admin model~~**: ~~The plan assumes `ADMIN_USER_IDS` but doesn't specify where user_id is sourced~~ — **FIXED**: Added channel-specific user_id format table and admin configuration via `.env`.
6. **~~Security boundary~~**: ~~Ensure user_id is server-issued and immutable from clients~~ — **FIXED**: Documented in "Request Identity Resolution" - user_id is server-issued only, never from client headers.
7. **~~Schema vs flow mismatch~~**: ~~Merge flow references `thread_users` and `user_threads`~~ — **FIXED**: Removed references to non-existent tables from merge flow examples.
8. **~~Migration note conflict~~**: ~~Document says clean-slate yet includes a migration example~~ — **FIXED**: Clarified as clean-slate with optional import section.
9. **~~ACL permission scope~~**: ~~ACL allows `admin` but `can_access()` doesn't use it~~ — **FIXED**: Added CHECK constraint limiting ACL to `read|write` only; admin via `workspace_members` only.
10. **~~Group role mapping~~**: ~~`group_members.role` uses `admin/member`, but workspace roles are `admin/editor/reader`~~ — **FIXED**: Mapping documented: Group `admin` → workspace `admin`, Group `member` → workspace `reader`.
11. **~~owner_system_id constraints~~**: ~~No FK or validation on `owner_system_id`~~ — **FIXED**: Added CHECK constraint `owner_system_id IS NULL OR owner_system_id = 'public'`.

**Remaining (deferred to future):**
- Workspace creation timing (eager vs lazy)
- Reminders/workflows scope (per-workspace vs per-thread)

### Recommendations
- [x] Add a short "identity resolution" section (canonicalize user_id → resolve alias → lookup workspace_id) — **DONE**
- [x] Add a "shared access policy" line (default read vs ACL-only) — **DONE** (public = read default, ACL for read|write)
- [x] Add a "Merge Policy" rule (identity-only vs data-moving) — **DONE**
- [x] Document role mapping between group roles and workspace roles — **DONE**

---

## Implementation (2026-01-17)

### Overview
Implemented the complete workspace redesign with three workspace types (individual, group, public) and role-based permissions. All storage operations now route through `workspace_id` instead of `thread_id`.

### Files Created

#### 1. `migrations/001_initial_schema.sql` (Consolidated)
Complete database schema in a single file (formerly 7 separate migrations):
- LangGraph checkpoint tables (required by LangGraph PostgresSaver)
- `users`, `user_aliases` - core identity with merge support
- `groups`, `group_members` - for group workspaces
- `workspaces` - supports 3 types via ownership columns with CHECK constraints
- `user_workspaces` - individual workspace mapping
- `group_workspaces` - group workspace mapping
- `thread_workspaces` - routing table (thread_id → workspace_id)
- `workspace_members` - role-based access (admin/editor/reader)
- `workspace_acl` - resource-level sharing (read|write only; admin via members)
- `conversations`, `messages` - chat metadata and audit log
- `workers`, `scheduled_jobs` - orchestrator-spawned workers
- `reminders` - scheduled reminders with recurrence
- `file_paths`, `db_paths`, `user_registry` - ownership tracking
- All foreign keys, indexes, and constraints
- Idempotent: uses `CREATE TABLE IF NOT EXISTS` and `DROP CONSTRAINT IF EXISTS`
- **New CHECK constraints**: `acl_valid_permission`, `valid_system_owner`

#### 2. `src/cassey/storage/workspace_storage.py`
Core workspace abstraction layer with:
```python
# Context management
set_workspace_id(workspace_id: str) -> None
get_workspace_id() -> str | None
clear_workspace_id() -> None

# Path resolution
get_workspace_path(workspace_id: str) -> Path
get_workspace_files_path(workspace_id: str) -> Path
get_workspace_kb_path(workspace_id: str) -> Path
get_workspace_db_path(workspace_id: str) -> Path
get_workspace_mem_path(workspace_id: str) -> Path
get_workspace_reminders_path(workspace_id: str) -> Path
get_workspace_workflows_path(workspace_id: str) -> Path

# Database operations
resolve_user_id(user_id: str, conn) -> str  # Alias to canonical
ensure_user(user_id: str, conn) -> str
ensure_user_workspace(user_id: str, conn) -> str
ensure_thread_workspace(thread_id: str, user_id: str, conn) -> str

# Access control
ROLE_PERMISSIONS = {"admin": {...}, "editor": {...}, "reader": {...}}
can_access(user_id, workspace_id, action, conn) -> bool
accessible_workspaces(user_id, conn) -> list[dict]

# Merge operations
add_alias(alias_id, canonical_user_id, conn) -> None
resolve_alias_chain(user_id, conn) -> str

# Public workspace
ensure_public_workspace(conn) -> str
```

### Files Modified

#### 1. `src/cassey/config/settings.py`
- Added `WORKSPACES_ROOT` setting
- Added workspace path methods:
  - `get_workspace_root(workspace_id)`
  - `get_workspace_files_path(workspace_id)`
  - `get_workspace_kb_path(workspace_id)`
  - `get_workspace_db_path(workspace_id)`
  - `get_workspace_mem_path(workspace_id)`
  - `get_workspace_reminders_path(workspace_id)`
  - `get_workspace_workflows_path(workspace_id)`

#### 2. `src/cassey/storage/file_sandbox.py`
- Added import: `from cassey.storage.workspace_storage import get_workspace_id`
- Updated `get_sandbox()` priority:
  1. `user_id` (explicit, backward compatibility)
  2. `workspace_id` from context (new workspace routing)
  3. `thread_id` from context (legacy thread routing)
  4. global sandbox fallback

#### 3. `src/cassey/storage/db_storage.py`
- Added import: `from cassey.storage.workspace_storage import get_workspace_id`
- Updated `_get_db_path()` to accept `workspace_id` parameter
- Priority: `workspace_id` → `thread_id` for path resolution

#### 4. `src/cassey/storage/seekdb_storage.py`
- Added import: `from cassey.storage.workspace_storage import get_workspace_id`
- Added `_get_storage_id()` helper function
- Added `get_kb_storage_dir()` function
- All functions updated to support `workspace_id` parameter:
  - `get_seekdb_client(thread_id, workspace_id)`
  - `list_seekdb_collections(thread_id, workspace_id)`
  - `get_seekdb_collection(thread_id, name, workspace_id)`
  - `create_seekdb_collection(thread_id, name, embedding_function, workspace_id)`

#### 5. `src/cassey/storage/kb_tools.py`
- Added import: `from cassey.storage.workspace_storage import get_workspace_id`
- Added `_get_storage_id()` helper function
- Updated all KB tools to use workspace-aware storage:
  - `create_kb_collection()`
  - `search_kb()`
  - `describe_kb_collection()`
  - `drop_kb_collection()`
  - `delete_kb_documents()`
  - `add_kb_documents()`

#### 6. `src/cassey/channels/base.py`
- Added imports:
  ```python
  from cassey.storage.workspace_storage import (
      ensure_thread_workspace,
      set_workspace_id as set_workspace_context,
      clear_workspace_id as clear_workspace_context,
  )
  ```
- Updated `stream_agent_response()` to:
  1. Call `ensure_thread_workspace(thread_id, user_id)` to get/create workspace
  2. Set `workspace_id` context via `set_workspace_context()`
  3. Clear all contexts (thread_id, user_id, workspace_id) in finally block

### Storage Layout
```
data/workspaces/
  {workspace_id}/
    files/
    kb/
    db/
    mem/
    reminders/
    workflows/
```

### Routing Priority (in all tools)
1. **workspace_id** from context (new, primary)
2. **thread_id** from context (legacy, fallback)

This ensures backward compatibility while enabling the new workspace-based routing.

### Migration Consolidation (2026-01-17)

All migration scripts have been consolidated into a single `migrations/001_initial_schema.sql` file for cleaner deployment:

**Before:** 7 separate migration files (001-007)
**After:** 1 consolidated initial schema

**Key changes:**
- All tables created in their final state (no `ALTER TABLE ... ADD` statements)
- Only `ALTER TABLE` statements remaining are for FK constraints with `DROP CONSTRAINT IF EXISTS` (for safe re-runs)
- Old migration files removed:
  - `002_reminders.sql`
  - `003_workers.sql`
  - `004_scheduled_jobs.sql`
  - `005_structured_summary.sql`
  - `006_drop_legacy_summary.sql`
  - `007_workspaces.sql` → merged into `001_initial_schema.sql`

**Consolidated schema includes:**
- LangGraph checkpoint tables (required by LangGraph PostgresSaver)
- User identity: `users`, `user_aliases`
- Groups: `groups`, `group_members`
- Workspaces: `workspaces`, `user_workspaces`, `group_workspaces`, `thread_workspaces`
- Access control: `workspace_members`, `workspace_acl`
- Conversations: `conversations`, `messages`
- Workers & jobs: `workers`, `scheduled_jobs`
- Ownership tracking: `file_paths`, `db_paths`, `user_registry`
- Reminders: `reminders`

### Next Steps for Deployment

1. **Fresh deployment with Docker:**
   ```bash
   docker compose down -v  # Clean volumes
   docker compose up -d    # Auto-runs migrations via /docker-entrypoint-initdb.d
   ```

   Docker-compose mounts `./migrations:/docker-entrypoint-initdb.d:ro`, which automatically runs all `.sql` files on first startup.

2. **Manual migration (alternative):**
   ```bash
   psql -U cassey -d cassey_db -f migrations/001_initial_schema.sql
   ```

3. **Restart Cassey** to pick up the code changes

4. **Verify workspace creation:**
   - New users will automatically get individual workspaces
   - Existing threads will be mapped to workspaces on first interaction

5. **Optional - Create public workspace:**
   ```python
   from cassey.storage.workspace_storage import ensure_public_workspace
   await ensure_public_workspace()
   ```

### Implementation Checklist Status

- [x] Create migration script with all tables
- [x] Consolidate migrations into single initial schema (no ALTER TABLE ... ADD)
- [x] Implement WorkspaceStorage abstraction layer
- [x] Implement access control logic (`can_access()`)
- [x] Update FileSandbox to use workspace routing
- [x] Update DBStorage to use workspace routing
- [x] Update KB tools to use workspace routing
- [x] Integrate workspace setup in channels
- [ ] Create management CLI for workspace/group operations
- [ ] Add tests for all three workspace types
- [ ] Add tests for role-based permissions
- [ ] Add tests for merge/unmerge flows

---

## Schema Refinements (2026-01-17)

Incorporated peer review feedback with the following refinements:

### 1. ACL Permission Scope
**Issue**: ACL allowed `admin` permission but access control didn't use it.
**Fix**: Added CHECK constraint limiting ACL to `read|write` only.
```sql
CONSTRAINT acl_valid_permission CHECK (permission IN ('read', 'write'))
```
Admin privileges are granted exclusively through `workspace_members` entries.

### 2. owner_system_id Validation
**Issue**: No validation on `owner_system_id` values.
**Fix**: Added CHECK constraint to only allow `"public"`:
```sql
CONSTRAINT valid_system_owner CHECK (
  owner_system_id IS NULL OR owner_system_id = 'public'
)
```

### 3. Merge Flow Documentation
**Issue**: Examples referenced non-existent tables (`thread_users`, `user_threads`).
**Fix**: Updated all merge flow examples to use actual schema (`thread_workspaces`).

### 4. Clean-Slate Migration Note
**Issue**: Document claimed clean-slate but included detailed migration examples.
**Fix**: Clarified as true clean-slate with brief optional import section.

### 5. Request Identity Resolution
**Issue**: No documentation on how `user_id` is derived from HTTP/Telegram requests.
**Fix**: Added "Request Identity Resolution" section documenting:
- Channel-specific user_id formats (`tg:*`, `email:*`, `anon:*`)
- Server-issued only (never from client headers)
- Alias resolution flow
- Security requirements

### 6. Admin Configuration
Admins are configured via environment variable:
```bash
# .env
ADMIN_USER_IDS=tg:123456,tg:789012,email:admin@example.com
```
- Server-controlled (cannot be forged by clients)
- Environment-specific (different admins per environment)
- No database dependency for bootstrapping

### 7. Merge Policy
**Issue**: Merge flow conflicted with "identity-only" principle.
**Fix**: Added explicit "Merge Policy" section:
- Identity merges are identity-only (no data copying)
- If target has no workspace: adopt source's workspace
- If target has workspace: archive source's workspace
- Data merging requires explicit user decision (out of scope for automated merges)

### 8. Group Role Mapping
Explicitly documented in peer review:
| Group Role | Workspace Role |
|------------|----------------|
| admin | admin |
| member | reader |

Group membership provides read-only access by default; write access requires explicit `workspace_members` entry.

---

## Final Review Checklist (2026-01-16 22:30)

- [x] All tables created in final state (no ALTER TABLE ... ADD)
- [x] CHECK constraints on critical fields (ACL permissions, owner_system_id)
- [x] Foreign keys with CASCADE where appropriate
- [x] Merge flows reference correct schema
- [x] Merge policy: identity-only (archive rather than data copy)
- [x] Request identity resolution documented
- [x] Documentation matches implementation
- [x] Admin model defined (.env based)
- [x] Storage routing: workspace_id → thread_id fallback
- [x] ACL scope limited to read/write (admin via members only)
- [x] Group role mapping documented (admin→admin, member→reader)
