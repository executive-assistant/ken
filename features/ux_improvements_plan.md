# UX Improvements Plan

**Date:** 2025-02-02
**Status:** Draft
**Priority:** High
**Based on:** Persona testing with good, OK, and bad prompters

---

## Executive Summary

Executive Assistant performs excellently with good prompts (Grade: A) but struggles with vague requests (Grade: C). This plan outlines specific improvements to make the agent more user-friendly for all skill levels.

**Current Performance by Persona:**
- **Good Prompts** (Tech Lead, Data Analyst): ⭐⭐⭐⭐⭐ (Grade: A)
- **OK Prompts** (Casual User, Busy Manager): ⭐⭐⭐⭐ (Grade: B+)
- **Bad Prompts** (Confused User, Frustrated User): ⭐⭐⭐ (Grade: C)

---

## Problem Statement

Executive Assistant is like a power tool - excellent in skilled hands, challenging for beginners. The agent makes assumptions instead of asking clarifying questions, and doesn't guide confused users toward better prompts.

**Key Issues:**
1. **Vague Request Handling** - Struggles with "help", "i need thing"
2. **Missing Clarifications** - Doesn't ask when information is missing
3. **No Progressive Disclosure** - Doesn't offer next steps
4. **Lacks Prompt Guidance** - Doesn't teach users to prompt better
5. **Technical Error Messages** - Shows stack traces instead of user-friendly help

---

## Priority 1: Better Vague Request Handling

### Current Behavior
```python
# User says: "help"
Agent: (generic help or long feature list) OR
Agent: "I don't understand what you mean"
```

### Desired Behavior
```python
# User says: "help"
Agent: """
I'd love to help! Could you be a bit more specific?

Here are some things I can do:
📊 Track work: "Log 4 hours to Project Alpha - code review"
🔍 Search web: "Find recent articles about LangChain"
⏰ Reminders: "Remind me to review PRs every weekday at 3pm"
📈 Analyze: "Show me my work hours for this week"

What would you like help with?
"""
```

### Implementation Plan

1. **Create Intent Detection System**
   - Detect when user intent confidence is low (< 0.5)
   - Identify vague patterns: "help", "do thing", "stuff"
   - Trigger guided help workflow

2. **Build Help Templates**
   - Categorized examples by feature (timesheets, search, reminders, analysis)
   - Show concrete examples with context
   - Keep it brief (5-7 examples max)

3. **Add Progressive Questioning**
   - Start broad: "What area do you need help with?"
   - Narrow down: "For work tracking or web search?"
   - Get specific: "What do you want to track/search for?"

### Code Changes Required

**File:** `src/executive_assistant/agent/nodes.py` (or appropriate agent file)

```python
def detect_vague_request(state: AgentState) -> bool:
    """Check if user request is too vague."""
    user_input = state["messages"][-1].content.lower()

    vague_patterns = [
        r"^help$",
        r"^i need (something|thing|stuff)$",
        r"^(can you|could you) (do|make)( the)? (thing|stuff)$",
        r"^(hi|hello)$",  # Just greeting without request
    ]

    for pattern in vague_patterns:
        if re.match(pattern, user_input.strip()):
            return True

    # Check if input is very short (< 10 chars) and unclear
    if len(user_input.strip()) < 10:
        return True

    return False


def provide_guided_help(state: AgentState) -> str:
    """Provide structured help when request is vague."""

    help_template = """
I'd love to help! Could you be a bit more specific?

Here are some things I can do:

📊 **Track Work**
   - "Log 4 hours to Project Alpha - code review"
   - "Create a timesheet for this week"

🔍 **Search Web**
   - "Find recent articles about LangChain updates"
   - "Search for Python best practices 2025"

⏰ **Reminders**
   - "Remind me to review PRs every weekday at 3pm"
   - "Set reminder for team standup tomorrow at 10am"

📈 **Data Analysis**
   - "Show me my work hours for this week"
   - "Analyze my productivity patterns"

💾 **File Management**
   - "List files in /projects"
   - "Search for TODO comments in my codebase"

What would you like help with?
"""

    return help_template
```

**Integration Point:** Add to agent's decision tree before routing to tools.

---

## Priority 2: Ask Clarifying Questions

### Current Behavior
```python
# User says: "log 5 hours to Project X"
Agent: (Immediately logs it without asking for details)
```

### Desired Behavior
```python
# User says: "log 5 hours to Project X"
Agent: """
I'll log 5 hours to Project X.

Quick questions to help you better:
- What date is this for? (default: today)
- What work did you do? (brief description)
"""

# Or even better - if memory has this info:
Agent: """
I'll log 5 hours to Project X for today's code review.
Is that correct? (You usually do code reviews for Project X)
"""
```

### Implementation Plan

1. **Detect Missing Information**
   - Date (default: today)
   - Project (required)
   - Hours (required)
   - Description/Task (important for context)

2. **Use Memory to Fill Gaps**
   - Check user's past timesheets
   - Recall common patterns
   - Suggest based on history

3. **Ask Only What's Needed**
   - Don't ask if memory has it
   - Show defaults clearly
   - Allow quick confirm/modify

### Code Changes Required

**File:** `src/executive_assistant/tools/tdb_tools.py` (or timesheet tools)

```python
def detect_missing_timesheet_info(user_input: str, thread_id: str) -> dict:
    """Detect what information is missing from timesheet request."""
    missing = {}

    # Extract what we can from input
    has_hours = bool(re.search(r'\d+\s*hours?', user_input, re.IGNORECASE))
    has_project = bool(re.search(r'(project|for)\s+\w+', user_input, re.IGNORECASE))
    has_date = bool(re.search(r'(today|yesterday|tomorrow|\d{4}-\d{2}-\d{2})', user_input, re.IGNORECASE))
    has_description = len(user_input.split()) > 5  # Rough heuristic

    # Check memory for patterns
    memories = get_user_memories(thread_id, limit=5)
    likely_project = extract_common_project(memories)
    likely_description = extract_common_task(memories)

    if not has_date:
        missing["date"] = {
            "required": False,
            "default": "today",
            "question": "What date is this for?"
        }

    if not has_project:
        if likely_project:
            missing["project"] = {
                "required": True,
                "suggestion": likely_project,
                "question": f"Is this for {likely_project}? (That's your most common project)"
            }
        else:
            missing["project"] = {
                "required": True,
                "question": "Which project is this for?"
            }

    if not has_description:
        if likely_description:
            missing["description"] = {
                "required": False,
                "suggestion": likely_description,
                "question": f"What did you work on? (Usually you do: {likely_description})"
            }
        else:
            missing["description"] = {
                "required": False,
                "question": "What work did you do? (brief description)"
            }

    return missing


def generate_clarifying_questions(missing_info: dict) -> str:
    """Generate natural clarifying questions."""
    questions = []

    for field, info in missing_info.items():
        if info.get("suggestion"):
            questions.append(f"- **{field.capitalize()}**: {info['question']}")
        else:
            questions.append(f"- **{field.capitalize()}**: {info['question']}")

    return """
I'd like to clarify a few things to help you better:

""" + "\n".join(questions) + """

Should I proceed with reasonable defaults for the rest?
"""
```

**Memory Integration:**
```python
def extract_user_patterns(thread_id: str) -> dict:
    """Extract common patterns from user's history."""
    memories = get_user_memories(thread_id, category="timesheet", limit=20)

    projects = Counter()
    tasks = Counter()
    hour_patterns = Counter()

    for memory in memories:
        if "project" in memory.data:
            projects[memory.data["project"]] += 1
        if "task" in memory.data:
            tasks[memory.data["task"]] += 1
        if "hours" in memory.data:
            hour_patterns[memory.data["hours"]] += 1

    return {
        "likely_project": projects.most_common(1)[0] if projects else None,
        "likely_task": tasks.most_common(1)[0] if tasks else None,
        "common_hours": hour_patterns.most_common(3) if hour_patterns else []
    }
```

---

## Priority 3: Progressive Disclosure

### Current Behavior
```python
# User says: "Create a timesheet table"
Agent: "Table created with columns: date, project, hours, description"
# (End of interaction)
```

### Desired Behavior
```python
# User says: "Create a timesheet table"
Agent: """
✅ Created timesheet table with columns: date, project, hours, description

Next steps you might want:
- Add your first entry: "Log 4 hours to Project Alpha"
- Set up automatic reminders: "Remind me to log hours daily at 6pm"
- Create a summary: "Show me my hours for this week"
- Export data: "Export timesheet to CSV"

Want me to help with any of these?
"""
```

### Implementation Plan

1. **Track Completed Tasks**
   - Store last action in conversation state
   - Identify task type (creation, search, analysis, etc.)

2. **Generate Contextual Next Steps**
   - Based on what was just done
   - Based on user's typical patterns (from memory)
   - Keep it to 3-5 options max

3. **Offer Proactive Help**
   - Don't wait for user to ask
   - Suggest logical next actions
   - Learn from what user usually does next

### Code Changes Required

**File:** `src/executive_assistant/middleware/progressive_disclosure.py` (new file)

```python
from typing import List, Dict, Any
from executive_assistant.storage.thread_storage import get_state_history


class ProgressiveDisclosure:
    """Offer contextual next steps after task completion."""

    # Define next step templates by task type
    NEXT_STEPS = {
        "create_table": [
            "Add your first entry",
            "Set up automatic reminders",
            "Create a summary view",
            "Export to CSV"
        ],
        "search_web": [
            "Save this to knowledge base",
            "Search for related topics",
            "Summarize findings",
            "Share with team"
        ],
        "set_reminder": [
            "Create recurring reminder",
            "Set up related reminders",
            "View all reminders",
            "Add reminder notes"
        ],
        "log_hours": [
            "Log more hours",
            "View weekly summary",
            "Analyze productivity",
            "Export timesheet"
        ],
        "create_file": [
            "Add content to file",
            "Create related files",
            "Commit to git",
            "Share with team"
        ]
    }

    def generate_next_steps(self, task_type: str, context: Dict[str, Any]) -> List[str]:
        """Generate contextual next steps."""
        templates = self.NEXT_STEPS.get(task_type, [])

        # Personalize based on user history
        if context.get("user_patterns"):
            common_next = self.get_common_next_action(task_type, context["user_patterns"])
            if common_next:
                templates.insert(0, common_next)

        return templates[:5]  # Max 5 suggestions

    def get_common_next_action(self, task_type: str, patterns: Dict) -> str:
        """Find what user usually does after this task."""
        # Analyze user's conversation history
        # Return most common next action
        pass

    def format_next_steps(self, task_name: str, next_steps: List[str]) -> str:
        """Format next steps as user-friendly message."""

        steps = "\n".join([f"- {step}" for step in next_steps])

        return f"""
✅ {task_name} complete!

Next steps you might want:
{steps}

Want me to help with any of these?
"""


def add_progressive_disclosure(state: AgentState) -> AgentState:
    """Add progressive disclosure to agent responses."""

    last_action = state.get("last_action")
    if not last_action:
        return state

    disclosure = ProgressiveDisclosure()
    next_steps = disclosure.generate_next_steps(
        last_action["type"],
        state.get("context", {})
    )

    if next_steps:
        message = disclosure.format_next_steps(
            last_action["description"],
            next_steps
        )
        state["suggested_next_steps"] = message

    return state
```

---

## Priority 4: User Education & Prompt Guidance

### Current Behavior
```python
# User says: "i need thing"
Agent: "I don't understand what you need"
```

### Desired Behavior
```python
# User says: "i need thing"
Agent: """
I'm not sure what you need. Could you be more specific?

For example, instead of "i need thing", try:
- "Create a timesheet table" (for data tracking)
- "Search for Python tutorials" (for web search)
- "Remind me about my meeting tomorrow" (for reminders)
- "Show me my work hours this week" (for analysis)

The more specific you are, the better I can help!
"""
```

### Implementation Plan

1. **Detect Poor Prompts**
   - Very short inputs (< 10 chars)
   - Vague nouns (thing, stuff, something)
   - Missing verbs or actions
   - Generic phrases only

2. **Provide Concrete Examples**
   - Show before/after comparisons
   - Keep examples relevant to user's interests (from memory)
   - Don't overwhelm (3 examples max)

3. **Educate Gradually**
   - First time: Detailed explanation with examples
   - Subsequent times: Brief reminder
   - After 3+ times: Pattern detected, suggest creating instinct

### Code Changes Required

**File:** `src/executive_assistant/middleware/prompt_guidance.py` (new file)

```python
import re
from typing import Optional, Tuple


class PromptGuidance:
    """Help users improve their prompts through gentle guidance."""

    # Patterns that indicate poor prompts
    POOR_PROMPT_PATTERNS = [
        (r"^(i need|need|want|get)( the)? (thing|stuff|something|it)$", "vague_noun"),
        (r"^(can you|could you)( please)?( do|make|create)( the)? (thing|stuff)$", "vague_request"),
        (r"^(help|assist|support)$", "just_help"),
        (r"^(ok|okay|yes|no)$", "response_only"),
    ]

    # Example improvements by category
    EXAMPLE_IMPROVEMENTS = {
        "vague_noun": {
            "poor": "i need thing",
            "better": [
                "Create a timesheet table",
                "Search for LangChain tutorials",
                "Set a reminder for tomorrow at 2pm"
            ]
        },
        "vague_request": {
            "poor": "can you do the thing",
            "better": [
                "Can you create a database for my daily tasks?",
                "Can you search for recent AI news?",
                "Can you analyze my work hours for this week?"
            ]
        },
        "just_help": {
            "poor": "help",
            "better": [
                "Help me log my work hours",
                "Help me find information about Python",
                "Help me organize my files"
            ]
        },
        "response_only": {
            "poor": "ok",
            "better": [
                "OK, create the table now",
                "OK, show me the search results",
                "OK, set that reminder for 3pm"
            ]
        }
    }

    def detect_poor_prompt(self, user_input: str) -> Optional[str]:
        """Detect if user's prompt needs improvement."""
        user_input_lower = user_input.lower().strip()

        for pattern, category in self.POOR_PROMPT_PATTERNS:
            if re.match(pattern, user_input_lower):
                return category

        # Check for extremely short input
        if len(user_input.strip()) < 8:
            return "too_short"

        return None

    def get_improvement_suggestion(
        self,
        category: str,
        user_context: Optional[dict] = None
    ) -> Tuple[str, list]:
        """Get specific improvement suggestions for user."""

        if category in self.EXAMPLE_IMPROVEMENTS:
            examples = self.EXAMPLE_IMPROVEMENTS[category]["better"]

            # Personalize based on user's common tasks
            if user_context and user_context.get("common_tasks"):
                user_tasks = user_context["common_tasks"][:3]
                examples = user_tasks + examples[:2]

            return self.EXAMPLE_IMPROVEMENTS[category]["poor"], examples

        # Generic suggestion for unknown categories
        return user_input, [
            "Be more specific about what you want",
            "Include details like: what, when, where, why",
            "Use complete sentences with clear actions"
        ]

    def format_guidance(
        self,
        poor_prompt: str,
        better_examples: list,
        is_first_time: bool = True
    ) -> str:
        """Format user-friendly prompt guidance."""

        if is_first_time:
            header = f"""
I'm not sure I understood "{poor_prompt}" correctly.

Here's how to be more specific:
"""
        else:
            header = f"""
To help me understand better, try:

"""

        examples = "\n".join([f"- "{example}" for example in better_examples])

        footer = """
The more specific you are, the better I can help!
"""

        return header + examples + footer


def should_provide_guidance(state: AgentState) -> bool:
    """Decide whether to provide prompt guidance."""

    # Count how many times we've given guidance recently
    guidance_count = state.get("prompt_guidance_count", 0)

    # Don't overdo it - max 3 times per conversation
    if guidance_count >= 3:
        return False

    # Check if user is repeatedly giving poor prompts
    poor_prompt_history = state.get("poor_prompt_history", [])
    if len(poor_prompt_history) >= 2:
        return True

    return False


def provide_prompt_guidance(state: AgentState) -> str:
    """Provide helpful prompt guidance to user."""

    guidance = PromptGuidance()
    user_input = state["messages"][-1].content

    category = guidance.detect_poor_prompt(user_input)

    if not category:
        return None

    poor, better = guidance.get_improvement_suggestion(
        category,
        state.get("user_context")
    )

    is_first_time = state.get("prompt_guidance_count", 0) == 0

    guidance_message = guidance.format_guidance(poor, better, is_first_time)

    # Update state
    state["prompt_guidance_count"] = state.get("prompt_guidance_count", 0) + 1
    state["poor_prompt_history"] = state.get("poor_prompt_history", [])
    state["poor_prompt_history"].append(user_input)

    return guidance_message
```

---

## Priority 5: User-Friendly Error Messages

### Current Behavior
```python
# User says: "log abc hours to Project X"
Agent: "NameError: invalid literal for int() with base 10: 'abc'"
# (Shows technical stack trace)
```

### Desired Behavior
```python
# User says: "log abc hours to Project X"
Agent: """
I couldn't log those hours because "abc" isn't a valid number.

Try again with a specific number:
- "log 4 hours to Project X"
- "log 2.5 hours to Project X"

How many hours did you work?
"""
```

### Implementation Plan

1. **Catch Common Errors**
   - Invalid numbers (hours, dates)
   - Missing required fields
   - Malformed requests
   - API failures

2. **Explain in Plain Language**
   - What went wrong
   - Why it went wrong
   - How to fix it
   - Example of correct input

3. **Maintain Conversation Flow**
   - Don't just error - guide to correction
   - Keep context of what user was trying to do
   - Offer to retry with corrections

### Code Changes Required

**File:** `src/executive_assistant/middleware/error_handling.py` (enhance existing)

```python
from typing import Dict, Any
from langchain_core.messages import AIMessage


class UserFriendlyErrors:
    """Convert technical errors into user-friendly guidance."""

    # Error message templates
    ERROR_TEMPLATES = {
        "invalid_number": {
            "pattern": r"(invalid literal|ValueError|not a number)",
            "message": """
I couldn't process that number.

{input} isn't a valid number. Try again with:
- A whole number: "4 hours"
- A decimal: "2.5 hours"
- Specific time: "3 hours 30 minutes"

How many hours did you work?
"""
        },
        "missing_required": {
            "pattern": r"(missing|required|KeyError|NoneType)",
            "message": """
I'm missing some information to do that.

To {task}, I need:
{required_fields}

Could you provide those details?
"""
        },
        "api_failure": {
            "pattern": r"(RateLimitError|APIError|ConnectionError)",
            "message": """
I'm having trouble connecting to my services right now.

This might be:
- Rate limiting (too many requests)
- Network connection issues
- Service temporarily unavailable

Let's try again in a moment, or you can:
- Wait a few minutes and retry
- Use a different service
- Contact support if this persists
"""
        },
        "file_not_found": {
            "pattern": r"(FileNotFoundError|No such file)",
            "message": """
I couldn't find that file.

Checked: {path}

Suggestions:
- Check the file path is correct
- List files in the directory first
- Make sure the file exists

Want me to list files in that directory?
"""
        }
    }

    def categorize_error(self, error: Exception) -> str:
        """Categorize error into user-friendly type."""
        error_message = str(error)

        for category, template in self.ERROR_TEMPLATES.items():
            if re.search(template["pattern"], error_message):
                return category

        return "unknown_error"

    def format_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> str:
        """Format user-friendly error message."""

        category = self.categorize_error(error)

        if category == "unknown_error":
            # Generic fallback
            return """
Something went wrong when I tried to help you.

What you were trying to do: {task}

Error details: {error}

Can you try rephrasing your request? Or contact support if this keeps happening.
"""

        template = self.ERROR_TEMPLATES[category]["message"]

        # Fill in context variables
        formatted = template.format(**context)

        return formatted


def handle_error_gracefully(
    error: Exception,
    state: AgentState
) -> AIMessage:
    """Convert error into helpful user message."""

    handler = UserFriendlyErrors()

    context = {
        "input": state["messages"][-1].content,
        "task": state.get("current_task", "complete your request"),
        "path": state.get("file_path", "the specified location"),
        "required_fields": format_required_fields(state.get("missing_fields", [])),
    }

    friendly_message = handler.format_error(error, context)

    return AIMessage(content=friendly_message)
```

---

## Implementation Timeline

### Phase 1: Quick Wins (1-2 weeks)
- ✅ Priority 1: Basic vague request handling
- ✅ Priority 5: User-friendly error messages

### Phase 2: Core Improvements (2-3 weeks)
- ✅ Priority 2: Clarifying questions for common tasks
- ✅ Priority 4: Basic prompt guidance

### Phase 3: Advanced Features (3-4 weeks)
- ✅ Priority 3: Progressive disclosure
- ✅ Memory integration for personalized suggestions

### Phase 4: Polish (1 week)
- ✅ Testing with real users
- ✅ Refinement based on feedback
- ✅ Documentation updates

---

## Success Metrics

### Quantitative
- **Vague request success rate**: Increase from 30% to 80%
- **Average clarifying questions**: Reduce from 5 to 2 per ambiguous request
- **User frustration** (measured by "nevermind"/"forget it"): Reduce by 70%
- **Task completion rate**: Increase from 75% to 95% for OK prompts

### Qualitative
- **User feedback**: More positive comments about ease of use
- **Support tickets**: Fewer "how do I..." questions
- **Conversation quality**: More natural, less mechanical

---

## Testing Strategy

### A/B Testing Plan
1. **Control Group**: Current behavior
2. **Test Group**: With improvements
3. **Metrics**: Success rate, user satisfaction, time to completion

### User Scenarios to Test
1. **New User** (first time using agent)
   - Says: "help"
   - Measures: Quality of guidance provided

2. **Casual User** (uses occasionally)
   - Says: "log my hours"
   - Measures: Clarifying questions asked

3. **Expert User** (uses frequently)
   - Says: "Create timesheet with columns..."
   - Measures: No unnecessary questions

4. **Frustrated User** (had bad experience)
   - Says: "can you just do it"
   - Measures: De-escalation success

---

## Dependencies

### Required Systems
- ✅ Memory system (already exists)
- ✅ Instincts system (already exists)
- ✅ Conversation state management (already exists)
- ✅ Tool routing (already exists)

### New Components Needed
- ❌ Intent confidence detection
- ❌ Progressive disclosure engine
- ❌ Prompt quality detector
- ❌ Error message formatter

---

## Open Questions

1. **How aggressive should we be with education?**
   - Option A: Teach at every opportunity (might annoy experts)
   - Option B: Teach only when confused (might miss learning moments)
   - **Recommendation**: Option B + user preference setting

2. **Should we remember user's prompt preferences?**
   - Store in memory: "User prefers brief confirmations"
   - Adapt behavior based on patterns
   - **Recommendation**: Yes, use instincts system

3. **How to handle multi-part vague requests?**
   - "log hours AND search stuff AND remind me"
   - Break down? Ask for each part?
   - **Recommendation**: Break down and handle sequentially

---

## Related Documents

- [onboarding_plan.md](./onboarding_plan.md) - New user onboarding
- [memory_time_tiers_plan.md](./memory_time_tiers_plan.md) - Memory system design
- [instinct_and_memory_evolution.md](./instinct_and_memory_evolution.md) - Learning system
- [CONFIG_OPTIMIZATION_PLAN.md](./CONFIG_OPTIMIZATION_PLAN.md) - Configuration improvements

---

**Next Steps:**
1. Review and approve this plan
2. Create detailed technical specs for each Priority
3. Begin Phase 1 implementation
4. Set up success metrics tracking
5. Schedule regular review sessions
