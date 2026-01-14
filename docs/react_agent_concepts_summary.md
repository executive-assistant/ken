# React Agent Concepts Summary

Compiled from multiple sources for creating a Claude skill.

## What is a ReAct Agent?

ReAct (Reasoning + Acting) is a pattern for building AI agents that:
1. **Reason** about what they need to do next
2. **Act** by calling tools or functions
3. **Observe** the results of their actions
4. Repeat until they can deliver a final answer

## Core Components

### State
Shared memory that flows through the graph containing:
- Messages (conversation history)
- Next action indicator
- Iteration count
- Custom fields for your use case

### Nodes
Functional units that perform actions:
- **Model node**: Calls the LLM
- **Tool node**: Executes tools
- **Custom nodes**: Any function you define

### Edges
Connections between nodes:
- **Static edges**: Always go from A to B
- **Conditional edges**: Route based on state conditions

## Implementation Patterns

### Using create_react_agent (Simplest)

```python
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(
    model=llm,
    tools=tools,
    state_modifier="You are a helpful assistant"
)
```

### From Scratch (Most Control)

1. Define state with TypedDict
2. Define model and tools
3. Define nodes (call_model, tool_node)
4. Define routing logic (should_continue)
5. Build graph with StateGraph
6. Compile and invoke

### With LangChain JavaScript

```javascript
import { createAgent } from "langchain";

const agent = createAgent({
  model: "gpt-4o",
  tools: [search, getWeather],
  systemPrompt: "You are a helpful assistant"
});
```

## Tools

### Defining Tools (Python)

```python
from langchain_core.tools import tool

@tool
def my_tool(param: str) -> str:
    """Tool description for the LLM."""
    return "result"
```

### Defining Tools (JavaScript)

```javascript
import { tool } from "langchain";
import * as z from "zod";

const myTool = tool(
  ({ param }) => `result`,
  {
    name: "my_tool",
    description: "Tool description",
    schema: z.object({
      param: z.string()
    })
  }
);
```

## Memory Management

### Short-term (Session)

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

### Long-term (Cross-session)

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
agent = builder.compile(store=store)
```

### External Storage

- SQLite
- PostgreSQL
- Amazon S3
- Azure Blob Storage
- Google Cloud Storage

## Best Practices

1. **Start with prebuilt**: Use `create_react_agent` first
2. **Add reducer functions**: Use `operator.add` for message accumulation
3. **Handle errors gracefully**: Use middleware for tool error handling
4. **Limit iterations**: Set max iterations to prevent infinite loops
5. **Use system prompts**: Guide agent behavior with clear instructions
6. **Stream responses**: Use streaming for better UX
7. **Debug with LangSmith**: Trace execution paths and state transitions

## Common Patterns

### Multi-step Reasoning

Agent performs multiple tool calls before answering:
1. Search for information
2. Retrieve additional details
3. Synthesize and respond

### Dynamic Tool Selection

Agent chooses which tools to use based on:
- User query content
- Previous tool results
- Current conversation context

### Human-in-the-Loop

Pause execution for human input:
```python
graph = workflow.compile(interrupt_before=["critical_action"])
```

## When to Use ReAct Agents

✅ Good for:
- Open-ended questions without predefined paths
- Tasks requiring dynamic tool selection
- Multi-step reasoning problems
- Research and information gathering

❌ Not ideal for:
- Simple, single-step queries (use a chain instead)
- Tasks with known execution paths (use workflows)
- Low-latency requirements (agents require multiple LLM calls)
