#!/usr/bin/env python3
"""
RecyclePolicy Example - Data Lifecycle Management

This example demonstrates how to use RecyclePolicy to control the lifecycle
of context data in the cloud.

Expected Output:
    ======================================================================
    Example 1: Default RecyclePolicy
    ======================================================================
    ✅ Context created: SdkCtx-xxxxxxxxxxxxx
       Lifecycle: Lifecycle_Forever
       Paths: ['']
    ✅ Session created: session-xxxxxxxxxxxxx
    ✅ Data written to /tmp/default_data/test.txt
    ✅ Session deleted
    ✅ Context deleted

    ======================================================================
    Example 2: RecyclePolicy with 1 Day Lifecycle
    ======================================================================
    ✅ Context created: SdkCtx-xxxxxxxxxxxxx
       Lifecycle: Lifecycle_1Day
       Paths: ['']
    ✅ Session created: session-xxxxxxxxxxxxx
    ✅ Data written to /tmp/oneday_data/test.txt
       ℹ️  This data will be automatically deleted after 1 day
    ✅ Session deleted
    ✅ Context deleted

    ======================================================================
    Example 3: RecyclePolicy for Specific Paths
    ======================================================================
    ✅ Context created: SdkCtx-xxxxxxxxxxxxx
       Lifecycle: Lifecycle_3Days
       Paths: ['/tmp/cache', '/tmp/logs']
       ℹ️  Only files in /tmp/cache and /tmp/logs will be deleted after 3 days
    ✅ Session created: session-xxxxxxxxxxxxx
    ✅ Session deleted
    ✅ Context deleted

    ======================================================================
    Example 4: Different Lifecycle Options
    ======================================================================
    📋 Available Lifecycle Options:
    --------------------------------------------------
       Lifecycle_1Day            - 1 day
       Lifecycle_3Days           - 3 days
       Lifecycle_5Days           - 5 days
       Lifecycle_10Days          - 10 days
       Lifecycle_30Days          - 30 days
       Lifecycle_Forever         - Forever (permanent)
    ✅ All lifecycle options validated successfully

    ======================================================================
    Example 5: Error Handling - Wildcard Patterns
    ======================================================================
    ❌ Test 1: Using wildcard * in path (should fail)
       ✅ Correctly rejected: Wildcard patterns are not supported...
    ❌ Test 2: Using wildcard ? in path (should fail)
       ✅ Correctly rejected: Wildcard patterns are not supported...
    ❌ Test 3: Using wildcard [ ] in path (should fail)
       ✅ Correctly rejected: Wildcard patterns are not supported...
    ❌ Test 4: Using invalid lifecycle value (should fail)
       ✅ Correctly rejected: Invalid lifecycle value...
    ✅ Test 5: Correct usage with exact paths
       ✅ Successfully created with paths: ['/tmp/cache', '/var/log']

    ======================================================================
    ✅ All RecyclePolicy examples completed successfully!
    ======================================================================
"""

import os
from agentbay import AgentBay, CreateSessionParams
from agentbay.context_sync import (
    ContextSync,
    SyncPolicy,
    RecyclePolicy,
    Lifecycle,
    UploadPolicy,
    DownloadPolicy,
    DeletePolicy,
    ExtractPolicy,
    BWList,
    WhiteList
)


def example_1_default_recycle_policy():
    """Example 1: Using default RecyclePolicy (keeps data forever)"""
    print("\n" + "="*70)
    print("Example 1: Default RecyclePolicy")
    print("="*70)

    agent_bay = AgentBay()

    # Create a context
    context_result = agent_bay.context.get("default-recycle-demo", create=True)
    if not context_result.success:
        print(f"❌ Failed to create context: {context_result.error_message}")
        return

    context = context_result.context
    print(f"✅ Context created: {context.id}")

    # Use default SyncPolicy (includes default RecyclePolicy with LIFECYCLE_FOREVER)
    sync_policy = SyncPolicy.default()
    print(f"   Lifecycle: {sync_policy.recycle_policy.lifecycle.value}")
    print(f"   Paths: {sync_policy.recycle_policy.paths}")

    context_sync = ContextSync.new(
        context_id=context.id,
        path="/tmp/default_data",
        policy=sync_policy
    )

    # Create session with context sync
    params = CreateSessionParams(context_syncs=[context_sync])
    session_result = agent_bay.create(params)

    if not session_result.success:
        print(f"❌ Failed to create session: {session_result.error_message}")
        return

    session = session_result.session
    print(f"✅ Session created: {session.session_id}")

    # Write some data
    session.command.execute_command("echo 'Default policy - data kept forever' > /tmp/default_data/test.txt")
    print("✅ Data written to /tmp/default_data/test.txt")

    # Clean up
    agent_bay.delete(session)
    print("✅ Session deleted")

    # Clean up context
    agent_bay.context.delete(context)
    print("✅ Context deleted")


def example_2_one_day_lifecycle():
    """Example 2: Set RecyclePolicy to keep data for 1 day"""
    print("\n" + "="*70)
    print("Example 2: RecyclePolicy with 1 Day Lifecycle")
    print("="*70)

    agent_bay = AgentBay()

    # Create a context
    context_result = agent_bay.context.get("one-day-recycle-demo", create=True)
    if not context_result.success:
        print(f"❌ Failed to create context: {context_result.error_message}")
        return

    context = context_result.context
    print(f"✅ Context created: {context.id}")

    # Create custom RecyclePolicy with 1 day lifecycle
    recycle_policy = RecyclePolicy(
        lifecycle=Lifecycle.LIFECYCLE_1DAY,
        paths=[""]  # Apply to all paths
    )

    # Create SyncPolicy with custom RecyclePolicy
    sync_policy = SyncPolicy(
        upload_policy=UploadPolicy.default(),
        download_policy=DownloadPolicy.default(),
        delete_policy=DeletePolicy.default(),
        extract_policy=ExtractPolicy.default(),
        recycle_policy=recycle_policy,
        bw_list=BWList(white_lists=[WhiteList(path="", exclude_paths=[])])
    )

    print(f"   Lifecycle: {sync_policy.recycle_policy.lifecycle.value}")
    print(f"   Paths: {sync_policy.recycle_policy.paths}")

    context_sync = ContextSync.new(
        context_id=context.id,
        path="/tmp/oneday_data",
        policy=sync_policy
    )

    # Create session with context sync
    params = CreateSessionParams(
        labels={"example": "recycle_policy", "lifecycle": "1day"},
        context_syncs=[context_sync]
    )
    session_result = agent_bay.create(params)

    if not session_result.success:
        print(f"❌ Failed to create session: {session_result.error_message}")
        return

    session = session_result.session
    print(f"✅ Session created: {session.session_id}")

    # Write some data
    session.command.execute_command("mkdir -p /tmp/oneday_data")
    session.command.execute_command("echo 'This data will be deleted after 1 day' > /tmp/oneday_data/test.txt")
    print("✅ Data written to /tmp/oneday_data/test.txt")
    print("   ℹ️  This data will be automatically deleted after 1 day")

    # Clean up
    agent_bay.delete(session)
    print("✅ Session deleted")

    # Clean up context
    agent_bay.context.delete(context)
    print("✅ Context deleted")


def example_3_specific_paths():
    """Example 3: Apply RecyclePolicy to specific paths"""
    print("\n" + "="*70)
    print("Example 3: RecyclePolicy for Specific Paths")
    print("="*70)

    agent_bay = AgentBay()

    # Create a context
    context_result = agent_bay.context.get("specific-path-demo", create=True)
    if not context_result.success:
        print(f"❌ Failed to create context: {context_result.error_message}")
        return

    context = context_result.context
    print(f"✅ Context created: {context.id}")

    # Create RecyclePolicy for specific paths
    recycle_policy = RecyclePolicy(
        lifecycle=Lifecycle.LIFECYCLE_3DAYS,
        paths=["/tmp/cache", "/tmp/logs"]  # Only these paths
    )

    sync_policy = SyncPolicy(recycle_policy=recycle_policy)

    print(f"   Lifecycle: {sync_policy.recycle_policy.lifecycle.value}")
    print(f"   Paths: {sync_policy.recycle_policy.paths}")
    print("   ℹ️  Only files in /tmp/cache and /tmp/logs will be deleted after 3 days")

    context_sync = ContextSync.new(
        context_id=context.id,
        path="/tmp/multipath_data",
        policy=sync_policy
    )

    # Create session
    params = CreateSessionParams(context_syncs=[context_sync])
    session_result = agent_bay.create(params)

    if not session_result.success:
        print(f"❌ Failed to create session: {session_result.error_message}")
        return

    session = session_result.session
    print(f"✅ Session created: {session.session_id}")

    # Clean up
    agent_bay.delete(session)
    print("✅ Session deleted")

    # Clean up context
    agent_bay.context.delete(context)
    print("✅ Context deleted")


def example_4_different_lifecycles():
    """Example 4: Demonstrate different lifecycle options"""
    print("\n" + "="*70)
    print("Example 4: Different Lifecycle Options")
    print("="*70)

    lifecycles = [
        (Lifecycle.LIFECYCLE_1DAY, "1 day"),
        (Lifecycle.LIFECYCLE_3DAYS, "3 days"),
        (Lifecycle.LIFECYCLE_5DAYS, "5 days"),
        (Lifecycle.LIFECYCLE_10DAYS, "10 days"),
        (Lifecycle.LIFECYCLE_30DAYS, "30 days"),
        (Lifecycle.LIFECYCLE_FOREVER, "Forever (permanent)")
    ]

    print("\n📋 Available Lifecycle Options:")
    print("-" * 50)
    for lifecycle, description in lifecycles:
        recycle_policy = RecyclePolicy(lifecycle=lifecycle, paths=[""])
        print(f"   {lifecycle.value:25s} - {description}")

    print("\n✅ All lifecycle options validated successfully")


def example_5_error_handling():
    """Example 5: Error handling - wildcard patterns not supported"""
    print("\n" + "="*70)
    print("Example 5: Error Handling - Wildcard Patterns")
    print("="*70)

    # Test 1: Wildcard in path
    print("\n❌ Test 1: Using wildcard * in path (should fail)")
    try:
        recycle_policy = RecyclePolicy(
            lifecycle=Lifecycle.LIFECYCLE_1DAY,
            paths=["/invalid/path/*"]
        )
        print("   ERROR: Should have raised ValueError!")
    except ValueError as e:
        print(f"   ✅ Correctly rejected: {str(e)[:80]}...")

    # Test 2: Question mark wildcard
    print("\n❌ Test 2: Using wildcard ? in path (should fail)")
    try:
        recycle_policy = RecyclePolicy(
            lifecycle=Lifecycle.LIFECYCLE_1DAY,
            paths=["/invalid/path?"]
        )
        print("   ERROR: Should have raised ValueError!")
    except ValueError as e:
        print(f"   ✅ Correctly rejected: {str(e)[:80]}...")

    # Test 3: Bracket wildcard
    print("\n❌ Test 3: Using wildcard [ ] in path (should fail)")
    try:
        recycle_policy = RecyclePolicy(
            lifecycle=Lifecycle.LIFECYCLE_1DAY,
            paths=["/invalid/path[abc]"]
        )
        print("   ERROR: Should have raised ValueError!")
    except ValueError as e:
        print(f"   ✅ Correctly rejected: {str(e)[:80]}...")

    # Test 4: Invalid lifecycle
    print("\n❌ Test 4: Using invalid lifecycle value (should fail)")
    try:
        recycle_policy = RecyclePolicy(
            lifecycle="invalid_lifecycle",
            paths=[""]
        )
        print("   ERROR: Should have raised ValueError!")
    except ValueError as e:
        print(f"   ✅ Correctly rejected: {str(e)[:80]}...")

    # Test 5: Correct usage
    print("\n✅ Test 5: Correct usage with exact paths")
    try:
        recycle_policy = RecyclePolicy(
            lifecycle=Lifecycle.LIFECYCLE_1DAY,
            paths=["/tmp/cache", "/var/log"]
        )
        print(f"   ✅ Successfully created with paths: {recycle_policy.paths}")
    except ValueError as e:
        print(f"   ERROR: Should not have raised error: {e}")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("RecyclePolicy Examples - Data Lifecycle Management")
    print("="*70)
    print("\nThese examples demonstrate how to use RecyclePolicy to control")
    print("the lifecycle of context data in the cloud.")

    try:
        # Run examples
        example_1_default_recycle_policy()
        example_2_one_day_lifecycle()
        example_3_specific_paths()
        example_4_different_lifecycles()
        example_5_error_handling()

        print("\n" + "="*70)
        print("✅ All RecyclePolicy examples completed successfully!")
        print("="*70)

    except Exception as e:
        print(f"\n❌ Example failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

