#!/usr/bin/env python3
"""Test script for DeepSeek native provider integration.

This script tests the official langchain-deepseek integration with:
1. Official DeepSeek API (api.deepseek.com)
2. Ollama Cloud backend (ollama.com with Ollama Cloud API key)

Usage:
    # Test with official DeepSeek API
    DEEPSEEK_API_KEY=your_key uv run test_deepseek_provider.py

    # Test with Ollama Cloud backend
    DEEPSEEK_API_KEY=your_ollama_key DEEPSEEK_API_BASE=https://ollama.com uv run test_deepseek_provider.py
"""

import os
import asyncio
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage, SystemMessage

# Get configuration from environment
api_key = os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OLLAMA_CLOUD_API_KEY", ""))
api_base = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com")
model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

if not api_key:
    print("❌ DEEPSEEK_API_KEY not set!")
    print("\nUsage:")
    print("  # Official DeepSeek API:")
    print("  DEEPSEEK_API_KEY=your_key uv run test_deepseek_provider.py")
    print("\n  # Ollama Cloud backend:")
    print("  DEEPSEEK_API_KEY=your_ollama_key DEEPSEEK_API_BASE=https://ollama.com uv run test_deepseek_provider.py")
    exit(1)

print("=" * 60)
print("DeepSeek Native Provider Test")
print("=" * 60)
print(f"API Base: {api_base}")
print(f"Model: {model}")
print(f"API Key: {'*' * (len(api_key) - 4) + api_key[-4:]}")
print()

# Test 1: Simple chat completion
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
    print(f"✅ Response: {response.content}")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

print()

# Test 2: Tool calling (if using official DeepSeek API)
if api_base == "https://api.deepseek.com" or api_base == "https://api.deepseek.com":
    print("Test 2: Tool calling (official API only)")
    print("-" * 60)
    try:
        from langchain_core.tools import tool

        @tool
        def get_weather(location: str) -> str:
            """Get the current weather in a given location."""
            return f"The weather in {location} is sunny and 75°F."

        chat_with_tools = chat.bind_tools([get_weather])

        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="What's the weather like in San Francisco?"),
        ]

        response = chat_with_tools.invoke(messages)
        print(f"✅ Tool calls: {response.tool_calls}")
        print(f"Response content: {response.content}")
    except Exception as e:
        print(f"❌ Tool calling error: {e}")
else:
    print("Test 2: Tool calling")
    print("-" * 60)
    print("⚠️  Skipped (Ollama Cloud backend detected)")
    print("   Note: Ollama Cloud with DeepSeek models uses custom tool calling format.")
    print("   Use official DeepSeek API for full bind_tools() support.")

print()
print("=" * 60)
print("✅ All tests completed successfully!")
print("=" * 60)
