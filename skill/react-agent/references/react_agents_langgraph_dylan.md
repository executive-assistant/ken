# Building ReAct Agents with (and Without) LangGraph

Source: https://dylancastillo.co/posts/react-agent-langgraph.html

## What is an Agent?

Agents are systems that can independently make decisions, use tools, take actions, and pursue a goal without direct human guidance. The most well-known agent implementation are **ReAct Agents**.

## What's a ReAct Agent?

ReAct (Reasoning and Acting) Agents are AI systems that merge the reasoning of Large Language Models (LLMs) with the ability to perform actions. They follow an iterative "think, act, observe" cycle to solve problems:

1. Take a user query
2. Think about the query and decide on an action
3. Execute the action using available tools (environment)
4. Analyze the result of that action (environment)
5. Continue the "Reason, Act, Observe" loop until final answer

The first generation of ReAct agents used a prompt technique of "Thought, Action, Observation". Current agents rely on **function-calling** to implement the "think, act, observe" loop.

## What is LangGraph?

LangGraph is a graph-based framework for building complex LLM applications, designed for stateful workflows. Graphs are composed of:
- **Nodes**: The units of work (functions, tools)
- **Edges**: Define the paths between nodes
- **State**: Persistent data passed between nodes
- **Reducers**: Functions that define how the state is updated

## Prerequisites

```bash
python -m venv venv
source venv/bin/activate
pip install langchain langchain-openai langchain-community langgraph jupyter
```

## Vanilla ReAct Agent

### Define the Tool

```python
from langchain_core.tools import tool

@tool
def run_python_code(code: str) -> str:
    """Run arbitrary Python code including imports, assignments, and statements.
    Do not use any external libraries. Save your results as a variable.

    Args:
        code: Python code to run
    """
    import sys
    from io import StringIO

    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    namespace = {}

    try:
        exec(code, namespace)

        output = captured_output.getvalue()

        if not output.strip():
            user_vars = {
                k: v
                for k, v in namespace.items()
                if not k.startswith("__") and k not in ["StringIO", "sys"]
            }
            if len(user_vars) == 1:
                output = str(list(user_vars.values())[0])
            else:
                output = str(user_vars)

        return output.strip() if output.strip() else "Code executed successfully"

    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        sys.stdout = old_stdout


tools = [run_python_code]
tools_mapping = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)
```

### The Agent Function

```python
def run_agent(question: str):
    messages = [
        SystemMessage(
            "You're a helpful assistant. Use the tools provided when relevant."
        ),
        HumanMessage(question),
    ]
    ai_message = model_with_tools.invoke(messages)
    messages.append(ai_message)

    while ai_message.tool_calls:
        for tool_call in ai_message.tool_calls:
            selected_tool = tools_mapping[tool_call["name"]]
            tool_msg = selected_tool.invoke(tool_call)
            messages.append(tool_msg)
        ai_message = model_with_tools.invoke(messages)
        messages.append(ai_message)

    return messages
```

## LangGraph ReAct Agent

### Define the Nodes

```python
def call_llm(state: MessagesState):
    messages = [
        SystemMessage(content="You are a helpful assistant that can run python code."),
    ] + state["messages"]
    return {"messages": [model_with_tools.invoke(messages)]}


def call_tool(state: MessagesState):
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}


def should_continue(state: MessagesState) -> Literal["environment", END]:
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "Action"
    return END
```

### Build the Graph

```python
agent_builder = StateGraph(MessagesState)

agent_builder.add_node("llm", call_llm)
agent_builder.add_node("environment", call_tool)

agent_builder.add_edge(START, "llm")
agent_builder.add_conditional_edges(
    "llm",
    should_continue,
    {
        "Action": "environment",
        END: END,
    },
)
agent_builder.add_edge("environment", "llm")

agent = agent_builder.compile()
```

### Visualize and Run

```python
from IPython.display import Image, display
display(Image(agent.get_graph(xray=True).draw_mermaid_png()))

messages = [
    SystemMessage(content="You are a helpful assistant that can run python code."),
    HumanMessage(content="Generate 10 random numbers between 1 and 100"),
]

messages = agent.invoke({"messages": messages})
```

## Key Differences: Vanilla vs LangGraph

| Vanilla | LangGraph |
|---------|-----------|
| Manual loop management | Declarative graph structure |
| Harder to visualize | Built-in visualization |
| Manual state management | Automatic state handling |
| Less extensible | Easy to add nodes/edges |

## When to Use Agents vs Agentic Workflows

- **Agents**: Tasks without a predefined path, where the order of steps is not known beforehand
- **Agentic Workflows**: Tasks where both the path and order of steps are known

Agents are great for open-ended tasks like coding assistants and support agents.
