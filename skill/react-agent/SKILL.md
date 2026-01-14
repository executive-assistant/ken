---
name: react-agent
description: Build ReAct (Reasoning plus Acting) agents from scratch using LangGraph in Python. Use this skill when creating AI agents that reason through problems and use tools iteratively, implementing custom agent workflows with LangGraph StateGraph, understanding agent architecture including nodes/edges/state/tools, building stateful agents with memory, or creating agents requiring dynamic decision-making and multi-step reasoning. This skill focuses on building agents from scratch rather than using prebuilt create_agent().
---

# ReAct Agent with LangGraph

## Quick Start

ReAct agents follow a **Reason → Act → Observe** loop:

1. **Reason**: LLM decides what action to take
2. **Act**: Execute a tool/function
3. **Observe**: Feed results back to LLM
4. Repeat until final answer

## Minimal Working Example

```python
from langgraph.graph import StateGraph, END, START
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI

# 1. Define state
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# 2. Define model
model = ChatOpenAI(model="gpt-4o-mini")

# 3. Define nodes
def call_model(state: AgentState):
    return {"messages": [model.invoke(state["messages"])]}

# 4. Build graph
graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_edge(START, "agent")
graph.add_edge("agent", END)
agent = graph.compile()

# 5. Invoke
result = agent.invoke({"messages": [("user", "Hello!")]})
```

## From Scratch: Complete ReAct Agent

### Step 1: Define State with Reducer

```python
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """State flows through all nodes in the graph."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # add_messages reducer ensures messages accumulate, not overwrite
```

### Step 2: Define Tools

```python
from langchain_core.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get weather for a location."""
    return f"Weather in {location}: Sunny, 72°F"

tools = [get_weather]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)
```

### Step 3: Define Nodes

```python
from langchain_core.messages import ToolMessage, SystemMessage
import json

def call_model(state: AgentState):
    """LLM node - generates responses and tool calls."""
    system_prompt = SystemMessage("You are a helpful assistant.")
    response = model_with_tools.invoke([system_prompt] + state["messages"])
    return {"messages": [response]}

def call_tool(state: AgentState):
    """Tool node - executes tools when LLM requests them."""
    outputs = []
    for tool_call in state["messages"][-1].tool_calls:
        tool_result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
        outputs.append(ToolMessage(
            content=json.dumps(tool_result),
            name=tool_call["name"],
            tool_call_id=tool_call["id"]
        ))
    return {"messages": outputs}
```

### Step 4: Define Routing Logic

```python
from typing import Literal

def should_continue(state: AgentState) -> Literal["tools", END]:
    """Decide whether to call tools or finish."""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END
```

### Step 5: Build and Compile

```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", call_tool)
workflow.set_entry_point("agent")

# Conditional edge: agent routes to either tools or END
workflow.add_conditional_edges("agent", should_continue, {
    "tools": "tools",
    END: END
})

# Static edge: tools always route back to agent
workflow.add_edge("tools", "agent")

agent = workflow.compile()
```

### Step 6: Use the Agent

```python
# Simple invoke
result = agent.invoke({
    "messages": [("user", "What's the weather in SF?")]
})

# Stream for visibility
for event in agent.stream({"messages": [("user", "What's the weather in SF?")}):
    print(event)
```

## Memory Management

### Short-term Memory (Session)

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
agent = workflow.compile(checkpointer=checkpointer)

# Use thread_id for conversation continuity
config = {"configurable": {"thread_id": "session_123"}}
result = agent.invoke({"messages": [("user", "Hello")]}, config)
```

### Long-term Memory (Cross-session)

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
agent = workflow.compile(store=store)

# Store and retrieve across sessions
store.put(("user_123", "preferences"), "theme", "dark")
```

### External Storage (SQLite, PostgreSQL, etc.)

```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("agent_state.db")
agent = workflow.compile(checkpointer=checkpointer)
```

## Common Patterns

### Multi-tool Agent

```python
@tool
def search(query: str) -> str:
    """Search the web."""
    return f"Results for: {query}"

@tool
def calculate(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))

tools = [search, calculate, get_weather]
```

### Custom System Prompts

```python
def call_model(state: AgentState):
    prompt = SystemMessage(
        "You are a research assistant. "
        "Always cite sources and verify information."
    )
    return {"messages": [model_with_tools.invoke([prompt] + state["messages"])]}
```

### Iteration Limits

```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    iterations: int  # Track loop count

def should_continue(state: AgentState) -> Literal["tools", END]:
    if state.get("iterations", 0) >= 5:
        return END  # Prevent infinite loops
    return "tools" if state["messages"][-1].tool_calls else END
```

## When to Use ReAct vs Simple Chain

| Use ReAct Agent | Use Simple Chain |
|-----------------|------------------|
| Path to answer is unknown | Path is predetermined |
| Multiple tool calls needed | Single operation |
| Dynamic decision required | Static workflow |
| Research/planning tasks | Simple Q&A or formatting |

## Troubleshooting

### Agent not calling tools
- Ensure tools are bound: `model.bind_tools(tools)`
- Check tool descriptions are clear
- Verify `should_continue` routing logic

### Infinite loops
- Add iteration counter to state
- Set max iterations in routing logic
- Use interrupts for human-in-the-loop

### Memory not persisting
- Verify checkpointer is configured
- Include `thread_id` in config dict
- Check state schema includes reducer

## References

For deeper dives, consult these references:

- **[react_agent_from_scratch_langgraph.md](references/react_agent_from_scratch_langgraph.md)** - Complete step-by-step guide with examples
- **[react_agents_beginner_guide.md](references/react_agents_beginner_guide.md)** - Beginner-friendly with hardcoded vs LLM-powered examples
- **[react_agents_langgraph_dylan.md](references/react_agents_langgraph_dylan.md)** - Vanilla vs LangGraph comparison
- **[langgraph_agents_tutorial.md](references/langgraph_agents_tutorial.md)** - State, nodes, edges, and memory patterns
- **[langgraph_introduction.md](references/langgraph_introduction.md)** - Core benefits and ecosystem
- **[react_agent_concepts_summary.md](references/react_agent_concepts_summary.md)** - Quick reference for patterns and best practices
