# Executive Assistant API Contract v1.0

API contract for Executive Assistant, designed for desktop app integration.

## Base Configuration

```
Base URL: http://localhost:8000/api/v1
Content-Type: application/json
Authentication: None (localhost only) or X-Local-Token header
```

---

## Message

### POST /message

Send a message to your Executive Assistant.

**Request:**
```json
{
  "message": "string",
  "stream": false,
  "user_id": "string (optional, default: 'default')",
  "thread_id": "string (optional)"
}
```

**Response:**
```json
{
  "content": "string",
  "thread_id": "string"
}
```

### POST /message/stream

Send a message with streaming response (SSE).

**Request:**
```json
{
  "message": "string",
  "user_id": "string (optional)"
}
```

**Response:** Server-Sent Events stream
```
data: {"chunk": "partial content"}
data: {"chunk": "more content"}
data: [THREAD:thread-id]
data: [DONE]
```

---

## Summarize

### POST /summarize

Summarize text (utility endpoint, bypasses agent).

**Request:**
```json
{
  "text": "string",
  "max_length": 200
}
```

**Response:**
```json
{
  "summary": "string"
}
```

---

## Thread Management

### GET /thread

Get current thread status for a user.

**Query:** `user_id` (optional)

**Response:**
```json
{
  "thread_id": "string",
  "status": "idle | running | waiting",
  "last_activity": "2025-02-15T10:30:00Z",
  "message_count": 10
}
```

### GET /thread/runs

List all runs for the thread.

**Query:** `user_id`, `limit` (default: 20)

**Response:**
```json
{
  "runs": [
    {
      "run_id": "string",
      "status": "completed | running | failed | cancelled",
      "created_at": "2025-02-15T10:30:00Z",
      "completed_at": "2025-02-15T10:30:05Z"
    }
  ],
  "has_more": false
}
```

### GET /thread/runs/{run_id}

Get details of a specific run.

**Response:**
```json
{
  "run_id": "string",
  "status": "completed",
  "created_at": "2025-02-15T10:30:00Z",
  "completed_at": "2025-02-15T10:30:05Z",
  "result": {
    "content": "string",
    "tools_used": ["web_scrape", "memory_add"]
  }
}
```

### POST /thread/runs/{run_id}/cancel

Cancel a running task.

**Response:**
```json
{
  "status": "cancelled",
  "run_id": "string"
}
```

---

## Memory

### GET /memory

Search memories.

**Query:**
- `query` (required): Search query
- `type` (optional): `semantic | episodic | procedural`
- `limit` (optional, default: 10)
- `min_confidence` (optional, default: 0.5)

**Response:**
```json
{
  "memories": [
    {
      "id": "string",
      "content": "string",
      "type": "semantic",
      "confidence": 0.9,
      "source": "learned",
      "created_at": "2025-02-15T10:30:00Z",
      "last_accessed": "2025-02-15T12:00:00Z"
    }
  ],
  "total": 5
}
```

### POST /memory

Create a new memory.

**Request:**
```json
{
  "content": "string",
  "type": "semantic | episodic | procedural",
  "confidence": 0.9,
  "source": "explicit"
}
```

**Response:**
```json
{
  "id": "string",
  "status": "created"
}
```

### PUT /memory/{id}

Update an existing memory.

**Request:**
```json
{
  "content": "string",
  "confidence": 0.95
}
```

**Response:**
```json
{
  "id": "string",
  "status": "updated"
}
```

### DELETE /memory/{id}

Delete a memory.

**Response:**
```json
{
  "status": "deleted"
}
```

### GET /memory/export

Export all memories for backup.

**Query:** `min_confidence` (optional)

**Response:**
```json
{
  "exported_at": "2025-02-15T10:30:00Z",
  "memories": [...],
  "count": 50
}
```

### POST /memory/import

Import memories from backup.

**Request:**
```json
{
  "memories": [...],
  "merge": true
}
```

**Response:**
```json
{
  "imported": 45,
  "skipped": 5
}
```

---

## Journal

### GET /journal

Get journal entries.

**Query:**
- `from` (optional): Start date
- `to` (optional): End date
- `tags` (optional): Comma-separated tags
- `limit` (optional, default: 20)

**Response:**
```json
{
  "entries": [
    {
      "id": "string",
      "content": "string",
      "tags": ["work", "meeting"],
      "mood": "productive",
      "timestamp": "2025-02-15T10:30:00Z"
    }
  ],
  "has_more": false
}
```

### POST /journal

Create a journal entry.

**Request:**
```json
{
  "content": "string",
  "tags": ["string"],
  "mood": "string (optional)"
}
```

**Response:**
```json
{
  "id": "string",
  "status": "created"
}
```

### PUT /journal/{id}

Update a journal entry.

**Request:**
```json
{
  "content": "string",
  "tags": ["string"]
}
```

**Response:**
```json
{
  "status": "updated"
}
```

### DELETE /journal/{id}

Delete a journal entry.

**Response:**
```json
{
  "status": "deleted"
}
```

### GET /journal/summaries

Get roll-up summaries.

**Query:** `period` = `hourly | daily | weekly | monthly | yearly`

**Response:**
```json
{
  "summaries": [
    {
      "period_start": "2025-02-15T10:00:00Z",
      "entry_count": 5,
      "summary": "string",
      "themes": ["work", "project-x"]
    }
  ]
}
```

---

## Todos

### GET /todos

List all todos.

**Query:** `status` = `pending | completed | all`

**Response:**
```json
{
  "todos": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "status": "pending",
      "priority": "high | medium | low",
      "due_date": "2025-02-20T00:00:00Z",
      "created_at": "2025-02-15T10:30:00Z"
    }
  ]
}
```

### POST /todos

Create a todo.

**Request:**
```json
{
  "title": "string",
  "description": "string (optional)",
  "priority": "medium",
  "due_date": "2025-02-20T00:00:00Z (optional)"
}
```

**Response:**
```json
{
  "id": "string",
  "status": "created"
}
```

### PUT /todos/{id}

Update a todo.

**Request:**
```json
{
  "title": "string",
  "status": "completed",
  "priority": "high"
}
```

**Response:**
```json
{
  "status": "updated"
}
```

### DELETE /todos/{id}

Delete a todo.

**Response:**
```json
{
  "status": "deleted"
}
```

---

## Reminders

### GET /reminders

List all reminders.

**Query:** `status` = `pending | completed | all`

**Response:**
```json
{
  "reminders": [
    {
      "id": "string",
      "message": "string",
      "trigger_at": "2025-02-15T14:00:00Z",
      "status": "pending",
      "repeat": "none | daily | weekly | monthly"
    }
  ]
}
```

### POST /reminders

Create a reminder.

**Request:**
```json
{
  "message": "string",
  "trigger_at": "2025-02-15T14:00:00Z",
  "repeat": "none"
}
```

**Response:**
```json
{
  "id": "string",
  "status": "created"
}
```

### DELETE /reminders/{id}

Cancel a reminder.

**Response:**
```json
{
  "status": "cancelled"
}
```

---

## Notes

### GET /notes

List/search notes.

**Query:**
- `search` (optional): Search query
- `limit` (optional, default: 20)

**Response:**
```json
{
  "notes": [
    {
      "id": "string",
      "title": "string",
      "content": "string",
      "tags": ["string"],
      "created_at": "2025-02-15T10:30:00Z",
      "updated_at": "2025-02-15T12:00:00Z"
    }
  ]
}
```

### POST /notes

Create a note.

**Request:**
```json
{
  "title": "string",
  "content": "string",
  "tags": ["string"]
}
```

**Response:**
```json
{
  "id": "string",
  "status": "created"
}
```

### PUT /notes/{id}

Update a note.

**Request:**
```json
{
  "title": "string",
  "content": "string",
  "tags": ["string"]
}
```

**Response:**
```json
{
  "status": "updated"
}
```

### DELETE /notes/{id}

Delete a note.

**Response:**
```json
{
  "status": "deleted"
}
```

---

## Passwords (Encrypted Vault)

### GET /passwords

List saved credentials (passwords not returned).

**Response:**
```json
{
  "credentials": [
    {
      "id": "string",
      "service": "github.com",
      "username": "user@example.com",
      "created_at": "2025-02-15T10:30:00Z",
      "last_used": "2025-02-15T12:00:00Z"
    }
  ]
}
```

### POST /passwords

Save a credential.

**Request:**
```json
{
  "service": "string",
  "username": "string",
  "password": "string",
  "notes": "string (optional)"
}
```

**Response:**
```json
{
  "id": "string",
  "status": "created"
}
```

### GET /passwords/{id}

Retrieve a credential (requires re-authentication).

**Query:** `master_password` or session token

**Response:**
```json
{
  "service": "string",
  "username": "string",
  "password": "string",
  "notes": "string"
}
```

### DELETE /passwords/{id}

Delete a credential.

**Response:**
```json
{
  "status": "deleted"
}
```

---

## Bookmarks

### GET /bookmarks

List bookmarks.

**Query:** `tag` (optional)

**Response:**
```json
{
  "bookmarks": [
    {
      "id": "string",
      "url": "https://example.com",
      "title": "string",
      "description": "string",
      "tags": ["reference", "docs"],
      "created_at": "2025-02-15T10:30:00Z"
    }
  ]
}
```

### POST /bookmarks

Save a bookmark.

**Request:**
```json
{
  "url": "string",
  "title": "string (optional)",
  "description": "string (optional)",
  "tags": ["string"]
}
```

**Response:**
```json
{
  "id": "string",
  "status": "created"
}
```

### DELETE /bookmarks/{id}

Delete a bookmark.

**Response:**
```json
{
  "status": "deleted"
}
```

---

## Check-in

### GET /checkin/status

Get check-in configuration and next scheduled time.

**Response:**
```json
{
  "enabled": true,
  "interval_minutes": 30,
  "next_checkin": "2025-02-15T11:00:00Z",
  "last_checkin": "2025-02-15T10:30:00Z"
}
```

### POST /checkin/trigger

Manually trigger a check-in.

**Response:**
```json
{
  "message": "You have 3 pending tasks and a meeting in 1 hour.",
  "has_items": true
}
```

---

## Configuration

### GET /config

Get app-level configuration.

**Response:**
```json
{
  "memory": {
    "confidence_min": 0.7,
    "max_memories_context": 20,
    "enable_auto_learn": true
  },
  "journal": {
    "enabled": true,
    "auto_rollup": true
  },
  "checkin": {
    "enabled": true,
    "interval_minutes": 30
  },
  "agent": {
    "temperature": 0.7,
    "max_tokens": 4096
  }
}
```

### PUT /config

Update configuration.

**Request:**
```json
{
  "memory": {...},
  "journal": {...},
  "checkin": {...}
}
```

**Response:**
```json
{
  "status": "updated"
}
```

---

## MCP Configuration

### GET /mcp

List configured MCP servers (shared + user).

**Response:**
```json
{
  "servers": [
    {
      "name": "filesystem",
      "source": "shared | user",
      "transport": "stdio | sse | http",
      "url": "string (optional)",
      "enabled": true,
      "tools": ["read_file", "write_file"]
    }
  ]
}
```

### GET /mcp/shared

Get shared/team MCP configuration.

**Response:**
```json
{
  "config": {
    "servers": {
      "filesystem": {
        "command": "mcp-filesystem",
        "args": ["/data"]
      }
    }
  }
}
```

### GET /mcp/user

Get user's personal MCP configuration.

**Response:**
```json
{
  "config": {
    "servers": {
      "github": {
        "url": "https://mcp.github.com/sse",
        "headers": {"Authorization": "Bearer ***"}
      }
    }
  }
}
```

### PUT /mcp/user

Update user's MCP configuration.

**Request:**
```json
{
  "config": {
    "servers": {
      "server-name": {
        "command": "string (for stdio)",
        "url": "string (for http/sse)",
        "headers": {"key": "value"},
        "env": {"VAR": "value"}
      }
    }
  }
}
```

**Response:**
```json
{
  "status": "updated",
  "servers_added": 1,
  "servers_removed": 0
}
```

### POST /mcp/test

Test connection to an MCP server.

**Request:**
```json
{
  "name": "string",
  "config": {...}
}
```

**Response:**
```json
{
  "success": true,
  "tools_available": ["tool1", "tool2"],
  "latency_ms": 150
}
```

---

## Skills

### GET /skills

List available skills.

**Query:** `source` = `all | built-in | user | team`

**Response:**
```json
{
  "skills": [
    {
      "name": "coding",
      "description": "string",
      "source": "built-in | user | team",
      "path": "/skills/coding/SKILL.md",
      "enabled": true,
      "created_at": "2025-02-15T10:30:00Z"
    }
  ]
}
```

### GET /skills/{name}

Get skill content.

**Response:**
```json
{
  "name": "string",
  "source": "user",
  "content": "# Skill Name\n\n...",
  "metadata": {
    "version": "1.0.0",
    "tags": ["coding", "debugging"]
  }
}
```

### POST /skills

Create a new user skill.

**Request:**
```json
{
  "name": "string",
  "content": "# Skill Name\n\n## Instructions\n...",
  "metadata": {
    "version": "1.0.0",
    "tags": ["string"]
  }
}
```

**Response:**
```json
{
  "name": "string",
  "status": "created",
  "path": "/user/skills/my-skill/SKILL.md"
}
```

### PUT /skills/{name}

Update a user skill.

**Request:**
```json
{
  "content": "# Updated Skill\n\n...",
  "metadata": {...}
}
```

**Response:**
```json
{
  "status": "updated"
}
```

### DELETE /skills/{name}

Delete a user skill.

**Response:**
```json
{
  "status": "deleted"
}
```

### POST /skills/generate

Generate skill from patterns (HITL required).

**Request:**
```json
{
  "name": "string",
  "description": "string",
  "from_patterns": true,
  "pattern_types": ["semantic", "procedural"]
}
```

**Response:**
```json
{
  "id": "string",
  "status": "pending_approval",
  "preview": "# Generated Skill\n\n## Instructions\n\n...",
  "patterns_used": 5
}
```

### POST /skills/generate/{id}/confirm

Confirm and create generated skill.

**Request:**
```json
{
  "modify_content": "string (optional edits)"
}
```

**Response:**
```json
{
  "status": "created",
  "name": "string",
  "path": "/user/skills/my-skill/SKILL.md"
}
```

### POST /skills/generate/{id}/reject

Reject generated skill.

**Response:**
```json
{
  "status": "rejected"
}
```

### POST /skills/{name}/enable

Enable/disable a skill.

**Request:**
```json
{
  "enabled": true
}
```

**Response:**
```json
{
  "status": "updated"
}
```

---

## System

### GET /health

Health check.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "postgres": "connected",
  "ollama": "available"
}
```

### GET /models

List available LLM models.

**Response:**
```json
{
  "models": [
    {
      "provider": "ollama",
      "model": "qwen3-coder-next",
      "available": true
    },
    {
      "provider": "openai",
      "model": "gpt-4o-mini",
      "available": true
    }
  ]
}
```

---

## Error Responses

All endpoints return consistent error format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request body",
    "details": {...}
  }
}
```

**Common error codes:**
- `VALIDATION_ERROR` - Invalid request
- `NOT_FOUND` - Resource not found
- `UNAUTHORIZED` - Authentication required
- `RATE_LIMITED` - Too many requests
- `INTERNAL_ERROR` - Server error
