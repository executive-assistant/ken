# Step-by-Step Guide: Implementing a ReAct Agent with Tools

This guide explains how to implement a ReAct (Reasoning + Acting) agent using LangChain 1.x with file operations and custom tools.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Project Structure](#project-structure)
4. [Step 1: Environment Setup](#step-1-environment-setup)
5. [Step 2: Create Custom Tools](#step-2-create-custom-tools)
6. [Step 3: Create File Backend](#step-3-create-file-backend)
7. [Step 4: Create the Agent](#step-4-create-the-agent)
8. [Step 5: Register with LangGraph](#step-5-register-with-langgraph)
9. [Full Example](#full-example)

---

## Overview

A **ReAct Agent** combines:
- **Reasoning**: The model thinks about what action to take
- **Acting**: The model executes tools and observes results

**Key Components:**

| Component | Purpose |
|-----------|---------|
| `create_agent()` | LangChain 1.x function to create ReAct agents |
| `@tool` decorator | Converts Python functions to agent tools |
| `MemorySaver` | Checkpointer for conversation persistence |
| `ToolRuntime` | Provides context (thread_id, config) to tools |

---

## Prerequisites

### Required Packages

```bash
# Core LangChain packages
pip install langchain>=0.3.0 langchain-core>=0.3.0 langchain-anthropic langchain-openai

# LangGraph for agent orchestration
pip install langgraph>=0.2.0

# Optional: For file operations
pip install python-dotenv httpx
```

### Environment Variables

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-xxx  # For Claude
OPENAI_API_KEY=sk-xxx          # For GPT-4
# Or other provider keys
```

---

## Project Structure

```
my-agent/
├── .env                        # Environment variables
├── langgraph.json              # LangGraph configuration
├── agent/
│   ├── __init__.py
│   ├── graph.py                # Main agent definition
│   ├── backends.py             # File system backend (optional)
│   └── tools/
│       ├── __init__.py
│       ├── config.py           # Shared config
│       ├── file_tools.py       # File operations
│       └── custom_tool.py      # Your custom tools
└── workspace/                  # Created at runtime
    └── {thread_id}/            # Thread-specific files
```

---

## Step 1: Environment Setup

### Create `.env` file

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-xxx
```

### Create config helper (`agent/tools/config.py`)

```python
"""Shared configuration with lazy .env loading."""
import os
from dotenv import load_dotenv

def get_config():
    """Load config with lazy .env loading."""
    load_dotenv()
    return {
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
    }
```

---

## Step 2: Create Custom Tools

### Basic Tool Pattern

Every tool follows this pattern:

```python
from langchain_core.tools import tool

@tool
def my_tool(param: str) -> str:
    """Tool description that the AI sees.

    Args:
        param: Description of parameter

    Returns:
        Result that the AI will see
    """
    # Your logic here
    return "result"
```

### Example: File Read Tool

```python
from langchain_core.tools import tool
from pathlib import Path

@tool
def read_file(file_path: str) -> str:
    """Read the contents of a file.

    Args:
        file_path: Path to the file to read (relative to workspace)

    Returns:
        The file contents as a string
    """
    full_path = Path("./workspace") / file_path
    try:
        return full_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Error: File '{file_path}' not found"
```

### Example: File Write Tool

```python
from langchain_core.tools import tool
from pathlib import Path

@tool
def write_file(file_path: str, content: str) -> str:
    """Write content to a new file.

    Args:
        file_path: Path for the new file
        content: Content to write

    Returns:
        Confirmation message
    """
    full_path = Path("./workspace") / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return f"Successfully wrote {len(content)} characters to '{file_path}'"
```

### Example: API Tool with Runtime Context

```python
from langchain_core.tools import tool
from langchain.tools import ToolRuntime
import httpx

@tool
def fetch_website(url: str, runtime: ToolRuntime) -> str:
    """Fetch content from a website.

    Args:
        url: The URL to fetch
        runtime: Tool context (injected automatically)

    Returns:
        The website content
    """
    try:
        response = httpx.get(url, timeout=30)
        return response.text[:5000]  # Truncate for safety
    except Exception as e:
        return f"Error fetching {url}: {e}"
```

### Export Tools (`agent/tools/__init__.py`)

```python
from .file_tools import read_file, write_file
from .custom_tool import my_tool

# All tools for the agent
ALL_TOOLS = [
    read_file,
    write_file,
    my_tool,
]
```

---

## Step 3: Create File Backend (Optional)

For thread-aware file operations:

```python
# agent/backends.py
from pathlib import Path
from typing import Any
from langchain.tools import ToolRuntime

class ThreadAwareBackend:
    """Backend that isolates files by thread_id."""

    def __init__(self, base_root_dir: str = "./workspace"):
        self.base_root_dir = Path(base_root_dir)

    def get_workspace_dir(self, runtime: ToolRuntime) -> Path:
        """Get thread-specific workspace directory."""
        thread_id = "default"

        # Extract thread_id from runtime config
        if hasattr(runtime, "config") and runtime.config:
            configurable = runtime.config.get("configurable", {})
            thread_id = configurable.get("thread_id", "default")

        workspace = self.base_root_dir / thread_id
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace
```

---

## Step 4: Create the Agent

### Basic Agent (`agent/graph.py`)

```python
"""ReAct Agent implementation."""
import os
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

# Import your tools
from agent.tools import ALL_TOOLS


def get_model_id() -> str:
    """Get model ID string for create_agent()."""
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic:claude-sonnet-4-5-20250929"
    if os.getenv("OPENAI_API_KEY"):
        return "openai:gpt-4o"
    return "anthropic:claude-sonnet-4-5-20250929"


def create_react_agent():
    """Create a ReAct agent with tools."""
    system_prompt = """You are a helpful AI assistant with access to various tools.

## Tools Available:
- **read_file**: Read file contents from the workspace
- **write_file**: Create new files in the workspace
- **my_tool**: [Your tool description]

## Instructions:
1. Think before acting - analyze what the user needs
2. Choose the appropriate tool
3. Execute and observe the result
4. If needed, try another approach
"""

    # Checkpointer for conversation persistence
    checkpointer = MemorySaver()

    # Create the agent
    agent = create_agent(
        model=get_model_id(),      # Model ID string
        tools=ALL_TOOLS,            # Your tools list
        system_prompt=system_prompt,
        checkpointer=checkpointer,
    )

    return agent


# LangGraph factory function
def agent(config: RunnableConfig):
    """Factory function called by LangGraph dev server."""
    return create_react_agent()


__all__ = ["agent", "create_react_agent"]
```

### Key Points:

1. **`create_agent()`** from `langchain.agents` automatically:
   - Binds tools to the model
   - Sets up ReAct loop (Thought → Action → Observation)
   - Handles tool execution and result parsing

2. **Model ID format**: `"provider:model-name"`
   - `"anthropic:claude-sonnet-4-5-20250929"`
   - `"openai:gpt-4o"`

3. **System prompt** defines tool usage patterns

---

## Step 5: Register with LangGraph

### Create `langgraph.json`

```json
{
  "graphs": {
    "my-agent": "./agent/graph.py:agent"
  },
  "dependencies": ["."],
  "env": ".env"
}
```

### Run the Agent

```bash
# Start LangGraph dev server
langgraph dev --port 2024

# The agent will be available at:
# - API: http://127.0.0.1:2024
# - Studio: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

---

## Full Example

### Complete `agent/graph.py`

```python
"""Complete ReAct Agent example."""
import os
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pathlib import Path
import httpx


# ===== Tools =====

@tool
def read_file(file_path: str) -> str:
    """Read the contents of a file from the workspace.

    Args:
        file_path: Path to the file (relative to workspace root)

    Returns:
        File contents or error message
    """
    full_path = Path("./workspace") / file_path
    try:
        return full_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Error: File '{file_path}' not found"
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def write_file(file_path: str, content: str) -> str:
    """Write content to a new file in the workspace.

    Args:
        file_path: Path for the new file
        content: Content to write

    Returns:
        Confirmation message with file info
    """
    full_path = Path("./workspace") / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    full_path.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to '{file_path}'"


@tool
def list_files(directory: str = ".") -> str:
    """List files in a workspace directory.

    Args:
        directory: Directory path (relative to workspace, default is root)

    Returns:
        List of files and directories
    """
    full_path = Path("./workspace") / directory
    if not full_path.exists():
        return f"Directory '{directory}' does not exist"

    items = []
    for item in full_path.iterdir():
        kind = "DIR " if item.is_dir() else "FILE"
        items.append(f"  {kind} {item.name}")

    return "\n".join(sorted(items)) if items else "Empty directory"


@tool
def fetch_url(url: str) -> str:
    """Fetch content from a URL.

    Args:
        url: The URL to fetch

    Returns:
        URL content (truncated to 5000 chars)
    """
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        response = httpx.get(url, timeout=30, follow_redirects=True)
        response.raise_for_status()
        return response.text[:5000]
    except Exception as e:
        return f"Error fetching URL: {e}"


# All tools for the agent
TOOLS = [read_file, write_file, list_files, fetch_url]


# ===== Agent Creation =====

def get_model_id() -> str:
    """Get model ID based on available API keys."""
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic:claude-sonnet-4-5-20250929"
    if os.getenv("OPENAI_API_KEY"):
        return "openai:gpt-4o"
    return "anthropic:claude-sonnet-4-5-20250929"


def create_react_agent():
    """Create a ReAct agent with file and web tools."""
    system_prompt = """You are a helpful AI assistant with file management and web fetching capabilities.

## Tools Available:

1. **read_file** - Read file contents
   - Use when you need to see what's in a file
   - Example: "Read the config file"

2. **write_file** - Create new files
   - Use to save content, notes, or results
   - Example: "Save this summary to a file"

3. **list_files** - List workspace contents
   - Use to see what files exist
   - Example: "Show me all files"

4. **fetch_url** - Fetch web content
   - Use to get content from a specific URL
   - Example: "Fetch the content from https://example.com"

## Workflow:
1. Understand what the user wants
2. Choose the appropriate tool(s)
3. Execute and observe results
4. Provide a helpful summary
"""

    checkpointer = MemorySaver()

    agent = create_agent(
        model=get_model_id(),
        tools=TOOLS,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
    )

    return agent


def agent(config: RunnableConfig):
    """LangGraph factory function."""
    return create_react_agent()


__all__ = ["agent", "create_react_agent"]
```

---

## Testing Your Agent

### Via Python

```python
from agent.graph import create_react_agent

# Create agent
agent = create_react_agent()

# Invoke with a message
config = {"configurable": {"thread_id": "test-thread"}}
result = agent.invoke(
    {"messages": [("user", "Create a file named hello.txt with content 'Hello World'")]},
    config=config
)

print(result["messages"][-1].content)
```

### Via LangGraph API

```bash
# Start server
langgraph dev --port 2024

# In another terminal, create a thread
curl -X POST http://127.0.0.1:2024/threads \
  -H "Content-Type: application/json"

# Run the agent
curl -X POST http://127.0.0.1:2024/threads/{thread_id}/runs \
  -H "Content-Type: application/json" \
  -d '{"assistant_id": "my-agent", "input": {"messages": [{"role": "user", "content": "Create a file"}]}}'
```

---

## Common Patterns

### Tool with Runtime Context (Thread ID)

```python
from langchain.tools import ToolRuntime

@tool
def thread_aware_tool(param: str, runtime: ToolRuntime) -> str:
    """Tool that can access thread_id from runtime."""
    thread_id = "default"

    if hasattr(runtime, "config") and runtime.config:
        configurable = runtime.config.get("configurable", {})
        thread_id = configurable.get("thread_id", "default")

    return f"Running in thread: {thread_id}"
```

### Tool That Updates State

```python
from langgraph.types import Command
from langchain_core.messages import ToolMessage

@tool
def state_updating_tool(param: str, runtime: ToolRuntime) -> Command:
    """Tool that updates agent state."""
    return Command(
        update={
            "my_state_key": param,
            "messages": [
                ToolMessage(
                    content=f"Updated state with: {param}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
        }
    )
```

### Async Tool

```python
@tool
async def async_tool(url: str) -> str:
    """Async tool for network operations."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Ensure package is in `langgraph.json` dependencies |
| Tool not found | Add tool to `tools` list in `create_agent()` |
| Model error | Check `get_model_id()` returns correct format |
| `.env` not loading | Use lazy loading in tool/config function |

---

## Key Takeaways

1. **`create_agent()`** is the simplest way to build ReAct agents in LangChain 1.x
2. **`@tool` decorator** converts functions to agent tools automatically
3. **Model ID format** must be `"provider:model-name"`
4. **`MemorySaver`** enables conversation persistence
5. **`ToolRuntime`** provides thread context when injected as a parameter
