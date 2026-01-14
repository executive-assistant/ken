"""Tool registry for aggregating all available tools."""

from langchain_core.tools import BaseTool

from cassey.storage.file_sandbox import list_files, read_file, write_file


async def get_file_tools() -> list[BaseTool]:
    """Get file operation tools."""
    return [read_file, write_file, list_files]


async def get_duckdb_tools() -> list[BaseTool]:
    """Get DuckDB tabular data tools."""
    from cassey.storage.duckdb_tools import (
        create_table,
        insert_table,
        query_table,
        list_tables,
        describe_table,
        drop_table,
        export_table,
        import_table,
    )
    return [
        create_table,
        insert_table,
        query_table,
        list_tables,
        describe_table,
        drop_table,
        export_table,
        import_table,
    ]


async def get_mcp_tools() -> list[BaseTool]:
    """
    Get tools from MCP servers configured in .mcp.json.

    This connects to the configured MCP servers (Firecrawl, Chrome DevTools,
    Meilisearch) and converts their tools to LangChain-compatible format.

    Returns:
        List of LangChain tools from MCP servers.
    """
    tools = []

    try:
        from langchain_mcp_adapters import MCPClient
        from pathlib import Path
        import json

        mcp_config_path = Path(".mcp.json")
        if not mcp_config_path.exists():
            return tools

        with open(mcp_config_path) as f:
            mcp_config = json.load(f)

        # Connect to each MCP server and get tools
        for server_name, server_config in mcp_config.get("mcpServers", {}).items():
            try:
                client = MCPClient(server_config)
                server_tools = await client.get_tools()
                tools.extend(server_tools)
            except Exception as e:
                print(f"Warning: Failed to connect to MCP server '{server_name}': {e}")

    except ImportError:
        print("Warning: langchain-mcp-adapters not installed. MCP tools unavailable.")
    except Exception as e:
        print(f"Warning: Error loading MCP tools: {e}")

    return tools


def get_standard_tools() -> list[BaseTool]:
    """Get standard LangChain tools."""
    tools = []

    # Add Tavily search if API key is available
    try:
        from langchain_community.tools import TavilySearchResults
        import os

        if os.getenv("TAVILY_API_KEY"):
            tools.append(TavilySearchResults(max_results=5))
    except ImportError:
        pass
    except Exception:
        pass

    # Add calculator tool
    from langchain_core.tools import tool

    @tool
    def calculator(expression: str) -> str:
        """
        Evaluate a mathematical expression.

        Args:
            expression: Mathematical expression to evaluate.

        Returns:
            Result of the calculation.

        Examples:
            >>> calculator("2 + 2")
            "4"
            >>> calculator("10 * 5")
            "50"
        """
        try:
            # Safe evaluation of math expressions
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"Error: {e}"

    tools.append(calculator)

    return tools


async def get_all_tools() -> list[BaseTool]:
    """
    Get all available tools for the agent.

    Aggregates tools from:
    - File operations (read, write, list)
    - DuckDB operations (create_table, query_table, etc.)
    - MCP servers (Firecrawl, Chrome DevTools, Meilisearch)
    - Standard tools (calculator, search)

    Returns:
        List of all available LangChain tools.
    """
    all_tools = []

    # Add file tools
    all_tools.extend(await get_file_tools())

    # Add DuckDB tools
    all_tools.extend(await get_duckdb_tools())

    # Add MCP tools
    all_tools.extend(await get_mcp_tools())

    # Add standard tools
    all_tools.extend(get_standard_tools())

    return all_tools
