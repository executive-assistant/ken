"""Circuit breaker middleware to prevent infinite tool retry loops.

When the agent gets stuck retrying the same tool with similar parameters,
this middleware detects the pattern and stops execution with a helpful error.
"""

import time
from collections import defaultdict
from typing import Any

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import AIMessage

from executive_assistant.logging import get_logger

logger = get_logger(__name__)


class ToolLoopBreaker:
    """
    Circuit breaker middleware that detects and prevents infinite tool retry loops.

    Tracks recent tool calls and detects when the agent is stuck in a retry pattern
    with the same tool and similar parameters. Stops execution with helpful guidance
    when a loop is detected.
    """

    def __init__(
        self,
        max_retries: int = 3,
        similarity_threshold: float = 0.7,
        time_window: float = 30.0,
    ):
        """
        Initialize the circuit breaker.

        Args:
            max_retries: Maximum identical/similar tool calls before breaking
            similarity_threshold: How similar arguments must be (0-1) to count as retry
            time_window: Time window in seconds to track tool calls (resets after this)
        """
        self.max_retries = max_retries
        self.similarity_threshold = similarity_threshold
        self.time_window = time_window

        # Track tool calls: {thread_id: [(tool_name, args, kwargs, timestamp), ...]}
        self._call_history: defaultdict[str, list[tuple[str, dict, dict, float]]] = defaultdict(
            list
        )

    def _cleanup_old_calls(self, thread_id: str, current_time: float) -> None:
        """Remove calls older than time_window."""
        cutoff = current_time - self.time_window
        self._call_history[thread_id] = [
            (name, args, kwargs, ts)
            for name, args, kwargs, ts in self._call_history[thread_id]
            if ts > cutoff
        ]

    def _args_similarity(self, args1: dict, args2: dict) -> float:
        """Calculate similarity between two argument dicts (0-1)."""
        if not args1 and not args2:
            return 1.0

        if not args1 or not args2:
            return 0.0

        # Check key overlap
        keys1 = set(args1.keys())
        keys2 = set(args2.keys())

        if not keys1 or not keys2:
            return 0.0

        # Calculate similarity based on shared keys and values
        shared_keys = keys1 & keys2
        total_keys = keys1 | keys2

        if not total_keys:
            return 0.0

        # Key similarity: ratio of shared keys
        key_sim = len(shared_keys) / len(total_keys)

        # Value similarity for shared keys
        if shared_keys:
            matching_values = sum(
                1 for k in shared_keys if str(args1.get(k)) == str(args2.get(k))
            )
            value_sim = matching_values / len(shared_keys) if shared_keys else 0
        else:
            value_sim = 0

        # Combined similarity (weighted toward values)
        return 0.3 * key_sim + 0.7 * value_sim

    def _detect_loop(
        self, thread_id: str, tool_name: str, tool_args: dict, tool_kwargs: dict
    ) -> tuple[bool, str]:
        """
        Detect if this tool call is part of a retry loop.

        Returns:
            (is_loop, guidance_message)
        """
        current_time = time.time()
        self._cleanup_old_calls(thread_id, current_time)

        history = self._call_history[thread_id]

        # Count similar recent calls
        similar_calls = 0
        for prev_name, prev_args, prev_kwargs, _ in history:
            if prev_name == tool_name:
                # Combine args and kwargs for comparison
                prev_all = {**prev_args, **prev_kwargs}
                curr_all = {**tool_args, **tool_kwargs}

                similarity = self._args_similarity(prev_all, prev_all)
                if similarity >= self.similarity_threshold:
                    similar_calls += 1

        if similar_calls >= self.max_retries:
            # Detected a loop!
            guidance = self._get_guidance(tool_name, tool_args)
            return True, guidance

        return False, ""

    def _get_guidance(self, tool_name: str, tool_args: dict) -> str:
        """Generate helpful guidance based on the tool that's looping."""
        # Common patterns and their solutions
        if tool_name == "write_file":
            return (
                "LOOP DETECTED: The agent is repeatedly trying to write a file with similar content.\n\n"
                "Common causes:\n"
                "1. Passing a dict/object instead of a string for `content` parameter\n"
                "2. Trying to write JSON without converting to string first\n\n"
                "Solution: Ensure `content` is a string. For JSON, pass it as a string like '{\"key\": \"value\"}' "
                "or use json.dumps() to convert your dict to a string first."
            )
        elif tool_name in ["insert_tdb_table", "update_tdb_table"]:
            return (
                "LOOP DETECTED: The agent is repeatedly trying to write to a database table.\n\n"
                "Common causes:\n"
                "1. Data format mismatch (passing dict instead of JSON string)\n"
                "2. Missing required columns\n"
                "3. Incorrect WHERE clause format\n\n"
                "Solution: Check the data parameter is properly formatted JSON string."
            )
        elif "search" in tool_name.lower():
            return (
                "LOOP DETECTED: The agent is repeatedly searching with similar queries.\n\n"
                "This suggests the search isn't finding what's needed. Consider:\n"
                "1. Trying different search terms\n"
                "2. Using a different search tool\n"
                "3. Providing the information directly without searching"
            )
        else:
            return (
                f"LOOP DETECTED: The agent is repeatedly calling `{tool_name}` with similar parameters.\n\n"
                f"This suggests an issue with the tool parameters or approach. "
                f"Try a different tool or approach."
            )

    def __call__(
        self,
        runnable: Any,
        input: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute the agent with loop detection.

        This middleware wraps the agent execution and monitors for tool call loops.
        """
        thread_id = config.get("configurable", {}).get("thread_id") if config else None

        # Track agent actions for loop detection
        original_run = runnable.__call__

        def wrapped_run(inp: dict[str, Any], cfg: dict[str, Any] | None = None) -> Any:
            nonlocal thread_id
            if cfg and cfg.get("configurable", {}).get("thread_id"):
                thread_id = cfg["configurable"]["thread_id"]

            # Process normally, but watch for tool call loops
            for event in original_run(inp, cfg):
                # Check for tool calls in the event
                if isinstance(event, dict):
                    if "messages" in event:
                        for msg in event["messages"]:
                            if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
                                for tool_call in msg.tool_calls:
                                    tool_name = tool_call.get("name", "")
                                    tool_args = tool_call.get("args", {})

                                    if thread_id:
                                        is_loop, guidance = self._detect_loop(
                                            thread_id, tool_name, tool_args, {}
                                        )

                                        if is_loop:
                                            # Return error response to break the loop
                                            logger.warning(
                                                f"ToolLoopBreaker: Loop detected for {tool_name} on {thread_id}"
                                            )

                                            # Return AIMessage with the guidance
                                            from langchain_core.messages import AIMessage, ToolMessage

                                            return [
                                                AIMessage(
                                                    content=f"**{guidance}**\n\n"
                                                    f"The task cannot be completed with the current approach. "
                                                    f"Please try a different approach or tool."
                                                )
                                            ]

                                    # Record this call
                                    self._call_history[thread_id].append(
                                        (tool_name, tool_args, {}, time.time())
                                    )

                yield event

        return wrapped_run(inp, config)


def get_tool_loop_breaker(
    max_retries: int = 3,
    similarity_threshold: float = 0.7,
    time_window: float = 30.0,
) -> ToolLoopBreaker:
    """Get a singleton ToolLoopBreaker instance."""
    return ToolLoopBreaker(
        max_retries=max_retries,
        similarity_threshold=similarity_threshold,
        time_window=time_window,
    )
