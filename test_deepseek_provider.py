#!/usr/bin/env python3
"""Manual DeepSeek provider probe script.

This file is intentionally import-safe so pytest collection does not execute it.
Run it directly:
  DEEPSEEK_API_KEY=... uv run test_deepseek_provider.py
"""

from __future__ import annotations

import os
import sys

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek


def _masked(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


def main() -> int:
    api_key = os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OLLAMA_CLOUD_API_KEY", ""))
    api_base = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    if not api_key:
        print("DEEPSEEK_API_KEY is not set.")
        print("Usage:")
        print("  DEEPSEEK_API_KEY=your_key uv run test_deepseek_provider.py")
        print("  DEEPSEEK_API_KEY=your_ollama_key DEEPSEEK_API_BASE=https://ollama.com uv run test_deepseek_provider.py")
        return 1

    print("=" * 60)
    print("DeepSeek Native Provider Test")
    print("=" * 60)
    print(f"API Base: {api_base}")
    print(f"Model: {model}")
    print(f"API Key: {_masked(api_key)}")
    print()

    print("Test 1: Simple chat completion")
    print("-" * 60)
    try:
        chat = ChatDeepSeek(
            model=model,
            api_key=api_key,
            base_url=api_base,
        )

        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="Say 'Hello, DeepSeek!' in a single sentence."),
        ]
        response = chat.invoke(messages)
        print(f"Response: {response.content}")
    except Exception as exc:
        print(f"Error: {exc}")
        return 1

    print()
    print("Test 2: Tool calling")
    print("-" * 60)
    if api_base == "https://api.deepseek.com":
        try:
            from langchain_core.tools import tool

            @tool
            def get_weather(location: str) -> str:
                """Get the current weather in a given location."""
                return f"The weather in {location} is sunny and 75F."

            chat_with_tools = chat.bind_tools([get_weather])
            messages = [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content="What's the weather like in San Francisco?"),
            ]
            response = chat_with_tools.invoke(messages)
            print(f"Tool calls: {response.tool_calls}")
            print(f"Response content: {response.content}")
        except Exception as exc:
            print(f"Tool calling error: {exc}")
            return 1
    else:
        print("Skipped for non-official DeepSeek API base.")

    print()
    print("=" * 60)
    print("All tests completed")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
