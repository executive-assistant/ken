# LangGraph Introduction

Source: https://langchain-ai.github.io/langgraph/tutorials/introduction/

## Overview

LangGraph is a low-level orchestration framework and runtime for building, managing, and deploying long-running, stateful agents. It is very low-level, and focused entirely on agent **orchestration**.

Before using LangGraph, familiarize yourself with some of the components used to build agents, starting with **models** and **tools**.

## Installation

```bash
pip install -U langgraph
```

### Hello World Example

```python
from langgraph.graph import StateGraph, MessagesState, START, END

def mock_llm(state: MessagesState):
    return {"messages": [{"role": "ai", "content": "hello world"}]}

graph = StateGraph(MessagesState)
graph.add_node(mock_llm)
graph.add_edge(START, "mock_llm")
graph.add_edge("mock_llm", END)
graph = graph.compile()

graph.invoke({"messages": [{"role": "user", "content": "hi!"}]})
```

## Core Benefits

LangGraph provides low-level supporting infrastructure for any long-running, stateful workflow or agent:

### Durable Execution
Build agents that persist through failures and can run for extended periods, resuming from where they left off.

### Human-in-the-Loop
Incorporate human oversight by inspecting and modifying agent state at any point.

### Comprehensive Memory
Create stateful agents with both short-term working memory for ongoing reasoning and long-term memory across sessions.

### Debugging with LangSmith
Gain deep visibility into complex agent behavior with visualization tools that trace execution paths, capture state transitions, and provide detailed runtime metrics.

### Production-Ready Deployment
Deploy sophisticated agent systems confidently with scalable infrastructure designed to handle the unique challenges of stateful, long-running workflows.

## LangGraph Ecosystem

While LangGraph can be used standalone, it also integrates seamlessly with any LangChain product:

### LangSmith
Trace requests, evaluate outputs, and monitor deployments in one place. Prototype locally with LangGraph, then move to production with integrated observability and evaluation.

### LangSmith Agent Server
Deploy and scale agents effortlessly with a purpose-built deployment platform for long running, stateful workflows. Discover, reuse, configure, and share agents across teams.

### LangChain
Provides integrations and composable components to streamline LLM application development. Contains agent abstractions built on top of LangGraph.

## Inspirations

LangGraph is inspired by:
- **Pregel**: Google's graph processing framework
- **Apache Beam**: Stream and batch processing
- **NetworkX**: Graph manipulation and analysis

The public interface draws inspiration from NetworkX. LangGraph is built by LangChain Inc, but can be used without LangChain.
