"""Simple integration test for Phase 4 features without framework overhead."""

import time
import uuid
from pathlib import Path

from executive_assistant.storage.instinct_storage import InstinctStorage
from executive_assistant.instincts.injector import get_instinct_injector


def test_basic_performance():
    """Test basic performance without framework overhead."""
    storage = InstinctStorage()
    injector = get_instinct_injector()

    # Use unique thread ID to avoid conflicts
    thread_id = f"perf_test_{uuid.uuid4().hex[:8]}"

    try:
        # Create 10 test instincts
        print("\n=== Creating 10 test instincts ===")
        start = time.perf_counter()
        for i in range(10):
            storage.create_instinct(
                trigger=f"test trigger {i}",
                action=f"test action {i}",
                domain="communication",
                confidence=0.7,
                thread_id=thread_id,
            )
        create_time = (time.perf_counter() - start) * 1000
        print(f"✅ Created 10 instincts in {create_time:.2f}ms")

        # Test build_instincts_context
        print("\n=== Testing build_instincts_context ===")
        start = time.perf_counter()
        context = injector.build_instincts_context(
            thread_id=thread_id,
            user_message="test message",
        )
        build_time = (time.perf_counter() - start) * 1000
        print(f"✅ build_instincts_context: {build_time:.2f}ms")
        print(f"   Context length: {len(context)} chars")

        # Test list_instincts
        print("\n=== Testing list_instincts ===")
        start = time.perf_counter()
        instincts = storage.list_instincts(thread_id=thread_id)
        list_time = (time.perf_counter() - start) * 1000
        print(f"✅ list_instincts: {list_time:.2f}ms")
        print(f"   Found {len(instincts)} instincts")

        # Test find_similar_instincts
        print("\n=== Testing find_similar_instincts ===")
        start = time.perf_counter()
        similar = storage.find_similar_instincts(thread_id=thread_id)
        similar_time = (time.perf_counter() - start) * 1000
        print(f"✅ find_similar_instincts: {similar_time:.2f}ms")
        print(f"   Found {len(similar)} clusters")

        # Test export_instincts
        print("\n=== Testing export_instincts ===")
        start = time.perf_counter()
        json_data = storage.export_instincts(thread_id=thread_id)
        export_time = (time.perf_counter() - start) * 1000
        print(f"✅ export_instincts: {export_time:.2f}ms")
        print(f"   Export size: {len(json_data)} chars")

        # Test format_instincts_for_user
        print("\n=== Testing format_instincts_for_user ===")
        start = time.perf_counter()
        formatted = injector.format_instincts_for_user(thread_id=thread_id)
        format_time = (time.perf_counter() - start) * 1000
        print(f"✅ format_instincts_for_user: {format_time:.2f}ms")
        print(f"   Formatted length: {len(formatted)} chars")

        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Total operations: {create_time + build_time + list_time + similar_time + export_time + format_time:.2f}ms")
        print(f"Most expensive: max({create_time:.1f}, {build_time:.1f}, {list_time:.1f}, {similar_time:.1f}, {export_time:.1f}, {format_time:.1f}) = "
          f"{max(create_time, build_time, list_time, similar_time, export_time, format_time):.2f}ms")

        # Assertions
        assert build_time < 100, f"build_instincts_context too slow: {build_time:.2f}ms"
        assert list_time < 50, f"list_instincts too slow: {list_time:.2f}ms"
        assert similar_time < 50, f"find_similar_instincts too slow: {similar_time:.2f}ms"

    finally:
        # Cleanup
        thread_dir = Path(f"data/instincts/{thread_id}")
        if thread_dir.exists():
            import shutil
            shutil.rmtree(thread_dir)
            print(f"\n✅ Cleaned up test data")


def test_50_instincts_performance():
    """Test with 50 instincts to see scaling."""
    storage = InstinctStorage()
    injector = get_instinct_injector()

    thread_id = f"perf_test_50_{uuid.uuid4().hex[:8]}"

    try:
        # Create 50 test instincts
        print("\n=== Creating 50 test instincts ===")
        start = time.perf_counter()
        for i in range(50):
            storage.create_instinct(
                trigger=f"test trigger {i}",
                action=f"test action {i}",
                domain="communication",
                confidence=0.7,
                thread_id=thread_id,
            )
        create_time = (time.perf_counter() - start) * 1000
        print(f"✅ Created 50 instincts in {create_time:.2f}ms")

        # Test build_instincts_context
        print("\n=== Testing build_instincts_context (50 instincts) ===")
        iterations = 5
        times = []
        for i in range(iterations):
            start = time.perf_counter()
            context = injector.build_instincts_context(
                thread_id=thread_id,
                user_message="test message",
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)

        print(f"✅ {iterations} iterations:")
        print(f"   Average: {avg_time:.2f}ms")
        print(f"   Min:     {min_time:.2f}ms")
        print(f"   Max:     {max_time:.2f}ms")

        # Assertion
        assert avg_time < 100, f"Average build time too slow: {avg_time:.2f}ms"

    finally:
        # Cleanup
        thread_dir = Path(f"data/instincts/{thread_id}")
        if thread_dir.exists():
            import shutil
            shutil.rmtree(thread_dir)
            print(f"\n✅ Cleaned up test data")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("SIMPLE INTEGRATION TEST")
    print("="*60)

    test_basic_performance()
    test_50_instincts_performance()

    print("\n" + "="*60)
    print("ALL TESTS PASSED ✅")
    print("="*60)
