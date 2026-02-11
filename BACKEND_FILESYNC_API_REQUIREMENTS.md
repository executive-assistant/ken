# Backend File Sync API Requirements (Desktop POC/MVP)

This document defines the exact API contract the current desktop app expects for file sync.

## Scope

Required immediately to unblock current desktop GUI errors:

1. `GET /files/manifest`
2. `GET /files/download`

## 1) GET `/files/manifest`

Purpose: incremental file sync feed per thread.

### Request

- Method: `GET`
- Path: `/files/manifest`
- Query params:
- `thread_id` (required, string)
- `cursor` (optional, string; fetch changes after this cursor)
- Headers:
- `Authorization: Bearer <token>` (desktop sends when token exists)

### Success Response

- Status: `200 OK`
- Content-Type: `application/json`
- Body schema:

```json
{
  "items": [
    {
      "path": "docs/a.txt",
      "tombstone": false,
      "cursor": "c_000123"
    }
  ],
  "next_cursor": "c_000123",
  "has_more": false,
  "server_time_utc": "2026-02-11T10:41:39Z"
}
```

### Field Rules

- `items` is required array.
- Each item:
- `path` required, relative path only.
- `tombstone` boolean. If `true`, desktop deletes local file.
- `cursor` optional but strongly recommended per item.
- `has_more` is required boolean.
- If `has_more=true`, `next_cursor` must be present and non-empty.
- `next_cursor` must be monotonic per `thread_id`.
- Cursor must advance; do not return an endless cursor loop.

### Error Responses

- `400` invalid params
- `401`/`403` auth failure
- `404` thread not found (or return empty manifest by backend policy)
- `429` rate limited
- `5xx` transient server errors

Recommended error body shape:

```json
{
  "code": "invalid_cursor",
  "message": "Cursor not found",
  "retryable": false,
  "details": {}
}
```

## 2) GET `/files/download`

Purpose: fetch raw file bytes for a manifest item.

### Request

- Method: `GET`
- Path: `/files/download`
- Query params:
- `thread_id` (required, string)
- `path` (required, string; relative path)
- Headers:
- `Authorization: Bearer <token>` (desktop sends when token exists)

### Success Response

- Status: `200 OK`
- Body: raw binary file bytes
- Content-Type: `application/octet-stream` (or concrete MIME type)
- Optional: `ETag` header (recommended)

### Error Responses

- `400` invalid path/thread_id
- `401`/`403` auth failure
- `404` file not found or tombstoned
- `429` rate limited
- `5xx` transient server errors

### Security Rules

- Reject path traversal (`..`) and absolute paths.

## Desktop Compatibility Notes

- Canonical response keys should use snake_case:
- `next_cursor`
- `has_more`
- `server_time_utc`
- `tombstone`
- `cursor`

The desktop parser tolerates some aliases, but canonical snake_case is preferred for consistency.

## Definition of Done (Backend)

1. `curl -i "http://127.0.0.1:8000/files/manifest?thread_id=thread-default"` returns `200` and valid schema.
2. At least one non-tombstone item can be downloaded via `/files/download`.
3. Manifest pagination using `cursor` advances correctly and terminates with `has_more=false`.

## Current Observed Gap (as of 2026-02-11)

- `GET /health` returns `200 OK`.
- `GET /files/manifest` returns `404 Not Found`.
- `GET /files/download` returns `404 Not Found`.

These missing routes are the direct cause of current File Sync errors in the desktop GUI.
