"""End-to-end smoke execution for every registered tool.

This suite ensures each runtime tool can be invoked at least once with
deterministic inputs and without unhandled exceptions.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
from dataclasses import dataclass
from uuid import uuid4

import pytest

from executive_assistant.storage.thread_storage import clear_thread_id, set_thread_id
from executive_assistant.tools.registry import clear_mcp_cache, get_all_tools


@dataclass
class _ToolRunState:
    suffix: str
    base_dir: str
    seed_file: str
    csv_file: str
    moved_file: str
    folder: str
    renamed_folder: str
    tdb_table: str
    tdb_delete_table: str
    tdb_export_table: str
    tdb_alter_table: str
    tdb_export_file: str
    adb_table: str
    adb_import_table: str
    adb_export_file: str
    vdb_collection: str
    reminder_id: str | None = None
    memory_id: str | None = None
    instinct_id: str | None = None
    draft_id: str | None = None


def _tool_name(tool: object) -> str:
    return getattr(tool, "name", None) or getattr(tool, "__name__", "")


async def _invoke_tool(tool: object, args: dict) -> object:
    if hasattr(tool, "ainvoke"):
        return await tool.ainvoke(args)
    if inspect.iscoroutinefunction(tool):
        return await tool(**args)
    return tool(**args)


def _schema_for(tool: object) -> tuple[list[str], dict]:
    args_schema = getattr(tool, "args_schema", None)
    if args_schema is None:
        return [], {}
    try:
        schema = args_schema.model_json_schema()
    except Exception:
        return [], {}
    required = schema.get("required", []) or []
    props = schema.get("properties", {}) or {}
    return required, props


def _sample_value(field: str, prop_schema: dict, state: _ToolRunState) -> object:
    enum_values = prop_schema.get("enum")
    if enum_values:
        return enum_values[0]

    field_l = field.lower()
    field_map = {
        "file_path": state.seed_file,
        "source": state.seed_file,
        "destination": state.moved_file,
        "folder_path": state.folder,
        "old_path": state.folder,
        "new_path": state.renamed_folder,
        "pattern": "*",
        "directory": state.base_dir,
        "table_name": state.tdb_table,
        "sql": f"SELECT * FROM {state.tdb_table} LIMIT 5",
        "columns": "name,status",
        "filename": state.tdb_export_file,
        "column_name": "status_note",
        "column_type": "TEXT",
        "csv_file": state.csv_file,
        "output_file": state.adb_export_file,
        "query": "tool smoke query",
        "skill_name": "material-design-3",
        "name": f"tool_name_{state.suffix}",
        "description": "tool smoke description",
        "content": "tool smoke content",
        "collection_name": state.vdb_collection,
        "document_id": "doc-1",
        "key": f"key_{state.suffix}",
        "time": "in 10 minutes",
        "message": f"reminder_{state.suffix}",
        "timezone": "UTC",
        "role": "tester",
        "responsibilities": "testing",
        "communication_preference": "concise",
        "trigger": "when testing",
        "action": "log result",
        "domain": "testing",
        "context": "test context",
        "instinct_id": state.instinct_id or "missing-instinct-id",
        "delta": 0.05,
        "draft_id": state.draft_id or "missing-draft-id",
        "json_data": "[]",
        "profile_id": "analyst",
        "instincts_json": "[]",
        "every": "1h",
        "lookback": "24h",
        "start": "00:00",
        "end": "23:59",
        "days": "Mon,Tue,Wed,Thu,Fri,Sat,Sun",
        "verification_id": "missing-verification-id",
        "response": "yes",
        "task_type": "analysis",
        "what_went_well": "clear output",
        "what_could_be_better": "faster",
        "suggestion_id": "missing-suggestion-id",
        "pattern_type": "workflow",
        "instruction": "extract key information",
        "code": "print('tool_smoke_ok')",
        "url": "https://example.com",
        "formats": "markdown",
        "limit": 2,
        "num_results": 2,
        "sources": "web",
        "scrape_results": False,
        "job_id": "job-smoke-id",
        "mode": "default",
        "server_name": f"srv_{state.suffix}",
        "command": "echo",
        "args": [],
        "env": {},
        "arguments": "--help",
        "headers": "{}",
        "config_json": "{\"mcpServers\":{}}",
        "load_skills": False,
        "details": "tool smoke details",
    }
    if field in field_map:
        return field_map[field]

    value_type = prop_schema.get("type")
    if value_type == "boolean":
        return True
    if value_type == "integer":
        return 1
    if value_type == "number":
        return 1.0
    if value_type == "array":
        return []
    if value_type == "object":
        return {}
    if "url" in field_l:
        return "https://example.com"
    if "time" in field_l:
        return "in 10 minutes"
    if "id" in field_l:
        return f"id_{state.suffix}"
    return f"{field}_{state.suffix}"


async def _safe_call(tool_map: dict[str, object], name: str, args: dict) -> str:
    tool = tool_map.get(name)
    if tool is None:
        return ""
    try:
        result = await asyncio.wait_for(_invoke_tool(tool, args), timeout=25)
        return str(result)
    except Exception as exc:  # pragma: no cover - defensive guard for setup phase
        return f"setup_error:{type(exc).__name__}:{exc}"


def _extract_memory_id(output: str) -> str | None:
    match = re.search(r"(?:ID:\s*|Memory (?:saved|created|updated):\s*)([0-9a-fA-F-]{8,36})", output)
    return match.group(1) if match else None


def _extract_reminder_id(output: str) -> str | None:
    match = re.search(r"ID:\s*(\d+)", output)
    return match.group(1) if match else None


def _extract_instinct_id(output: str) -> str | None:
    match = re.search(r"Instinct created:\s*([0-9a-fA-F-]{8,})", output)
    return match.group(1) if match else None


def _extract_draft_id(output: str) -> str | None:
    match = re.search(r"Draft ID:\s*([0-9a-fA-F-]+)", output)
    return match.group(1) if match else None


async def _prepare_for_tool(name: str, tool_map: dict[str, object], state: _ToolRunState) -> None:
    # Always ensure baseline files exist for file/ADB imports.
    await _safe_call(
        tool_map,
        "write_file",
        {"file_path": state.seed_file, "content": "seed content"},
    )
    await _safe_call(
        tool_map,
        "write_file",
        {"file_path": state.csv_file, "content": "name,score\nalice,10\nbob,20\n"},
    )
    await _safe_call(tool_map, "create_folder", {"folder_path": state.folder})

    if name in {"insert_tdb_table", "query_tdb", "list_tdb_tables", "describe_tdb_table"}:
        await _safe_call(tool_map, "create_tdb_table", {"table_name": state.tdb_table, "columns": "name,status"})
        await _safe_call(
            tool_map,
            "insert_tdb_table",
            {"table_name": state.tdb_table, "data": [{"name": "alice", "status": "ok"}]},
        )

    if name == "delete_tdb_table":
        await _safe_call(tool_map, "create_tdb_table", {"table_name": state.tdb_delete_table, "columns": "name,status"})

    if name == "export_tdb_table":
        await _safe_call(tool_map, "create_tdb_table", {"table_name": state.tdb_export_table, "columns": "name,status"})
        await _safe_call(
            tool_map,
            "insert_tdb_table",
            {"table_name": state.tdb_export_table, "data": [{"name": "export", "status": "ok"}]},
        )

    if name == "import_tdb_table":
        await _safe_call(tool_map, "export_tdb_table", {"table_name": state.tdb_export_table, "filename": state.tdb_export_file})

    if name in {"add_tdb_column", "drop_tdb_column"}:
        await _safe_call(tool_map, "create_tdb_table", {"table_name": state.tdb_alter_table, "columns": "name,status"})

    if name in {"describe_adb_table", "export_adb_table", "query_adb"}:
        await _safe_call(
            tool_map,
            "create_adb_table",
            {"table_name": state.adb_table, "data": [{"name": "alice", "score": 10}]},
        )

    if name == "drop_adb_table":
        await _safe_call(
            tool_map,
            "create_adb_table",
            {"table_name": state.adb_import_table, "data": [{"name": "dropme", "score": 1}]},
        )

    if name in {"create_vdb_collection", "search_vdb", "describe_vdb_collection", "add_vdb_documents", "update_vdb_document", "delete_vdb_documents", "add_file_to_vdb"}:
        await _safe_call(
            tool_map,
            "create_vdb_collection",
            {"collection_name": state.vdb_collection, "content": "alpha beta gamma"},
        )

    if name in {"update_memory", "delete_memory", "forget_memory", "get_memory_by_key", "get_memory_at_time", "get_memory_history"} and not state.memory_id:
        out = await _safe_call(
            tool_map,
            "create_memory",
            {"content": f"memory_{state.suffix}", "memory_type": "preference", "key": f"key_{state.suffix}"},
        )
        state.memory_id = _extract_memory_id(out)

    if name in {"adjust_instinct_confidence", "disable_instinct", "enable_instinct"} and not state.instinct_id:
        out = await _safe_call(
            tool_map,
            "create_instinct",
            {"trigger": "when testing", "action": "respond clearly", "domain": "workflow"},
        )
        state.instinct_id = _extract_instinct_id(out)

    if name in {"approve_evolved_skill"} and not state.draft_id:
        evolve_out = await _safe_call(tool_map, "evolve_instincts", {})
        state.draft_id = _extract_draft_id(evolve_out)

    if name in {"reminder_cancel", "reminder_edit"} and not state.reminder_id:
        out = await _safe_call(
            tool_map,
            "reminder_set",
            {"message": f"tool_reminder_{state.suffix}", "time": "in 15 minutes", "timezone": "UTC"},
        )
        state.reminder_id = _extract_reminder_id(out)


def _build_args_for_tool(name: str, tool: object, state: _ToolRunState) -> dict:
    required, props = _schema_for(tool)
    args = {field: _sample_value(field, props.get(field, {}), state) for field in required}

    # Per-tool deterministic overrides (including optional args for stronger behavior checks).
    overrides: dict[str, dict] = {
        "read_file": {"file_path": state.seed_file},
        "write_file": {"file_path": state.seed_file, "content": f"updated_{state.suffix}"},
        "list_files": {"directory": state.base_dir, "recursive": True},
        "create_folder": {"folder_path": state.folder},
        "delete_folder": {"folder_path": state.renamed_folder},
        "delete_file": {"file_path": state.moved_file},
        "rename_folder": {"old_path": state.folder, "new_path": state.renamed_folder},
        "move_file": {"source": state.seed_file, "destination": state.moved_file},
        "glob_files": {"pattern": "*.txt", "directory": state.base_dir},
        "grep_files": {"pattern": "updated_", "directory": state.base_dir},
        "create_tdb_table": {"table_name": f"tdb_new_{state.suffix}", "columns": "name,status"},
        "insert_tdb_table": {"table_name": state.tdb_table, "data": [{"name": "inserted", "status": "ok"}]},
        "query_tdb": {"sql": f"SELECT * FROM {state.tdb_table} LIMIT 5"},
        "describe_tdb_table": {"table_name": state.tdb_table},
        "delete_tdb_table": {"table_name": state.tdb_delete_table},
        "export_tdb_table": {"table_name": state.tdb_export_table, "filename": state.tdb_export_file},
        "import_tdb_table": {"table_name": f"tdb_import_{state.suffix}", "filename": state.tdb_export_file},
        "add_tdb_column": {"table_name": state.tdb_alter_table, "column_name": "status_note", "column_type": "TEXT"},
        "drop_tdb_column": {"table_name": state.tdb_alter_table, "column_name": "status_note"},
        "describe_adb_table": {"table_name": state.adb_table},
        "create_adb_table": {"table_name": f"adb_new_{state.suffix}", "data": [{"name": "alice", "score": 1}]},
        "import_adb_csv": {"csv_file": state.csv_file, "table_name": state.adb_import_table},
        "export_adb_table": {"table_name": state.adb_table, "output_file": state.adb_export_file, "format": "csv"},
        "drop_adb_table": {"table_name": state.adb_import_table, "if_exists": True},
        "query_adb": {"sql": f"SELECT * FROM {state.adb_table} LIMIT 5"},
        "load_skill": {"skill_name": "material-design-3"},
        "create_user_skill": {
            "name": f"user_skill_{state.suffix}",
            "description": "tool smoke skill",
            "content": "Use concise responses for smoke tests.",
        },
        "create_vdb_collection": {"collection_name": state.vdb_collection, "content": "alpha beta gamma"},
        "search_vdb": {"query": "alpha", "collection_name": state.vdb_collection, "limit": 3},
        "describe_vdb_collection": {"collection_name": state.vdb_collection},
        "drop_vdb_collection": {"collection_name": state.vdb_collection},
        "add_vdb_documents": {"collection_name": state.vdb_collection, "content": "new doc content"},
        "update_vdb_document": {"collection_name": state.vdb_collection, "document_id": "doc-1", "content": "updated doc"},
        "delete_vdb_documents": {"collection_name": state.vdb_collection, "ids": "doc-1"},
        "add_file_to_vdb": {"collection_name": state.vdb_collection, "file_path": state.seed_file},
        "create_memory": {"content": f"memory_{state.suffix}", "memory_type": "preference", "key": f"key_{state.suffix}"},
        "update_memory": {"memory_id": state.memory_id or "missing-memory-id", "content": f"memory_updated_{state.suffix}"},
        "delete_memory": {"memory_id": state.memory_id or "missing-memory-id"},
        "forget_memory": {"memory_id": state.memory_id or "missing-memory-id"},
        "get_memory_by_key": {"key": f"key_{state.suffix}"},
        "normalize_or_create_memory": {"key": f"norm_{state.suffix}", "content": "normalized memory", "memory_type": "fact"},
        "get_memory_at_time": {"key": f"key_{state.suffix}", "time": "2026-01-01T00:00:00Z"},
        "get_memory_history": {"key": f"key_{state.suffix}"},
        "create_user_profile": {
            "name": "Smoke Tester",
            "role": "QA Engineer",
            "responsibilities": "Validate runtime tooling",
            "communication_preference": "concise",
        },
        "create_instinct": {"trigger": "when testing", "action": "respond clearly", "domain": "workflow"},
        "adjust_instinct_confidence": {"instinct_id": state.instinct_id or "missing-instinct-id", "delta": 0.05},
        "get_applicable_instincts": {"context": "testing scenario", "max_count": 3},
        "disable_instinct": {"instinct_id": state.instinct_id or "missing-instinct-id"},
        "enable_instinct": {"instinct_id": state.instinct_id or "missing-instinct-id"},
        "approve_evolved_skill": {"draft_id": state.draft_id or "missing-draft-id"},
        "import_instincts": {"json_data": "[]"},
        "apply_profile": {"profile_id": "analyst", "clear_existing": False},
        "create_custom_profile": {"name": f"custom_{state.suffix}", "description": "custom profile", "instincts_json": "[]"},
        "checkin_enable": {"every": "30m", "lookback": "24h"},
        "checkin_schedule": {"every": "1h"},
        "checkin_hours": {"start": "00:00", "end": "23:59", "days": "Mon,Tue,Wed,Thu,Fri,Sat,Sun"},
        "confirm_learning": {"verification_id": "missing-verification-id", "response": "yes"},
        "create_learning_reflection": {"task_type": "analysis", "what_went_well": "clear", "what_could_be_better": "faster"},
        "implement_improvement": {"suggestion_id": "missing-suggestion-id"},
        "learn_pattern": {"pattern_type": "workflow", "description": "prefers concise updates", "trigger": "daily standup", "confidence": 0.8},
        "get_current_time": {"timezone": "UTC"},
        "get_current_date": {"timezone": "UTC"},
        "reminder_set": {"message": f"reminder_{state.suffix}", "time": "in 20 minutes", "timezone": "UTC"},
        "reminder_cancel": {"reminder_id": state.reminder_id or "999999"},
        "reminder_edit": {"reminder_id": state.reminder_id or "999999", "message": f"edited_{state.suffix}", "time": "in 25 minutes", "timezone": "UTC"},
        "get_meta": {"format": "json", "refresh": False},
        "execute_python": {"code": "print('tool_smoke_ok')"},
        "search_web": {"query": "OpenAI", "num_results": 1, "scrape_results": False},
        "playwright_scrape": {"url": "https://example.com", "timeout_ms": 5000, "max_chars": 1000},
        "ocr_extract_text": {"image_path": state.seed_file, "output_format": "text"},
        "ocr_extract_structured": {"image_path": state.seed_file, "instruction": "extract text"},
        "extract_from_image": {"image_path": state.seed_file, "instruction": "extract text", "method": "text"},
        "confirm_request": {"action": "tool_smoke", "details": "confirming smoke execution"},
        "firecrawl_scrape": {"url": "https://example.com", "formats": "markdown"},
        "firecrawl_crawl": {"url": "https://example.com", "limit": 1, "formats": "markdown"},
        "firecrawl_check_status": {"job_id": "job-smoke-id"},
        "firecrawl_search": {"query": "OpenAI", "num_results": 1, "sources": "web", "scrape_results": False},
        "enable_mcp_tools": {"mode": "default"},
        "add_mcp_server": {"server_name": f"admin_srv_{state.suffix}", "command": "echo", "args": [], "env": {}},
        "remove_mcp_server": {"server_name": f"admin_srv_{state.suffix}"},
        "mcp_add_server": {"name": f"user_srv_{state.suffix}", "command": "echo", "arguments": "--help", "env": "{}", "cwd": ""},
        "mcp_add_remote_server": {"name": f"user_remote_{state.suffix}", "url": "http://localhost:1", "headers": "{}"},
        "mcp_remove_server": {"name": f"user_srv_{state.suffix}"},
        "mcp_show_server": {"name": f"user_srv_{state.suffix}"},
        "mcp_import_config": {"config_json": "{\"mcpServers\":{}}"},
        "mcp_reload": {"load_skills": False},
        "list_tables": {"database": "default"},
        "run_select_query": {"query": "SELECT 1"},
    }

    tool_overrides = overrides.get(name, {})
    for key, value in tool_overrides.items():
        if key in props or key in required or not props:
            args[key] = value

    # Keep arguments restricted to schema properties when available.
    if props:
        args = {k: v for k, v in args.items() if k in props}
    # Some wrapped tools expose variadic placeholders (e.g. v__args) that are not
    # accepted by the actual callable signature.
    args = {k: v for k, v in args.items() if not k.startswith("v__")}
    return args


@pytest.mark.asyncio
async def test_all_registered_tools_execute_end_to_end() -> None:
    suffix = uuid4().hex[:8]
    state = _ToolRunState(
        suffix=suffix,
        base_dir=f"tool_e2e_{suffix}",
        seed_file=f"tool_e2e_{suffix}/seed.txt",
        csv_file=f"tool_e2e_{suffix}/seed.csv",
        moved_file=f"tool_e2e_{suffix}/moved.txt",
        folder=f"tool_e2e_{suffix}/folder",
        renamed_folder=f"tool_e2e_{suffix}/folder_renamed",
        tdb_table=f"tdb_{suffix}",
        tdb_delete_table=f"tdb_delete_{suffix}",
        tdb_export_table=f"tdb_export_{suffix}",
        tdb_alter_table=f"tdb_alter_{suffix}",
        tdb_export_file=f"tool_e2e_{suffix}/tdb_export.csv",
        adb_table=f"adb_{suffix}",
        adb_import_table=f"adb_import_{suffix}",
        adb_export_file=f"tool_e2e_{suffix}/adb_export.csv",
        vdb_collection=f"vdb_{suffix}",
    )
    thread_id = f"http:tool_e2e_{suffix}"
    failures: list[str] = []

    try:
        set_thread_id(thread_id)
        clear_mcp_cache()
        tools = await get_all_tools()

        names = [_tool_name(t) for t in tools]
        # Baseline excludes optional MCP server tools when admin MCP is disabled.
        # In this environment baseline is 114; enabling MCP adds more.
        assert len(tools) >= 114, f"Expected at least 114 tools, got {len(tools)}"
        assert all(names), f"Found unnamed tools: {names}"
        assert len(names) == len(set(names)), "Duplicate tool names detected in runtime registry"

        tool_map = {_tool_name(t): t for t in tools}

        for tool in tools:
            name = _tool_name(tool)
            await _prepare_for_tool(name, tool_map, state)
            args = _build_args_for_tool(name, tool, state)
            try:
                result = await asyncio.wait_for(_invoke_tool(tool, args), timeout=45)
            except Exception as exc:
                failures.append(f"{name}: raised {type(exc).__name__}: {exc}")
                continue

            text = result if isinstance(result, str) else json.dumps(result, default=str)
            if not text or not str(text).strip():
                failures.append(f"{name}: empty response")
                continue
            if "Traceback" in text or "ExceptionGroup" in text:
                failures.append(f"{name}: unexpected traceback-like output: {text[:200]}")

            # Capture IDs for downstream tool invocations.
            if name == "create_memory":
                state.memory_id = _extract_memory_id(text) or state.memory_id
            elif name == "reminder_set":
                state.reminder_id = _extract_reminder_id(text) or state.reminder_id
            elif name == "create_instinct":
                state.instinct_id = _extract_instinct_id(text) or state.instinct_id
            elif name == "evolve_instincts":
                state.draft_id = _extract_draft_id(text) or state.draft_id

        assert not failures, "Tool invocation failures:\n" + "\n".join(failures)
    finally:
        clear_thread_id()
