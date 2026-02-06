"""Compatibility checks for Ollama Cloud tool-calling models."""

from executive_assistant.config.llm_factory import check_ollama_tool_compatibility


def test_kimi_k25_cloud_marked_compatible() -> None:
    ok, reason = check_ollama_tool_compatibility("kimi-k2.5:cloud")
    assert ok is True
    assert reason is None


def test_deepseek_v32_cloud_marked_special_format() -> None:
    ok, reason = check_ollama_tool_compatibility("deepseek-v3.2:cloud")
    assert ok is False
    assert reason is not None
    assert "XML" in reason
