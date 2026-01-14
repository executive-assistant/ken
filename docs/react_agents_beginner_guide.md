# Building ReAct Agents with LangGraph: A Beginner's Guide

Source: https://machinelearningmastery.com/building-react-agents-with-langgraph-a-beginners-guide/

## What is the ReAct Pattern?

ReAct (Reasoning + Acting) is a common pattern for building AI agents that think through problems and take actions to solve them. The pattern follows a simple cycle:

1. **Reasoning**: The agent thinks about what it needs to do next.
2. **Acting**: The agent takes an action (like searching for information).
3. **Observing**: The agent examines the results of its action.

This cycle repeats until the agent has gathered enough information to answer the user's question.

## Why LangGraph?

LangGraph is a framework built on top of LangChain that lets you define agent workflows as graphs. A graph consists of:
- **Nodes**: Steps in your process
- **Edges**: The paths between steps

This structure allows for complex flows like loops and conditional branching.

## Part 1: Understanding ReAct with a Simple Example

### Setting Up the State

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

# Define the state that flows through our graph
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    next_action: str
    iterations: int
```

**Key Components:**
- `StateGraph`: The main class from LangGraph that defines our agent's workflow
- `AgentState`: A TypedDict that defines what information our agent tracks
- `messages`: Uses `operator.add` to accumulate all thoughts, actions, and observations
- `next_action`: Tells the graph which node to execute next
- `iterations`: Counts how many reasoning cycles we've completed

### Creating a Mock Tool

```python
# Simple mock search tool
def search_tool(query: str) -> str:
    # Simulate a search - in real usage, this would call an API
    responses = {
        "weather tokyo": "Tokyo weather: 18°C, partly cloudy",
        "population japan": "Japan population: approximately 125 million",
    }
    return responses.get(query.lower(), f"No results found for: {query}")
```

### The Reasoning Node

```python
# Reasoning node - decides what to do
def reasoning_node(state: AgentState):
    messages = state["messages"]
    iterations = state.get("iterations", 0)

    # Simple logic: first search weather, then population, then finish
    if iterations == 0:
        return {"messages": ["Thought: I need to check Tokyo weather"],
                "next_action": "action", "iterations": iterations + 1}
    elif iterations == 1:
        return {"messages": ["Thought: Now I need Japan's population"],
                "next_action": "action", "iterations": iterations + 1}
    else:
        return {"messages": ["Thought: I have enough info to answer"],
                "next_action": "end", "iterations": iterations + 1}
```

### The Action Node

```python
# Action node - executes the tool
def action_node(state: AgentState):
    iterations = state["iterations"]
    # Choose query based on iteration
    query = "weather tokyo" if iterations == 1 else "population japan"
    result = search_tool(query)
    return {"messages": [f"Action: Searched for '{query}'",
                       f"Observation: {result}"],
            "next_action": "reasoning"}

# Router - decides next step
def route(state: AgentState):
    return state["next_action"]
```

### Building and Executing the Graph

```python
# Build the graph
workflow = StateGraph(AgentState)
workflow.add_node("reasoning", reasoning_node)
workflow.add_node("action", action_node)

# Define edges
workflow.set_entry_point("reasoning")
workflow.add_conditional_edges("reasoning", route, {
    "action": "action",
    "end": END
})
workflow.add_edge("action", "reasoning")

# Compile and run
app = workflow.compile()

# Execute
result = app.invoke({
    "messages": ["User: Tell me about Tokyo and Japan"],
    "iterations": 0,
    "next_action": ""
})
```

## Part 2: LLM-Powered ReAct Agent

### Why Use an LLM?

The hardcoded version works, but it's inflexible. An LLM-powered agent can:
- Understand different types of questions
- Decide dynamically what information to gather
- Adapt its reasoning based on what it learns

### Setting Up the LLM Environment

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

class AgentStateLLM(TypedDict):
    messages: Annotated[list, operator.add]
    next_action: str
    iteration_count: int
```

### The LLM Tool

```python
def llm_tool(query: str) -> str:
    """Let the LLM answer the query directly using its knowledge"""
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=150,
        messages=[{"role": "user", "content": f"Answer this query briefly: {query}"}]
    )
    return response.choices[0].message.content.strip()
```

### LLM-Powered Reasoning

```python
def reasoning_node_llm(state: AgentStateLLM):
    iteration_count = state.get("iteration_count", 0)

    if iteration_count >= 3:
        return {"messages": ["Thought: I have gathered enough information"],
                "next_action": "end", "iteration_count": iteration_count}

    history = "\n".join(state["messages"])
    prompt = f"""You are an AI agent answering: "Tell me about Tokyo and Japan"
Conversation so far: {history}
Queries completed: {iteration_count}/3
You MUST make exactly 3 queries to gather information.
Respond ONLY with: QUERY: <your specific question>
Do NOT be conversational. Do NOT thank the user. ONLY output: QUERY: <question>"""

    decision = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    ).choices[0].message.content.strip()

    if decision.startswith("QUERY:"):
        return {"messages": [f"Thought: {decision}"],
                "next_action": "action", "iteration_count": iteration_count}
    return {"messages": [f"Thought: {decision}"],
            "next_action": "end", "iteration_count": iteration_count}
```

### Executing the Action

```python
def action_node_llm(state: AgentStateLLM):
    last_thought = state["messages"][-1]
    query = last_thought.replace("Thought: QUERY:", "").strip()
    result = llm_tool(query)
    return {"messages": [f"Action: query('{query}')",
                       f"Observation: {result}"],
            "next_action": "reasoning",
            "iteration_count": state.get("iteration_count", 0) + 1}
```

### Building the LLM-Powered Graph

```python
workflow_llm = StateGraph(AgentStateLLM)
workflow_llm.add_node("reasoning", reasoning_node_llm)
workflow_llm.add_node("action", action_node_llm)
workflow_llm.set_entry_point("reasoning")
workflow_llm.add_conditional_edges("reasoning", lambda s: s["next_action"],
                                  {"action": "action", "end": END})
workflow_llm.add_edge("action", "reasoning")

app_llm = workflow_llm.compile()

result_llm = app_llm.invoke({
    "messages": ["User: Tell me about Tokyo and Japan"],
    "next_action": "",
    "iteration_count": 0
})
```

## Key Insight

LangGraph lets you separate your workflow structure from the intelligence that drives it. The graph topology stayed the same between Part 1 and Part 2, but swapping hardcoded logic for LLM reasoning transformed a rigid script into an adaptive agent.
