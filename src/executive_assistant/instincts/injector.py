"""Instinct injector for loading learned behavioral patterns into system prompts.

The injector retrieves applicable instincts for the current context and formats
them for injection into the agent's system prompt between BASE_PROMPT and CHANNEL_APPENDIX.
"""

import logging
from typing import Any

from executive_assistant.storage.instinct_storage import get_instinct_storage

logger = logging.getLogger(__name__)


class InstinctInjector:
    """Injector for loading applicable instincts into system prompts."""

    # Conflict resolution rules: (domain, action_keyword) -> overrides
    CONFLICT_RESOLUTION = {
        # High-priority overrides
        ("timing", "urgent"): {
            "overrides": [
                ("communication", "detailed"),
                ("communication", "thorough"),
                ("communication", "explain"),
                ("learning_style", "explain"),
            ],
            "min_confidence": 0.6,
        },
        ("communication", "concise"): {
            "overrides": [
                ("communication", "detailed"),
                ("communication", "elaborate"),
                ("communication", "thorough"),
            ],
            "min_confidence": 0.6,
        },
        ("communication", "brief"): {
            "overrides": [
                ("communication", "detailed"),
                ("communication", "elaborate"),
            ],
            "min_confidence": 0.6,
        },
        ("emotional_state", "frustrated"): {
            "overrides": [
                ("workflow", "standard"),
                ("communication", "brief"),
            ],
            "min_confidence": 0.5,  # Lower threshold for emotional state
        },
        ("emotional_state", "confused"): {
            "overrides": [
                ("communication", "brief"),
                ("communication", "concise"),
            ],
            "min_confidence": 0.5,
        },
    }

    # Domain-specific guidance templates
    DOMAIN_TEMPLATES = {
        "communication": "## Communication Style\n{actions}\n",
        "format": "## Output Format Preferences\n{actions}\n",
        "workflow": "## Workflow Patterns\n{actions}\n",
        "tool_selection": "## Tool Selection Preferences\n{actions}\n",
        "verification": "## Quality Standards\n{actions}\n",
        "timing": "## Timing Preferences\n{actions}\n",
        # NEW domains
        "emotional_state": """## Emotional Context
The user appears to be in the following emotional state:
{actions}

Adjust your response accordingly:
- Be extra supportive and patient
- Offer to break down complex tasks
- Provide alternative approaches
""",
        "learning_style": """## Learning Approach
Based on past interactions, the user prefers:
{actions}

Adapt your explanations:
- Teaching mode: Show reasoning, offer resources
- Exploration mode: Provide options, explain trade-offs
- Hands-on mode: Focus on practical implementation
""",
        "expertise": """## Known Expertise Areas
The user has demonstrated knowledge in:
{actions}

Adjust your explanations:
- Skip basics in known areas
- Provide context for new topics
- Assume familiarity with domain terminology
""",
    }

    def __init__(self) -> None:
        self.storage = get_instinct_storage()

    def _resolve_conflicts(self, instincts: list[dict]) -> list[dict]:
        """Remove overridden instincts based on priority rules.

        Args:
            instincts: List of instinct dictionaries

        Returns:
            Filtered list with conflicts resolved
        """
        kept = []
        removed_count = 0

        for instinct in instincts:
            domain = instinct["domain"]
            action = instinct["action"].lower()
            confidence = instinct["confidence"]

            # Check if this instinct should be kept or overridden
            should_keep = True
            override_reason = None

            for kept_instinct in kept:
                # Check if any kept instinct overrides the current one
                for (rule_domain, rule_action), rule in self.CONFLICT_RESOLUTION.items():
                    # Does the kept instinct match a rule?
                    if (kept_instinct["domain"] == rule_domain and
                            rule_action in kept_instinct["action"].lower() and
                            kept_instinct["confidence"] >= rule["min_confidence"]):

                        # Check if current instinct is in the override list
                        for override_domain, override_action in rule["overrides"]:
                            if (domain == override_domain and
                                    override_action in action):

                                should_keep = False
                                override_reason = (
                                    f"Overridden by {rule_domain}:{rule_action} "
                                    f"(confidence: {kept_instinct['confidence']:.2f})"
                                )
                                break

                        if not should_keep:
                            break

                if not should_keep:
                    break

            if should_keep:
                kept.append(instinct)
            else:
                logger.debug(f"Conflict resolution: {override_reason} | Removed: {instinct['action'][:50]}")
                removed_count += 1

        if removed_count > 0:
            logger.info(f"Conflict resolution removed {removed_count} contradictory instincts")

        return kept

    def build_instincts_context(
        self,
        thread_id: str,
        user_message: str | None = None,
        min_confidence: float = 0.5,
        max_per_domain: int = 3,
    ) -> str:
        """
        Build instincts section for system prompt.

        Args:
            thread_id: Thread identifier
            user_message: Current user message for context filtering (optional)
            min_confidence: Minimum confidence threshold (default 0.5)
            max_per_domain: Maximum instincts to include per domain (default 3)

        Returns:
            Formatted instincts section for injection into system prompt
        """
        # Get applicable instincts
        if user_message:
            # Context-aware: get instincts matching current situation
            instincts = self.storage.get_applicable_instincts(
                context=user_message,
                thread_id=thread_id,
                max_count=max_per_domain * 6,  # Get more, then filter by domain
            )
            # Fall back to all high-confidence instincts if no matches
            if not instincts:
                instincts = self.storage.list_instincts(
                    min_confidence=min_confidence,
                    thread_id=thread_id,
                )
        else:
            # Load all high-confidence instincts
            instincts = self.storage.list_instincts(
                min_confidence=min_confidence,
                thread_id=thread_id,
            )

        if not instincts:
            return ""

        # Apply metadata-based confidence adjustments
        for instinct in instincts:
            metadata = instinct.get("metadata", {})
            occurrence_count = metadata.get("occurrence_count", 0)

            # Boost confidence for frequently-reinforced instincts
            if occurrence_count >= 5:
                # Cap boost at +0.15
                boost = min(0.15, occurrence_count * 0.03)
                instinct["confidence"] = min(1.0, instinct["confidence"] + boost)
                instinct["confidence_boosted"] = True  # Track for debugging
                logger.debug(
                    f"Boosted confidence by {boost:.3f} (occurrence_count: {occurrence_count}) "
                    f"for: {instinct['action'][:50]}"
                )

        # Resolve conflicts: remove contradictory instincts
        instincts = self._resolve_conflicts(instincts)

        # Group by domain
        by_domain: dict[str, list[dict]] = {}
        for instinct in instincts:
            domain = instinct["domain"]
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(instinct)

        # Build context section
        sections = []

        # Add header
        sections.append("## Behavioral Patterns")
        sections.append("")
        sections.append(f"Apply these learned preferences from your interactions:")
        sections.append("")

        # Add domain-specific sections
        for domain in sorted(by_domain.keys()):
            domain_instincts = by_domain[domain][:max_per_domain]

            # Format actions for this domain
            actions = []
            for instinct in domain_instincts:
                confidence = instinct["confidence"]
                trigger = instinct["trigger"]
                action = instinct["action"]

                # Format based on confidence
                if confidence >= 0.8:
                    actions.append(f"- **{action}** (always apply)")
                elif confidence >= 0.6:
                    actions.append(f"- {action}")
                else:
                    actions.append(f"- {action} (when: {trigger})")

            # Add domain section
            domain_name = domain.replace("_", " ").title()
            sections.append(f"### {domain_name}")
            sections.extend(actions)
            sections.append("")

        return "\n".join(sections)

    def get_instincts_summary(
        self,
        thread_id: str,
        min_confidence: float = 0.5,
    ) -> dict[str, Any]:
        """
        Get summary statistics about loaded instincts.

        Args:
            thread_id: Thread identifier
            min_confidence: Minimum confidence threshold

        Returns:
            Dictionary with instinct statistics
        """
        instincts = self.storage.list_instincts(
            min_confidence=min_confidence,
            thread_id=thread_id,
        )

        # Count by domain
        by_domain: dict[str, int] = {}
        total_confidence = 0.0

        for instinct in instincts:
            domain = instinct["domain"]
            by_domain[domain] = by_domain.get(domain, 0) + 1
            total_confidence += instinct["confidence"]

        avg_confidence = total_confidence / len(instincts) if instincts else 0.0

        return {
            "total": len(instincts),
            "by_domain": by_domain,
            "avg_confidence": avg_confidence,
            "min_confidence": min_confidence,
        }


_instinct_injector = InstinctInjector()


def get_instinct_injector() -> InstinctInjector:
    """Get singleton instinct injector instance."""
    return _instinct_injector
