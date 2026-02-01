# Personalization Analysis: How Executive Assistant Tracks User Characteristics

**Date:** 2025-02-02
**Status:** Comprehensive Analysis
**Related:** [ux_improvements_plan.md](./ux_improvements_plan.md), [onboarding_plan.md](./onboarding_plan.md)

---

## Executive Summary

**YES** - Executive Assistant has sophisticated systems for tracking user persona, AI literacy, and background. However, it's **NOT currently feeding this information back to the LLM to optimize UX**.

The systems exist but are underutilized. There's a significant opportunity to improve UX by connecting the existing memory/instincts systems to the agent's response generation.

---

## Current Personalization Systems

### 1. **Memory System** ✅ (Fully Implemented)

**Location:** `src/executive_assistant/storage/mem_storage.py`

**Capabilities:**
- ✅ Stores 6 types of memories: `profile`, `fact`, `preference`, `constraint`, `style`, `context`
- ✅ Temporal versioning (tracks changes over time)
- ✅ Confidence scoring (0.0 to 1.0)
- ✅ Full-text search with FTS5 indexing
- ✅ Point-in-time queries (what did user know at time X?)

**Memory Types:**
```python
_ALLOWED_TYPES = {
    "profile",      # User characteristics (role, expertise, background)
    "fact",         # Objective facts (location, timezone, team)
    "preference",   # User preferences (concise vs detailed, formal vs casual)
    "constraint",   # Limitations (can't access certain systems, time constraints)
    "style",        # Communication style (brief, technical, friendly)
    "context",      # Situational context (working on X project, in Y meeting)
}
```

**Key Features:**
- SQLite database per thread: `data/users/{thread_id}/mem.db`
- Automatic deduplication by content or key
- Configurable min confidence: `settings.MEM_CONFIDENCE_MIN`
- Max 5 memories injected per message

### 2. **Instincts System** ✅ (Fully Implemented)

**Location:** `src/executive_assistant/storage/instinct_storage.py`

**Capabilities:**
- ✅ Behavioral pattern learning (trigger → action)
- ✅ Confidence scoring (0.0 to 1.0)
- ✅ Multiple learning sources
- ✅ Domain categorization
- ✅ Probabilistic application based on confidence

**Instinct Domains:**
```python
_ALLOWED_DOMAINS = {
    "communication",   # How user prefers to communicate
    "format",         # Response format preferences
    "workflow",       # How user likes to work
    "tool_selection", # Which tools to prefer
    "verification",   # How much to double-check
    "timing",         # When to do things
}
```

**Learning Sources:**
```python
_ALLOWED_SOURCES = {
    "session-observation",    # Learned from current conversation
    "explicit-user",          # User directly stated
    "repetition-confirmed",   # User repeated preference 3+ times
    "correction-detected",     # User corrected agent
    "preference-expressed",    # User expressed preference
    "profile-preset",         # Chosen persona preset
    "custom-profile",         # User-defined profile
    "import",                 # Imported from elsewhere
}
```

### 3. **Memory Auto-Extraction** ⚠️ (Configured but Not Active)

**Configuration:**
```yaml
# docker/config.yaml
memory:
  auto_extract: true        # ← ENABLED in config
  confidence_min: 0.6       # Save only if confident
  max_per_turn: 3           # Max 3 memories per message
  extract_model: fast       # Use fast model
  extract_provider: null     # Use default provider
  extract_temperature: 0.0   # Deterministic extraction
```

**Reality Check:**
```python
# src/executive_assistant/config/settings.py:266
MEM_AUTO_EXTRACT: bool = _yaml_field("MEMORY_AUTO_EXTRACT", False)
#                                                            ^^^^^
#                                                            DISABLED!
```

**Status:** ⚠️ **Configured in YAML but default is False in code.**

**Question:** Is there an extraction middleware that uses this setting?
**Answer:** **Not found in codebase** - no implementation discovered.

---

## How Personalization Flows Currently

### Step 1: Memory Injection ✅ (Working)

**Location:** `src/executive_assistant/channels/base.py:501-520`

```python
def _inject_memories(self, content: str, memories: list[dict]) -> str:
    """
    Inject relevant memories into the message content.
    """
    if not memories:
        return content

    memory_lines = []
    for m in memories[:5]:  # Max 5 memories
        memory_lines.append(f"- {m['content']}")

    memory_context = "\n".join(memory_lines)
    return f"[User Memory]\n{memory_context}\n\n[User Message]\n{content}"
```

**Usage in Channels:**
```python
# Telegram channel (telegram.py:818-819)
memories = self._get_relevant_memories(thread_id, msg.content)
enhanced_content = self._inject_memories(msg.content, memories)

# HTTP channel (http.py:338-339)
memories = self._get_relevant_memories(thread_id, message.content)
enhanced_content = self._inject_memories(message.content, memories)
```

**What Gets Injected:**
```
[User Memory]
- User prefers Python over JavaScript
- User lives in New York
- User likes concise responses

[User Message]
Create a database table
```

### Step 2: Memory Retrieval ✅ (Working)

**Location:** `src/executive_assistant/channels/base.py:475-499`

```python
def _get_relevant_memories(self, thread_id: str, query: str, limit: int = 5):
    """Get relevant memories based on search query."""
    storage = get_mem_storage()
    memories = storage.search_memories(
        query=query,
        limit=limit,
        min_confidence=settings.MEM_CONFIDENCE_MIN,  # 0.6 by default
    )
    return memories
```

**Search Method:**
- Full-text search using SQLite FTS5
- Searches memory content
- Filters by minimum confidence
- Returns up to 5 memories

### Step 3: Instincts Application ❓ (Unclear)

**Status:** Instincts system exists but **no code found** that applies instincts during conversation.

**What's Missing:**
- No middleware that checks active instincts before responding
- No code that adjusts responses based on learned patterns
- No integration between instincts and LLM calls

**What Exists:**
- Storage system for instincts
- Tools to create/list/adjust instincts
- Confidence tracking
- But no actual application logic found

---

## What's NOT Being Tracked (Critical Gaps)

### 1. **AI Literacy Level** ❌

**Not Tracked:**
- How good is user at prompting?
- Does user understand LLM capabilities?
- How often does user need clarification?
- Does user give good or bad prompts?

**Impact:**
- Agent can't adapt communication style to user's skill level
- Can't provide appropriate level of guidance
- Treats expert users and beginners the same

### 2. **Prompt Quality Patterns** ❌

**Not Tracked:**
- Average prompt length from this user
- How specific user typically is
- Whether user provides context or needs it asked
- Common mistakes user makes

**Impact:**
- Can't predict when user needs help
- Can't proactively suggest improvements
- Doesn't learn from user's past mistakes

### 3. **Frustration Indicators** ❌

**Not Tracked:**
- User saying "nevermind", "forget it"
- User asking "what?" or repeating requests
- User correcting agent multiple times
- Short, terse responses (potential frustration)

**Impact:**
- Can't detect when user is struggling
- Can't adjust approach when frustrated
- Can't de-escalate difficult situations

### 4. **Learning Progress** ❌

**Not Tracked:**
- Is user getting better at prompting over time?
- Has user learned from guidance?
- What patterns has user adopted?

**Impact:**
- Can't measure teaching effectiveness
- Can't celebrate improvements
- Can't retire unnecessary guidance

---

## What IS Being Tracked (But Underutilized)

### 1. **Communication Style** ✅ Tracked, ❌ Not Used

**Memory Type:** `style`

**Examples of What Could Be Stored:**
```python
create_memory(
    "User prefers brief responses without elaboration",
    memory_type="style",
    key="communication_brevity"
)

create_memory(
    "User likes technical details and code examples",
    memory_type="preference",
    key="detail_preference"
)

create_memory(
    "User wants step-by-step explanations",
    memory_type="style",
    key="explanation_style"
)
```

**Problem:** These get stored but not used to customize responses.

### 2. **Expertise Level** ✅ Tracked, ❌ Not Used

**Memory Type:** `profile`

**Examples:**
```python
create_memory(
    "User is senior software engineer",
    memory_type="profile",
    key="role"
)

create_memory(
    "User knows Python and JavaScript",
    memory_type="profile",
    key="skills"
)

create_memory(
    "User is beginner at data analysis",
    memory_type="profile",
    key="expertise_level"
)
```

**Problem:** Agent doesn't adjust technical depth or explanations based on this.

### 3. **Workflow Preferences** ✅ Tracked, ❌ Not Used

**Instinct Domain:** `workflow`

**Examples:**
```python
create_instinct(
    trigger="user creates database table",
    action="ask if they want to add sample data next",
    domain="workflow",
    source="session-observation",
    confidence=0.7
)

create_instinct(
    trigger="user searches web",
    action="offer to save results to knowledge base",
    domain="workflow",
    source="session-observation",
    confidence=0.8
)
```

**Problem:** Instincts exist but no application layer found.

---

## The Missing Piece: Personalization Middleware

### Current Flow (What Happens)

```
User Message
    ↓
Search Memories (FTS query)
    ↓
Inject Top 5 Memories
    ↓
[User Memory]
- Memory 1
- Memory 2
- Memory 3
- Memory 4
- Memory 5

[User Message]
Original message

    ↓
Send to LLM
    ↓
LLM Response (generic)
```

### Proposed Flow (What SHOULD Happen)

```
User Message
    ↓
Analyze Message Quality (NEW)
    ↓ Detect: vague? specific? good?
    ↓ Classify: AI literacy level
    ↓ Check: frustration indicators?

Search Memories + Instincts
    ↓ FTS + behavioral patterns
    ↓
Build Personalization Context (NEW)
    ↓ Communication style
    ↓ Expertise level
    ↓ Prompt quality history
    ↓ Active instincts
    ↓ Frustration level

Inject Personalized Context (NEW)
    ↓
[User Profile]
- Expert: Senior engineer
- AI Literacy: High
- Preferred Style: Brief, technical
- Frustrated: False

[Relevant Memories]
- Prefers Python over JavaScript
- Currently working on Project Alpha

[Active Instincts]
- After creating table: offer sample data
- When searching: offer to save to KB

[Guidance for This Response]
- Use technical language
- Skip basic explanations
- Be concise
- Provide code examples

[User Message]
Original message (adjusted if needed)

    ↓
Send to LLM
    ↓
Personalized Response
```

---

## Implementation Plan

### Phase 1: Track AI Literacy & Prompt Quality (NEW)

**New Memory Type Addition:**

```python
# Add to _ALLOWED_TYPES in mem_storage.py
_ALLOWED_TYPES = {
    # ... existing types ...
    "prompt_pattern",   # NEW: User's prompting habits
}
```

**Automatic Tracking:**

```python
# New middleware: src/executive_assistant/middleware/personalization_tracker.py

class PersonalizationTracker:
    """Track user characteristics for UX optimization."""

    def track_prompt_quality(self, message: str, thread_id: str):
        """Analyze and track prompt quality metrics."""

        metrics = {
            "length": len(message),
            "has_context": self._has_context(message),
            "specificity": self._measure_specificity(message),
            "clarity": self._measure_clarity(message),
            "technical": self._is_technical(message),
        }

        # Calculate overall quality score
        quality_score = self._calculate_quality_score(metrics)

        # Store as memory
        create_memory(
            content=f"User's last prompt quality score: {quality_score:.2f}/1.0",
            memory_type="prompt_pattern",
            key="last_prompt_quality",
            confidence=0.9
        )

        return metrics, quality_score

    def track_ai_literacy(self, conversation_history: list, thread_id: str):
        """Track user's AI literacy over time."""

        indicators = {
            "uses_tool_names": self._counts_tool_name_usage(conversation_history),
            "provides_context": self._counts_context_provision(conversation_history),
            "clarifies_requests": self._counts_clarifications(conversation_history),
            "learns_from_corrections": self._counts_learning_patterns(conversation_history),
        }

        # Calculate literacy level
        literacy_level = self._calculate_literacy_level(indicators)

        # Update profile
        create_memory(
            content=f"User's AI literacy level: {literacy_level}",  # beginner/intermediate/expert
            memory_type="profile",
            key="ai_literacy",
            confidence=0.8
        )

        return literacy_level
```

### Phase 2: Detect Frustration (NEW)

```python
class FrustrationDetector:
    """Detect user frustration in real-time."""

    FRUSTRATION_PATTERNS = [
        r"\bnevermind\b",
        r"\bforget it\b",
        r"\bwhatever\b",
        r"\bjust do it\b",
        r"\btoo complicated\b",
        r"^(ok|okay|fine)[!.]*$",  # Terse responses
        r"\?\s*$",  # Just question marks
        r"(.*)\1{2,}",  # Repeated words (stuttering frustration)
    ]

    def detect_frustration(self, message: str, thread_id: str) -> bool:
        """Check if user is frustrated."""

        for pattern in self.FRUSTRATION_PATTERNS:
            if re.search(pattern, message.lower()):
                # Log frustration
                create_memory(
                    content=f"User showed frustration: '{message}'",
                    memory_type="context",
                    key="frustration_detected",
                    confidence=0.7
                )

                # Check if this is pattern
                recent_frustrations = self._count_recent_frustrations(thread_id)
                if recent_frustrations >= 3:
                    return "high"

                return "low"

        return False
```

### Phase 3: Apply Instincts to Responses (NEW)

```python
# New middleware: src/executive_assistant/middleware/instinct_application.py

class InstinctApplication:
    """Apply learned instincts to customize responses."""

    def get_active_instincts(self, thread_id: str, context: dict) -> list:
        """Get applicable instincts for current situation."""

        storage = get_instinct_storage()
        all_instincts = storage.list_instincts(
            thread_id=thread_id,
            status="active",
            min_confidence=0.6
        )

        # Filter by relevance
        active = []
        for instinct in all_instincts:
            if self._is_trigger_match(instinct, context):
                # Probabilistic application based on confidence
                if random.random() < instinct["confidence"]:
                    active.append(instinct)

        return active

    def apply_instincts_to_response(
        self,
        base_response: str,
        instincts: list,
        context: dict
    ) -> str:
        """Modify response based on active instincts."""

        modifications = []

        for instinct in instincts:
            if instinct["domain"] == "communication":
                modifications.append(self._apply_communication_instinct(
                    base_response,
                    instinct["action"]
                ))
            elif instinct["domain"] == "format":
                modifications.append(self._apply_format_instinct(
                    base_response,
                    instinct["action"]
                ))
            # ... other domains

        return self._merge_modifications(base_response, modifications)
```

### Phase 4: Build Personalization Context (NEW)

```python
# Enhance channels/base.py:_inject_memories()

def build_personalization_context(
    thread_id: str,
    user_message: str,
    conversation_history: list
) -> dict:
    """Build comprehensive personalization context."""

    # 1. Get AI literacy level
    literacy = get_user_memories(thread_id).get("ai_literacy", "unknown")

    # 2. Get communication preferences
    style = get_user_memories(thread_id).get(
        lambda m: m["memory_type"] == "style",
        {}
    )

    # 3. Get expertise level
    expertise = get_user_memories(thread_id).get(
        lambda m: m["key"] == "role" or m["key"] == "skills",
        {}
    )

    # 4. Check frustration level
    frustration = detect_frustration(user_message, thread_id)

    # 5. Get active instincts
    instincts = get_active_instincts(thread_id, {"message": user_message})

    # 6. Get prompt quality history
    prompt_quality = get_user_memories(thread_id).get(
        lambda m: m["key"] == "last_prompt_quality",
        {}
    )

    return {
        "ai_literacy": literacy,
        "communication_style": style,
        "expertise": expertise,
        "frustration_level": frustration,
        "active_instincts": instincts,
        "prompt_trend": prompt_quality,
    }


def inject_personalized_context(
    content: str,
    memories: list,
    context: dict
) -> str:
    """Inject personalized context into user message."""

    # Build personalization header
    header_parts = []

    # User Profile
    if context.get("expertise"):
        header_parts.append(f"[User Profile]\n{context['expertise']}")

    # Communication Preferences
    if context.get("communication_style"):
        header_parts.append(f"[Communication Style]\n{context['communication_style']}")

    # AI Literacy
    if context.get("ai_literacy") == "beginner":
        header_parts.append("[AI Literacy]\nBeginner - provide guidance and examples")
    elif context.get("ai_literacy") == "expert":
        header_parts.append("[AI Literacy]\nExpert - skip basics, be direct")

    # Frustration Handling
    if context.get("frustration_level") == "high":
        header_parts.append("[Current State]\nUser seems frustrated - be extra helpful and patient")

    # Active Instincts
    if context.get("active_instincts"):
        header_parts.append(f"[Active Patterns]\n{format_instincts(context['active_instincts'])}")

    # Memories
    if memories:
        memory_lines = [f"- {m['content']}" for m in memories[:5]]
        header_parts.append(f"[Relevant Memories]\n" + "\n".join(memory_lines))

    # Guidance for this response (NEW!)
    guidance = generate_response_guidance(context)
    if guidance:
        header_parts.append(f"[Response Guidance]\n{guidance}")

    header = "\n\n".join(header_parts)

    return f"{header}\n\n[User Message]\n{content}"


def generate_response_guidance(context: dict) -> str:
    """Generate specific guidance for LLM based on personalization."""

    guidance_parts = []

    # Based on AI literacy
    literacy = context.get("ai_literacy", "unknown")
    if literacy == "beginner":
        guidance_parts.append("- Be patient and educational")
        guidance_parts.append("- Provide examples of good prompts")
        guidance_parts.append("- Explain what you're doing")
    elif literacy == "expert":
        guidance_parts.append("- Be direct and concise")
        guidance_parts.append("- Skip explanations")
        guidance_parts.append("- Use technical language")

    # Based on expertise
    expertise = context.get("expertise", {})
    if "senior" in str(expertise).lower() or "lead" in str(expertise).lower():
        guidance_parts.append("- Assume deep technical knowledge")
        guidance_parts.append("- Provide code examples without extensive comments")

    # Based on frustration
    if context.get("frustration_level") == "high":
        guidance_parts.append("- Be extra helpful")
        guidance_parts.append("- Offer to break down complex tasks")
        guidance_parts.append("- Confirm understanding before proceeding")
        guidance_parts.append("- Use encouraging language")

    return "\n".join(guidance_parts) if guidance_parts else ""
```

---

## Summary & Recommendations

### ✅ **What Works Well**

1. **Memory Storage** - Excellent system with 6 types, temporal versioning, search
2. **Instincts Storage** - Good foundation for behavioral patterns
3. **Memory Injection** - Currently injects up to 5 relevant memories per message
4. **Configuration** - Auto-extraction configured but not active

### ❌ **What's Missing**

1. **AI Literacy Tracking** - Don't know if user is beginner/expert
2. **Prompt Quality Tracking** - Don't measure prompt quality over time
3. **Frustration Detection** - Can't tell when user is struggling
4. **Instinct Application** - Patterns stored but not applied
5. **Response Personalization** - Same response style for everyone

### 🎯 **Priority Recommendations**

#### Priority 1: Enable Auto-Extraction ⚠️ (Easy Win)

**Problem:** Config says `auto_extract: true` but code default is `False`

**Fix:**
```python
# src/executive_assistant/config/settings.py:266
# Change:
MEM_AUTO_EXTRACT: bool = _yaml_field("MEMORY_AUTO_EXTRACT", False)

# To:
MEM_AUTO_EXTRACT: bool = _yaml_field("MEMORY_AUTO_EXTRACT", True)
```

**Impact:** Agent will automatically learn about users without explicit commands.

#### Priority 2: Add AI Literacy Tracking 🆕 (New Feature)

**Implementation:**
- Add `prompt_pattern` memory type
- Track prompt length, specificity, clarity
- Calculate literacy level over time
- Store in memory as profile

**Impact:** Agent can adapt communication to user's skill level.

#### Priority 3: Implement Frustration Detection 🆕 (New Feature)

**Implementation:**
- Detect frustration patterns (nevermind, forget it, etc.)
- Track frustration frequency
- Adjust response style when frustrated
- De-escalate difficult situations

**Impact:** Better user experience, reduced frustration.

#### Priority 4: Apply Instincts to Responses 🆕 (Integration)

**Problem:** Instincts exist but aren't applied

**Implementation:**
- Create middleware that checks active instincts before responding
- Apply behavioral patterns based on confidence scores
- Integrate with memory system

**Impact:** Agent actually learns and adapts to user habits.

#### Priority 5: Build Response Personalization Layer 🆕 (New System)

**Implementation:**
- Create personalization context from memories + instincts + literacy + frustration
- Inject into LLM as system instructions
- Guide LLM on HOW to respond, not just WHAT to respond

**Impact:** Every response tailored to user's characteristics.

---

## Example: Before & After Personalization

### Before (Current Behavior)

```
User: "help"
Agent: (Long generic help message with all features)

User: "log 5 hours to Project X"
Agent: (Logs immediately without asking details)
     "Created timesheet entry with 5 hours for Project X"

User: "i need thing"
Agent: "I don't understand what you need"
```

### After (With Personalization)

```
[First interaction with new user]
User: "help"
Agent: """
I'd love to help! Could you be a bit more specific?

Here are some things I can do:
📊 Track work: "Log 4 hours to Project Alpha - code review"
🔍 Search web: "Find recent articles about LangChain"
⏰ Reminders: "Remind me to review PRs every weekday at 3pm"

What would you like help with?
"""
→ System tracks: AI literacy = "beginner"


[Third interaction - learning pattern]
User: "log 5 hours to Project X"
Agent: """
I'll log 5 hours to Project X.

Quick questions to help you better:
- What date is this for? (default: today)
- What work did you do?

[User Profile]
- AI Literacy: Beginner (3/10)
- Prompt Quality: Low (needs context)
"""
→ System tracks: User doesn't provide details naturally


[Tenth interaction - expert learned]
User: "log 5 hours to Project X"
Agent: """
Based on your usual pattern, I'll log:
- 5 hours to Project X
- Today's date
- Code review task

Is that correct? (You usually do code reviews for Project X)
→ System tracks: Instinct with confidence 0.85


[Frustrated user detected]
User: "whatever nevermind"
Agent: """
I sense you're frustrated - I'm sorry if I wasn't being helpful.

Let's start fresh. What would you like to accomplish?
- I can break it down into smaller steps
- Or you can tell me exactly what you need in your own words

[Current State]
- User Frustrated: YES
- Response Strategy: Extra patient, ask clarifications
"""
```

---

## Success Metrics

### Quantitative
- **Vague request success rate**: 30% → 80%
- **User frustration (measured by "nevermind")**: Reduce by 70%
- **Average turns to complete task**: Reduce by 40% for beginners
- **User satisfaction** (implicit: conversation continuation): Increase by 50%

### Qualitative
- **Expert users**: "Finally, it doesn't talk down to me!"
- **Beginner users**: "It actually teaches me how to use it better"
- **All users**: "It just gets me"

---

## Next Steps

1. **Review and approve** this analysis
2. **Implement Priority 1** (Enable auto-extraction) - 5 minutes
3. **Design Priority 2-5** (New tracking systems) - 1 week each
4. **Test with real users** across skill levels
5. **Measure impact** on UX metrics
6. **Iterate** based on feedback

---

## Conclusion

**Executive Assistant has excellent infrastructure for personalization (memory + instincts systems) but is NOT USING IT effectively.**

The systems exist but aren't connected to the LLM in a way that improves UX. By implementing the recommended changes, we can transform the agent from "one-size-fits-all" to "truly personalized assistant" that adapts to each user's skill level, preferences, and emotional state.

**Key Insight:** The data is there. The patterns can be learned. We just need to actually USE them to customize responses.
