#!/usr/bin/env python3
"""Test MCP client caching to verify FastMCP doesn't restart on every call."""

import asyncio
import sys
import logging

# Add src to path
sys.path.insert(0, "src")

from executive_assistant.tools.registry import (
    _load_mcp_servers,
    clear_mcp_cache,
    get_mcp_cache_info,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def test_mcp_caching():
    """Test that MCP client is cached and reused across calls."""

    print("\n" + "="*80)
    print("MCP CLIENT CACHING TEST")
    print("="*80)

    # Clear cache to start fresh
    clear_mcp_cache()
    print("\n✅ Cleared cache")

    # Sample MCP server config (using mcp-clickhouse as example)
    servers = {
        "mcp-clickhouse": {
            "command": "uv",
            "args": [
                "--directory",
                "/Users/eddy/Developer/Langgraph/ken/data/admins/skills/mcp-clickhouse",
                "run",
                "mcp-clickhouse",
            ],
            "env": {
                "CLICKHOUSE_HOST": "172.105.163.229",
                "CLICKHOUSE_PORT": "8123",
                "CLICKHOUSE_USER": "libre_chat",
                "CLICKHOUSE_PASSWORD": "${CLICKHOUSE_PASSWORD}",
                "CLICKHOUSE_DATABASE": "gong_cha_redcat_db",
            },
        }
    }

    print("\n📊 Initial cache state:")
    cache_info = get_mcp_cache_info()
    print(f"   Cache size: {cache_info['size']}")
    print(f"   Cache keys: {cache_info['keys']}")

    # First call - should create new client
    print("\n🔄 Call 1: Loading MCP tools (should create new client)...")
    tools_1 = await _load_mcp_servers(servers, "test")
    print(f"   Loaded {len(tools_1)} tools")

    print("\n📊 Cache state after call 1:")
    cache_info = get_mcp_cache_info()
    print(f"   Cache size: {cache_info['size']}")
    print(f"   Cache keys: {cache_info['keys']}")

    # Second call - should reuse cached client
    print("\n🔄 Call 2: Loading MCP tools again (should reuse cached client)...")
    tools_2 = await _load_mcp_servers(servers, "test")
    print(f"   Loaded {len(tools_2)} tools")

    print("\n📊 Cache state after call 2:")
    cache_info = get_mcp_cache_info()
    print(f"   Cache size: {cache_info['size']}")
    print(f"   Cache keys: {cache_info['keys']}")

    # Third call - should still reuse cached client
    print("\n🔄 Call 3: Loading MCP tools once more (should reuse cached client)...")
    tools_3 = await _load_mcp_servers(servers, "test")
    print(f"   Loaded {len(tools_3)} tools")

    print("\n📊 Final cache state:")
    cache_info = get_mcp_cache_info()
    print(f"   Cache size: {cache_info['size']}")
    print(f"   Cache keys: {cache_info['keys']}")

    # Verify results
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80)

    if cache_info['size'] == 1:
        print("\n✅ SUCCESS: MCP client was cached and reused!")
        print(f"   Only 1 client created for 3 calls (expected: 1)")
        print(f"   Cache hit rate: 2/3 = 66.7%")
    else:
        print(f"\n❌ FAILED: Expected 1 cached client, got {cache_info['size']}")
        print(f"   This means a new MCP client was created for each call!")
        return False

    if len(tools_1) > 0:
        print(f"\n✅ SUCCESS: Loaded {len(tools_1)} tools from MCP server")
        print(f"   Tool names: {[tool.name for tool in tools_1[:3]]}...")
    else:
        print("\n⚠️  WARNING: No tools loaded from MCP server")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80 + "\n")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_mcp_caching())
    sys.exit(0 if success else 1)
