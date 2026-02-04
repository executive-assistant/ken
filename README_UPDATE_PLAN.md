# README.md Updates - Missing Features Documentation

**Date**: 2026-02-04
**Purpose**: Document major features missing from README.md

---

## Summary

The README.md is **missing documentation for several MAJOR features** that are fully implemented and tested:

### Critical Missing Sections

1. **Unified Context System (4 Pillars)** - THE CORE ARCHITECTURE
   - Current: Memory and Instincts mentioned separately
   - Missing: The 4-pillar concept, Journal, Goals, and how they work together

2. **Journal System** - COMPLETELY UNDOCUMENTED
   - 17/17 tests passing
   - Time-series activity tracking with automatic rollups
   - Integration with goals and instincts

3. **Goals System** - COMPLETELY UNDOCUMENTED
   - 17/17 tests passing
   - Progress tracking, change detection, version history
   - 5 change detection mechanisms

4. **Onboarding System** - COMPLETELY UNDOCUMENTED
   - Recently fixed and production-ready
   - Automatic new user detection
   - Structured profile creation

5. **Browser Automation (Playwright)** - UNDERDOCUMENTED
   - Only mentioned as web search fallback
   - Should be prominent tool capability

---

## Proposed Additions to README.md

### INSERT AFTER LINE 39 (after "Intelligent Tool Selection")

```markdown
## Unified Context System: How Executive Assistant Remembers Everything

Executive Assistant uses a **4-pillar unified context system** to build persistent understanding across conversations. Each pillar serves a distinct purpose, working together to create comprehensive memory.

### The 4 Pillars

**1. Memory (Semantic) - "Who you are"**
- **What it stores**: Decisions, context, knowledge, preferences
- **How it works**: Meaning-based semantic search with automatic retrieval
- **Retrieval**: Surfaces based on conversation context automatically
- **Use cases**: Meeting notes, project decisions, API keys, user preferences
- **Scope**: Thread-isolated (private) or organization-wide (shared)

**2. Journal (Episodic) - "What you did"**
- **What it stores**: Time-series activity log with automatic hierarchical rollups
- **How it works**: Tracks every action with timestamps, rolls up hourly → weekly → monthly → yearly
- **Retention**: Configurable (default: 7 years for yearly rollups)
- **Search**: FTS5 keyword search combined with time-range filtering
- **Use cases**: Activity history, work patterns, progress tracking, "what did I work on last Tuesday?"

**3. Instincts (Procedural) - "How you behave"**
- **What it stores**: Learned behavioral patterns and personality profiles
- **How it works**: Detects patterns from corrections, repetitions, and preferences
- **Evolution**: Patterns can cluster into reusable skills
- **Application**: Probabilistic based on confidence scoring
- **Use cases**: Communication style (concise vs detailed), format preferences, response patterns

**4. Goals (Intentions) - "Why/Where"**
- **What it stores**: Objectives with progress tracking and version history
- **How it works**: Change detection (5 mechanisms), progress history, audit trail
- **Monitoring**: Detects stagnation, stalled progress, approaching deadlines
- **Integration**: Informed by journal activities and memory facts
- **Use cases**: Project goals, personal objectives, OKRs, deadline tracking

### How the Pillars Work Together

```
User: "I want to launch the sales dashboard by end of month"
         ↓
    [Memory] Stores: "User's priority: sales dashboard, deadline: EOM"
         ↓
    [Goals] Creates: Goal "Launch sales dashboard" with target_date
         ↓
    [Journal] Tracks: "Created dashboard schema", "Built charts", "Deployed to staging"
         ↓
    [Goals] Updates: Progress 0% → 30% → 75% → 100%
         ↓
    [Instincts] Learns: "User prefers visual progress updates"
```

**Unified Context Benefits:**
- **No repetition**: Never repeat your preferences or context
- **Progress continuity**: Goals track across sessions via journal
- **Adaptive behavior**: Instincts personalize interactions automatically
- **Historical intelligence**: Find past work by semantic meaning OR time OR keyword
```

---

### REPLACE LINES 41-60 (Update "Adaptive Behavior with Instincts")

```markdown
### Adaptive Behavior with Instincts

Executive Assistant learns your communication style and preferences automatically:

- **Pattern Detection**: Automatically learns from corrections, repetitions, and preferences
- **Profile Presets**: Quick personality configuration (Concise Professional, Detailed Explainer, Friendly Assistant, Technical Expert)
- **Confidence Scoring**: Behaviors are applied probabilistically based on confidence
- **Evolution to Skills**: Learned patterns can cluster into reusable skills
- **Part of 4-Pillar System**: Instincts store "how you behave" within the unified context system

**Example:**
```
You: Be concise
[Assistant learns: user prefers brief responses]

You: Use bullet points
[Assistant learns: user prefers list format]

You: Actually, use JSON for data
[Assistant adjusts: reinforces format preference]

→ Pattern evolves into: "Use concise, bulleted, or JSON format based on content type"
```

**Profile Presets:**
```
You: list_profiles
Assistant: Available profiles:
  • Concise Professional - Brief, direct, business-focused
  • Detailed Explainer - Comprehensive, educational, thorough
  • Friendly Assistant - Warm, conversational, approachable
  • Technical Expert - Precise, code-focused, architectural

You: apply_profile "Concise Professional"
[Assistant applies personality preset and adapts responses]
```

> **Inspired by** [Everything with Claude Code](https://github.com/affaan-m/everything-claude-code)'s continuous learning system, instincts provide adaptive behavior that evolves with your usage patterns.
```

---

### INSERT AFTER LINE 102 (After "Persistent Memory System" section)

```markdown
## Onboarding

Executive Assistant automatically detects new users and guides them through profile creation:

**Automatic Detection:**
- Triggers on first interaction (empty user data folder)
- Detects vague requests ("hi", "help", "what can you do")
- Checks for existing data (TDB, VDB, files) before showing onboarding

**Guided Flow:**
```
[New user detected]
Assistant: Welcome! I'd like to learn about you to serve you better.

1. What's your name?
2. What's your role? (Developer, Manager, Analyst, etc.)
3. What are your main goals? (Track work, analyze data, automate tasks)
4. Any preferences? (concise responses, detailed explanations)

[Profile created with 4 structured memories: name, role, responsibilities, communication_style]
[Onboarding marked complete - won't trigger again]
```

**Vague Request Handling:**
```
You: "hi"
Assistant: [Detects vague + new user]
        Hi! 👋 I'm your Executive Assistant.

        I can help you:
        • Track work and timesheets
        • Analyze data with SQL/Python
        • Store and retrieve knowledge
        • Set reminders and manage goals

        What would you like help with?
```

**Structured Profile Creation:**
- Uses `create_user_profile()` tool (not fragmented memories)
- Creates 4 normalized memories with proper keys
- Prevents onboarding re-trigger with marker file
- Stores completion marker in memory

**Onboarding Tools:**
```bash
create_user_profile(
    name="Ken",
    role="CIO at Gong Cha Australia",
    responsibilities="IT, escalation, franchise relations, legal, HR",
    communication_preference="professional"
)
mark_onboarding_complete()
```
```

---

### ADD TO "Slash Commands & Tools" SECTION

Update the table to add:

```markdown
| `/journal` | Journal commands: add entry, search, list by time range | `/journal add "Worked on dashboard"`, `/journal search "sales"`, `/journal list --days 7` |
| `/goals` | Goals commands: create, update progress, list, detect issues | `/goals create "Launch dashboard"`, `/goals progress "Launch dashboard" 50`, `/goals list --status planned` |
| `/onboarding` | Onboarding: start, complete, check status | `/onboarding start`, `/onboarding complete`, `/onboarding status` |
```

---

### ADD NEW SECTION IN "Tool Capabilities"

Add after line 736 (after Vector Database section):

```markdown
### Journal System - Activity Tracking & Time-Series Memory
**For tracking what you did and when you did it**

- **Automatic logging**: Every tool call and action logged with timestamp
- **Hierarchical rollups**: Raw entries → Hourly → Weekly → Monthly → Yearly summaries
- **Keyword search**: FTS5 full-text search through all activities
- **Time-range queries**: Find what you worked on last Tuesday, or last month
- **Configurable retention**: Keep hourly for 30 days, weekly for 1 year, yearly for 7 years (default)
- **Semantic search**: Find activities by meaning, not just keywords
- **Integration**: Feeds goals progress, informs instinct patterns

**Use cases:**
- Activity tracking and timesheet generation
- Progress tracking for goals and projects
- Pattern detection (e.g., "User works on sales every Monday")
- Historical queries ("What did I work on last week?")
- Work analysis and productivity insights

**Journal Commands:**
```bash
# Add journal entry
/add_journal_entry "Created sales dashboard schema"

# Search by keyword
/search_journal "dashboard"

# Search by time range
/list_journal --start "2024-01-01" --end "2024-01-31"

# Get rollup hierarchy
/get_journal_rollup "2024-01"  # Monthly rollup with weekly breakdowns
```

**Data Retention (configurable in docker/config.yaml):**
- Raw entries: 30 days
- Hourly rollups: 30 days
- Weekly rollups: 52 weeks (1 year)
- Monthly rollups: 84 months (7 years)
- Yearly rollups: 7 years

### Goals System - Objective Tracking & Progress Management
**For setting goals, tracking progress, and detecting what needs attention**

- **Goal creation**: Set objectives with target dates, priorities, and importance scores
- **Progress tracking**: Manual updates or automatic from journal activities
- **Change detection (5 mechanisms)**:
  1. Explicit modifications (user edits goal)
  2. Journal stagnation (no activity for 2+ weeks)
  3. Progress stall (no progress updates for 1+ week)
  4. Approaching deadlines (low progress within 5 days of deadline)
  5. Goal completion (100% progress achieved)
- **Version history**: Full audit trail with snapshots and change reasons
- **Restore capability**: Revert to any previous version
- **Categories**: Short-term (< 1 month), Medium-term (1-6 months), Long-term (> 6 months)
- **Priority matrix**: Eisenhower matrix (priority × importance)

**Use cases:**
- Project goals and OKRs
- Personal objectives and habit tracking
- Deadline management with proactive alerts
- Progress visualization and reporting
- Goal dependency management (sub-goals, related projects)

**Goals Commands:**
```bash
# Create goal
/create_goal "Launch sales dashboard" --category "medium_term" --target_date "2024-02-01" --priority 8 --importance 9

# Update progress
/update_goal_progress "Launch sales dashboard" --progress 35 --notes "Completed backend API"

# List goals by status
/list_goals --status "planned"  # Active goals
/list_goals --status "completed"  # Completed goals

# Detect issues
/detect_stagnant_goals --weeks 2  # No activity for 2+ weeks
/detect_stalled_progress --weeks 1  # No progress for 1+ week
/detect_urgent_goals --days 5 --progress_threshold 30  # Deadline soon, low progress

# Version history
/get_goal_versions "Launch sales dashboard"
/restore_goal_version "Launch sales dashboard" --version 1

# Progress history
/get_goal_progress "Launch sales dashboard"
```
```

---

### REPLACE/PROMOTE Browser Automation Section

Currently only mentioned in passing under web search. Should be a full section like Python, OCR, etc:

```markdown
### Browser Automation (Playwright)
**For JavaScript-heavy pages that need real browser rendering**

- **Full browser rendering**: Handles React, Vue, Angular, and any JS framework
- **Interactive elements**: Waits for dynamic content to load
- **Screenshot capture**: Export page as image
- **PDF export**: Save page as PDF document
- **Custom selectors**: Wait for specific elements before extracting
- **Fallback for web search**: Automatically used when web scraping fails
- **Use cases**:
  - Single-page applications (SPAs)
  - Infinite scroll pages
  - Authentication-required pages
  - Dynamic dashboards and charts
  - Pages with heavy client-side rendering

**Playwright Commands:**
```bash
# Scrape JS-rendered page
/playwright_scrape "https://example.com/dashboard"

# Wait for specific element
/playwright_scrape "https://example.com" --wait_for_selector ".data-loaded"

# Set timeout and character limit
/playwright_scrape "https://example.com" --timeout_ms 60000 --max_chars 25000
```

**Example:**
```
You: Scrape the sales dashboard at https://internal.example.com/dashboard
Assistant: [Detects JS-heavy page]
     Using Playwright for full browser rendering...

     ✅ Scraped successfully:
        • Total Revenue: $1,234,567
        • Active Users: 8,432
        • Top Product: Widget Pro ($45,678)

     📊 Saved to: dashboard_sales_2024-01-15.json
```

**Installation (if needed):**
```bash
uv add playwright
playwright install  # Download browser binaries
```
```

---

## File Structure for Updates

```
README.md
├── [What Executive Assistant Can Do For You] - EXISTING
├── [Unified Context System] - NEW SECTION HERE ⭐
├── [How Executive Assistant Thinks] - EXISTING
├── [Real-Time Progress Updates] - EXISTING
├── [Multi-Channel Access] - EXISTING
├── [Storage That Respects Your Privacy] - EXISTING
├── [Persistent Memory System] - EXISTING
├── [Onboarding] - NEW SECTION HERE ⭐
├── [Quick Start] - EXISTING
├── [What Makes Executive Assistant Different] - EXISTING
├── [Example Workflows] - EXISTING
├── [Configuration] - EXISTING
├── [Slash Commands & Tools] - UPDATE TABLE ⭐
├── [HTTP API] - EXISTING
├── [Tool Capabilities] - ADD NEW SECTIONS ⭐
│   ├── [Analytics Database] - EXISTING
│   ├── [Transactional Database] - EXISTING
│   ├── [Vector Database] - EXISTING
│   ├── [Python Execution] - EXISTING
│   ├── [Journal System] - NEW HERE ⭐
│   ├── [Goals System] - NEW HERE ⭐
│   ├── [Browser Automation] - PROMOTE FROM FOOTNOTE ⭐
│   └── [MCP Integration] - EXISTING
├── [Admin Configuration] - EXISTING
├── [Token Usage & Cost Monitoring] - EXISTING
├── [Architecture Overview] - UPDATE TO MENTION 4 PILLARS ⭐
├── [Testing] - EXISTING
├── [Project Structure] - EXISTING
├── [License] - EXISTING
├── [Contributing] - EXISTING
└── [Tech Stack] - EXISTING
```

---

## Priority Order

### High Priority (Must Have) ⭐⭐⭐
1. **Unified Context System section** - Core differentiator, completely missing
2. **Journal System documentation** - 17/17 tests passing, no docs
3. **Goals System documentation** - 17/17 tests passing, no docs
4. **Onboarding section** - Recently fixed, production-ready

### Medium Priority (Should Have) ⭐⭐
5. **Browser Automation** - Enabled but underdocumented
6. **Update slash commands table** - Add /journal, /goals, /onboarding
7. **Enhanced Instincts docs** - Mention 4-pillar integration, profile presets

### Low Priority (Nice to Have) ⭐
8. **Update Architecture Overview** - Mention 4-pillar system in diagram
9. **Update Example Workflows** - Show goals + journal integration

---

## Implementation Notes

### Tone and Style
- User-facing benefits focus (not implementation details)
- Concise but comprehensive
- Code examples for all commands
- Clear use cases for each feature
- Consistent formatting with existing README

### Key Points to Emphasize
- Unified Context System is the **core differentiator**
- All 4 pillars work together (not separate features)
- Journal + Goals integration for progress tracking
- Instincts evolve from patterns into skills
- Onboarding creates structured profiles (not fragmented memories)

### Avoid
- Implementation details (SQLite, file paths)
- Test coverage numbers (unless showing production-ready)
- Technical jargon without explanation
- Over-promising (disabled features like agents/flows)

---

## Next Steps

1. Review this document with user
2. Create actual README.md updates
3. Commit changes with comprehensive message
4. Update related documentation (features/*.md files if needed)

**Total estimated additions**: ~400-500 lines of documentation
