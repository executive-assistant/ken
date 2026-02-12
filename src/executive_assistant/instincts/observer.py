"""Instinct observer for automatic pattern detection and learning.

The observer monitors user interactions and automatically detects behavioral patterns:
- Corrections: User corrects assistant responses
- Repetitions: User repeats similar requests
- Preferences: User expresses preferences
- Format choices: User consistently prefers certain formats

Detected patterns are recorded as instincts with confidence scores.
"""

import re
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from executive_assistant.storage.instinct_storage import get_instinct_storage


def _utc_now() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


class InstinctObserver:
    """Observer for detecting behavioral patterns from user interactions."""

    # Pattern signatures for automatic detection
    PATTERNS = {
        "correction": {
            "triggers": [
                r"no, i meant",
                r"actually,?",
                r"wait, that's not",
                r"let me clarify",
                r"i want you to instead",
                r"not quite, ",
            ],
            "default_instinct": {
                "trigger": "user corrects previous response",
                "action": "acknowledge correction and adjust approach immediately",
                "domain": "communication",
            },
        },
        "repetition": {
            "triggers": [
                r"(again|once more|repeat)",
                r"like you did before",
                r"same as last time",
                r"remember when you",
            ],
            "default_instinct": {
                "trigger": "user requests repetition of previous action",
                "action": "follow the exact same pattern as before",
                "domain": "workflow",
            },
        },
        "preference_verbosity": {
            "patterns": [
                (r"(be brief|concise|short|to the point)", "concise"),
                (r"(more detail|explain more|elaborate|expand)", "detailed"),
                (r"(keep it simple|don't over-explain)", "simple"),
            ],
            "domain": "communication",
        },
        "preference_format": {
            "patterns": [
                (r"(json|csv|markdown|table)", "format_preference"),
                (r"(bullet points|list format)", "bullets"),
                (r"(paragraph|prose|narrative)", "prose"),
            ],
            "domain": "format",
        },
    }

    def __init__(self) -> None:
        self.storage = get_instinct_storage()

    def observe_message(
        self,
        user_message: str,
        assistant_message: str | None = None,
        thread_id: str | None = None,
    ) -> list[str]:
        """
        Observe a message exchange and detect patterns.

        Args:
            user_message: The user's message
            assistant_message: Optional assistant response (for context)
            thread_id: Thread identifier

        Returns:
            List of instinct IDs created or updated
        """
        detected = []

        # Check for corrections
        if self._is_correction(user_message):
            detected.extend(self._handle_correction(user_message, thread_id))

        # Check for repetitions
        if self._is_repetition(user_message):
            detected.extend(self._handle_repetition(user_message, thread_id))

        # Check for verbosity preferences
        detected.extend(self._detect_verbosity_preference(user_message, thread_id))

        # Check for format preferences
        detected.extend(self._detect_format_preference(user_message, thread_id))

        return detected

    def _is_correction(self, message: str) -> bool:
        """Check if message contains correction language."""
        message_lower = message.lower()

        for trigger in self.PATTERNS["correction"]["triggers"]:
            # Remove regex special chars for plain string matching
            import re
            pattern = trigger.replace(r"?", r"\?")  # Escape question marks
            if re.search(pattern, message_lower, re.IGNORECASE):
                return True

        return False

    def _is_repetition(self, message: str) -> bool:
        """Check if message requests repetition."""
        message_lower = message.lower()

        for trigger in self.PATTERNS["repetition"]["triggers"]:
            # Use regex search for pattern matching
            if re.search(trigger, message_lower, re.IGNORECASE):
                return True

        return False

    def _handle_correction(self, message: str, thread_id: str | None = None) -> list[str]:
        """Handle user correction pattern."""
        # Check if we already have a correction instinct
        existing = self.storage.list_instincts(
            domain="communication",
            thread_id=thread_id,
        )

        for instinct in existing:
            if "correct" in instinct["trigger"].lower():
                # Reinforce existing instinct
                self.storage.adjust_confidence(instinct["id"], 0.05, thread_id)
                return [instinct["id"]]

        # Create new correction instinct
        instinct_id = self.storage.create_instinct(
            trigger="user corrects previous response",
            action="acknowledge correction immediately, apologize, and adjust approach",
            domain="communication",
            source="correction-detected",
            confidence=0.7,
            thread_id=thread_id,
        )

        return [instinct_id]

    def _handle_repetition(self, message: str, thread_id: str | None = None) -> list[str]:
        """Handle user repetition pattern."""
        # Check if we already have a repetition instinct
        existing = self.storage.list_instincts(
            domain="workflow",
            thread_id=thread_id,
        )

        for instinct in existing:
            if "repeat" in instinct["trigger"].lower() or "again" in instinct["trigger"].lower():
                self.storage.adjust_confidence(instinct["id"], 0.05, thread_id)
                return [instinct["id"]]

        # Create new repetition instinct
        instinct_id = self.storage.create_instinct(
            trigger="user requests repetition",
            action="repeat the same action or follow the same pattern as before",
            domain="workflow",
            source="repetition-confirmed",
            confidence=0.6,
            thread_id=thread_id,
        )

        return [instinct_id]

    def _detect_verbosity_preference(self, message: str, thread_id: str | None = None) -> list[str]:
        """Detect verbosity preferences in user message."""
        detected = []

        for regex, pref_type in self.PATTERNS["preference_verbosity"]["patterns"]:
            if re.search(regex, message, re.IGNORECASE):
                # Check for existing instinct
                existing = self.storage.list_instincts(
                    domain="communication",
                    thread_id=thread_id,
                )

                for instinct in existing:
                    if pref_type in instinct["action"].lower():
                        # Reinforce
                        self.storage.adjust_confidence(instinct["id"], 0.05, thread_id)
                        return [instinct["id"]]

                # Create new instinct
                action_map = {
                    "concise": "be brief and concise, skip detailed explanations",
                    "detailed": "provide thorough explanations with examples",
                    "simple": "use simple language and avoid jargon",
                }

                instinct_id = self.storage.create_instinct(
                    trigger=f"user prefers {pref_type} responses",
                    action=action_map.get(pref_type, f"respond in a {pref_type} manner"),
                    domain="communication",
                    source="preference-expressed",
                    confidence=0.7,
                    thread_id=thread_id,
                )

                detected.append(instinct_id)
                break  # Only create one instinct per message

        return detected

    def _detect_format_preference(self, message: str, thread_id: str | None = None) -> list[str]:
        """Detect format preferences in user message."""
        detected = []

        for regex, pref_name in self.PATTERNS["preference_format"]["patterns"]:
            if re.search(regex, message, re.IGNORECASE):
                # Check for existing instinct
                existing = self.storage.list_instincts(
                    domain="format",
                    thread_id=thread_id,
                )

                for instinct in existing:
                    if pref_name in instinct["action"].lower():
                        # Reinforce
                        self.storage.adjust_confidence(instinct["id"], 0.05, thread_id)
                        return [instinct["id"]]

                # Create new instinct
                if pref_name == "bullets":
                    action = "use bullet points for lists and structured content"
                elif pref_name == "prose":
                    action = "use paragraph/prose format with full sentences"
                else:
                    action = f"use {pref_name} format by default"

                instinct_id = self.storage.create_instinct(
                    trigger=f"user prefers {pref_name} format",
                    action=action,
                    domain="format",
                    source="preference-expressed",
                    confidence=0.8,
                    thread_id=thread_id,
                )

                detected.append(instinct_id)
                break

        return detected

    # ========================================================================
    # SUCCESS RATE TRACKING: Learn which instincts actually help
    # ========================================================================

    # Satisfaction and frustration patterns for outcome detection
    SATISFACTION_PATTERNS = {
        "triggers": [
            r"\b(perfect|great|awesome|thanks|exactly what)\b",
            r"\b(that's what I needed|just what I wanted|love it)\b",
            r"\b(amazing|brilliant|excellent)\b",
            r"👍|✅|🎉|😊",
        ],
    }

    FRUSTRATION_PATTERNS = {
        "triggers": [
            r"\b(nevermind|forget it|whatever)\b",
            r"^(ok|okay|fine)[!.]*$",
            r"\?+$",
        ],
    }

    def record_outcome(
        self,
        instinct_id: str,
        success: bool,
        thread_id: str | None = None,
    ) -> None:
        """Record whether applying an instinct led to success.

        Args:
            instinct_id: Instinct identifier
            success: True if user was satisfied, False if frustrated
            thread_id: Thread identifier
        """
        instinct = self.storage.get_instinct(instinct_id, thread_id)
        if not instinct:
            return

        metadata = instinct.get("metadata", {})

        # Update success rate (moving average)
        current_rate = metadata.get("success_rate", 1.0)
        alpha = 0.2  # Learning rate (how fast to adapt)
        new_rate = (alpha * (1.0 if success else 0.0)) + ((1 - alpha) * current_rate)

        metadata["success_rate"] = new_rate
        instinct["metadata"] = metadata
        instinct["updated_at"] = _utc_now()

        # Save to storage
        self.storage._update_snapshot(instinct, thread_id)

        logger.debug(
            f"Recorded outcome for instinct: {success} | "
            f"success_rate: {current_rate:.2f} → {new_rate:.2f} | "
            f"{instinct['action'][:50]}"
        )

    def observe_conversation_outcome(
        self,
        user_message: str,
        applied_instinct_ids: list[str],
        thread_id: str | None = None,
    ) -> list[str]:
        """Detect if instincts led to positive or negative outcome.

        Args:
            user_message: Latest user message
            applied_instinct_ids: Instincts that were applied in previous response
            thread_id: Thread identifier

        Returns:
            List of instinct IDs that were updated
        """
        if not applied_instinct_ids:
            return []

        updated = []

        # Check for satisfaction
        for pattern in self.SATISFACTION_PATTERNS["triggers"]:
            if re.search(pattern, user_message, re.IGNORECASE):
                # Record success for all applied instincts
                for instinct_id in applied_instinct_ids:
                    self.record_outcome(instinct_id, success=True, thread_id=thread_id)
                    updated.append(instinct_id)

                if updated:
                    logger.info(
                        f"Detected satisfaction - reinforced {len(updated)} instincts"
                    )
                return updated

        # Check for frustration
        for pattern in self.FRUSTRATION_PATTERNS["triggers"]:
            if re.search(pattern, user_message, re.IGNORECASE):
                # Record failure for all applied instincts
                for instinct_id in applied_instinct_ids:
                    self.record_outcome(instinct_id, success=False, thread_id=thread_id)
                    updated.append(instinct_id)

                if updated:
                    logger.warning(
                        f"Detected frustration - penalized {len(updated)} instincts"
                    )
                return updated

        return updated


_instinct_observer = InstinctObserver()


def get_instinct_observer() -> InstinctObserver:
    return _instinct_observer
