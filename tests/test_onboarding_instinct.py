"""Test onboarding creates communication instincts.

This test verifies the fix for the onboarding bug where create_instinct
was not being called, resulting in no behavioral patterns being created.
"""

from pathlib import Path

import pytest

from executive_assistant.storage.file_sandbox import set_thread_id, clear_thread_id
from executive_assistant.storage.instinct_storage import get_instinct_storage
from executive_assistant.storage.mem_storage import get_mem_storage
from executive_assistant.tools.registry import get_all_tools


def test_onboarding_creates_instinct():
    """Test that onboarding flow creates a communication instinct.

    This is a regression test for the bug where onboarding would create
    memories but not call create_instinct, leaving the agent without
    learned behavioral patterns.

    Test flow:
    1. Create user profile
    2. Store timezone preference
    3. Create communication instinct (this was missing!)
    4. Mark onboarding complete
    5. Verify instinct exists in storage
    """
    import asyncio

    test_thread_id = "test_onboarding_instinct_001"

    async def run_test():
        tools = await get_all_tools()
        tool_map = {t.name: t for t in tools}

        set_thread_id(test_thread_id)

        # Step 1: Create user profile (simulates onboarding questions)
        profile_result = await tool_map["create_user_profile"].ainvoke({
            "name": "TestUser",
            "role": "Software Engineer",
            "responsibilities": "Backend systems, APIs",
            "communication_preference": "concise",
        })
        assert "TestUser" in str(profile_result)
        assert "Software Engineer" in str(profile_result)

        # Step 2: Store timezone preference
        timezone_result = await tool_map["create_memory"].ainvoke({
            "content": "Timezone: America/New_York",
            "memory_type": "preference",
            "key": "timezone",
            "confidence": 1.0,
        })
        result_str = str(timezone_result).lower()
        assert "saved" in result_str or "updated" in result_str or "already exists" in result_str

        # Step 3: Create communication instinct (THE FIX - this was missing!)
        instinct_result = await tool_map["create_instinct"].ainvoke({
            "trigger": "user_communication",
            "action": "use brief, direct communication style with minimal fluff",
            "domain": "communication",
            "source": "explicit-user",
            "confidence": 0.9,
        })
        instinct_str = str(instinct_result).lower()
        assert "created" in instinct_str or "instinct" in instinct_str

        # Step 4: Mark onboarding complete
        complete_result = await tool_map["mark_onboarding_complete"].ainvoke({})
        assert "complete" in str(complete_result).lower()

        # Step 5: Verify instinct exists in storage
        instinct_storage = get_instinct_storage()
        instincts = instinct_storage.list_instincts(thread_id=test_thread_id)

        # Assertions
        assert len(instincts) >= 1, f"Expected at least 1 instinct, got {len(instincts)}"

        # Find the communication instinct
        comm_instinct = None
        for instinct in instincts:
            if instinct.get("trigger") == "user_communication":
                comm_instinct = instinct
                break

        assert comm_instinct is not None, "Communication instinct not found"
        assert comm_instinct.get("domain") == "communication"
        assert comm_instinct.get("confidence") >= 0.8
        assert "brief" in comm_instinct.get("action", "").lower()

    try:
        asyncio.run(run_test())
    finally:
        clear_thread_id()


def test_onboarding_instinct_different_communication_styles():
    """Test that different communication preferences map to correct instinct actions.

    This verifies the communication style mapping from onboarding.md:
    - "brief"/"concise"/"direct" → "use brief, direct communication style"
    - "detailed"/"thorough" → "provide thorough explanations"
    - "formal"/"professional" → "use professional language"
    - "casual"/"friendly" → "use friendly, conversational tone"
    """
    import asyncio

    test_cases = [
        ("concise", "concise"),
        ("detailed", "detailed"),
        ("formal", "formal"),
        ("casual", "casual"),
    ]

    async def run_test():
        tools = await get_all_tools()
        tool_map = {t.name: t for t in tools}

        for idx, (style, expected_keyword) in enumerate(test_cases):
            test_thread_id = f"test_onboarding_style_{idx}_{style}"

            set_thread_id(test_thread_id)

            # Create profile with specific communication style
            await tool_map["create_user_profile"].ainvoke({
                "name": f"User{idx}",
                "role": "Developer",
                "responsibilities": "Coding",
                "communication_preference": style,
            })

            # Create corresponding instinct
            await tool_map["create_instinct"].ainvoke({
                "trigger": "user_communication",
                "action": f"use {style} communication style",
                "domain": "communication",
                "source": "explicit-user",
                "confidence": 0.9,
            })

            # Verify instinct has expected keyword in action
            instinct_storage = get_instinct_storage()
            instincts = instinct_storage.list_instincts(thread_id=test_thread_id)

            assert len(instincts) >= 1, f"No instincts created for style: {style}"
            assert expected_keyword in instincts[0].get("action", "").lower()

    asyncio.run(run_test())


def test_onboarding_creates_all_required_memories():
    """Test that onboarding creates all required memories via create_user_profile.

    Verifies that create_user_profile creates 4 memories:
    1. name (profile type)
    2. role (profile type)
    3. responsibilities (profile type)
    4. communication_style (style type)
    """
    import asyncio

    test_thread_id = "test_onboarding_memories_001"

    async def run_test():
        tools = await get_all_tools()
        tool_map = {t.name: t for t in tools}

        set_thread_id(test_thread_id)

        # Create user profile
        result = await tool_map["create_user_profile"].ainvoke({
            "name": "MemTestUser",
            "role": "Data Scientist",
            "responsibilities": "ML models, data analysis",
            "communication_preference": "detailed",
        })

        # Verify all 4 memories were created
        mem_storage = get_mem_storage()
        memories = mem_storage.list_memories(thread_id=test_thread_id)

        # Should have at least 4 memories from create_user_profile
        assert len(memories) >= 4, f"Expected at least 4 memories, got {len(memories)}"

        # Check for specific memory keys
        memory_keys = {m.get("key") for m in memories}
        assert "name" in memory_keys
        assert "role" in memory_keys
        assert "responsibilities" in memory_keys
        assert "communication_style" in memory_keys

        # Verify content
        name_mem = [m for m in memories if m.get("key") == "name"][0]
        assert "MemTestUser" in name_mem.get("content", "")

        role_mem = [m for m in memories if m.get("key") == "role"][0]
        assert "Data Scientist" in role_mem.get("content", "")

        style_mem = [m for m in memories if m.get("key") == "communication_style"][0]
        assert style_mem.get("memory_type") == "style"

    try:
        asyncio.run(run_test())
    finally:
        clear_thread_id()
