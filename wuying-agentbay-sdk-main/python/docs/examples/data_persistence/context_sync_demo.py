#!/usr/bin/env python3
"""
AgentBay SDK - Context Sync Dual-Mode Example

This example demonstrates the context.sync() method with dual calling patterns:
- Context creation for persistent storage
- Async calling pattern (immediate return)
- Sync calling pattern with callback (immediate return)
- Timing and status monitoring
- Error handling and timeout scenarios
"""

import json
import time
import asyncio
from agentbay import AgentBay, CreateSessionParams, ContextSync, SyncPolicy

async def main():
    """Main function"""
    print("🔄 AgentBay Context Sync Dual-Mode Example")
    
    # Initialize AgentBay client
    agent_bay = AgentBay()
    
    try:
        # Method 1: Async interface with callback
        print("\n" + "="*60)
        print("🔄 Method 1: context_sync_with_callback (Async with callback)")
        print("="*60)
        # Start the first demo without waiting for it to complete
        await context_sync_with_callback_demo(agent_bay)
        print("context_sync_with_callback_demo completed")
        print("="*60)
        
        # Sleep 3 seconds
        print("\n⏳ Sleeping 3 seconds before next demo...")
        await asyncio.sleep(3) 
        
        # Method 2: Sync interface with await
        print("\n" + "="*60)
        print("🔄 Method 2: context_sync (Sync with await)")
        print("="*60)
        await context_sync_demo(agent_bay)  # With await
        
    except Exception as e:
        print(f"❌ Example execution failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("✅ Context sync dual-mode example completed")


async def context_sync_with_callback_demo(agent_bay):
    """Method 1: Async interface with callback - function returns immediately"""
    print("\n🔄 Method 1: context_sync_with_callback (Async with callback)")
    print("📤 This method uses callback for completion notification")
    print("⚡ Function returns immediately, callback handles completion")
    
    # Create context and session
    print("\n📦 Creating context and session...")
    context_result = agent_bay.context.get("sync-callback-demo", create=True)
    if not context_result.success:
        print(f"❌ Context creation failed: {context_result.error_message}")
        return
    
    context = context_result.context
    print(f"✅ Context created: {context.id}")
    
    # Create session with context sync
    sync_policy = SyncPolicy.default()
    context_sync = ContextSync.new(
        context_id=context.id,
        path="/tmp/sync_data",
        policy=sync_policy
    )
    
    params = CreateSessionParams()
    params.context_syncs = [context_sync]
    session_result = agent_bay.create(params)
    
    if not session_result.success:
        print(f"❌ Session creation failed: {session_result.error_message}")
        return
    
    session = session_result.session
    print(f"✅ Session created: {session.session_id}")
    
    # Create test data
    print("\n💾 Creating test data...")
    session.command.execute_command("mkdir -p /tmp/sync_data/test_files")
    
    test_files = [
        ("/tmp/sync_data/test_files/small.txt", "Small test file content\n" * 10),
        ("/tmp/sync_data/test_files/medium.txt", "Medium test file content\n" * 100),
        ("/tmp/sync_data/config.json", json.dumps({
            "sync_demo": True,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "session_id": session.session_id
        }, indent=2))
    ]
    
    created_files = 0
    for file_path, content in test_files:
        write_result = session.file_system.write_file(file_path, content)
        if write_result.success:
            print(f"✅ Created file: {file_path}")
            created_files += 1
        else:
            print(f"❌ Failed to create file {file_path}: {write_result.error_message}")
    
    print(f"📊 Created {created_files}/{len(test_files)} test files")
    
    # Track sync timing
    sync_start_time = time.time()
    
    # Call context.sync() with callback - immediate return
    print("\n📤 Calling session.context.sync() with callback...")
    sync_result = await session.context.sync(callback=lambda success: (
        # Anonymous callback function - handles everything directly
        print(f"✅ Callback received: {'SUCCESS' if success else 'FAILED'} in {time.time() - sync_start_time:.2f} seconds") or
        print(f"   📊 {'All files synchronized successfully' if success else 'Some files may have failed to synchronize'}") or
        print("🧹 Deleting session after sync completion...") or
        agent_bay.delete(session) or
        print("✅ Session deleted successfully") or
        print("🎉 Callback-based sync completed!")
    ))
    
    if not sync_result.success:
        print(f"❌ Failed to initiate context sync: {sync_result.error_message}")
        return
    
    print("⚡ Context sync initiated successfully (immediate return)")
    print(f"   Request ID: {sync_result.request_id}")
    print(f"   Initial success: {sync_result.success}")
    print("✅ Method 1 completed: Async interface with callback")

async def context_sync_demo(agent_bay):
    """Method 2: Sync interface with await - wait for completion"""
    print("\n🔄 Method 2: context_sync (Sync with await)")
    print("📤 This method uses await to wait for completion")
    print("⏳ Function waits until sync is complete")
    
    # Create context and session
    print("\n📦 Creating context and session...")
    context_result = agent_bay.context.get("sync-await-demo", create=True)
    if not context_result.success:
        print(f"❌ Context creation failed: {context_result.error_message}")
        return
    
    context = context_result.context
    print(f"✅ Context created: {context.id}")
    
    # Create session with context sync
    sync_policy = SyncPolicy.default()
    context_sync = ContextSync.new(
        context_id=context.id,
        path="/tmp/sync_data",
        policy=sync_policy
    )
    
    params = CreateSessionParams()
    params.context_syncs = [context_sync]
    session_result = agent_bay.create(params)
    
    if not session_result.success:
        print(f"❌ Session creation failed: {session_result.error_message}")
        return
    
    session = session_result.session
    print(f"✅ Session created: {session.session_id}")
    
    # Create test data
    print("\n💾 Creating test data...")
    session.command.execute_command("mkdir -p /tmp/sync_data/test_files")
    
    test_files = [
        ("/tmp/sync_data/test_files/small.txt", "Small test file content\n" * 10),
        ("/tmp/sync_data/test_files/medium.txt", "Medium test file content\n" * 100),
        ("/tmp/sync_data/config.json", json.dumps({
            "sync_demo": True,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "session_id": session.session_id
        }, indent=2))
    ]
    
    created_files = 0
    for file_path, content in test_files:
        write_result = session.file_system.write_file(file_path, content)
        if write_result.success:
            print(f"✅ Created file: {file_path}")
            created_files += 1
        else:
            print(f"❌ Failed to create file {file_path}: {write_result.error_message}")
    
    print(f"📊 Created {created_files}/{len(test_files)} test files")
    
    # Track sync timing
    sync_start_time = time.time()
    
    # Call context.sync() with await - wait for completion
    print("\n📤 Calling await session.context.sync()...")
    sync_result = await session.context.sync()
    
    sync_duration = time.time() - sync_start_time
    
    if sync_result.success:
        print("✅ Sync completed successfully")
        print(f"   Request ID: {sync_result.request_id}")
        print(f"   Final success: {sync_result.success}")
        print(f"   Duration: {sync_duration:.2f} seconds")
    else:
        print("❌ Sync failed")
        print(f"   Request ID: {sync_result.request_id}")
        print(f"   Final success: {sync_result.success}")
        print(f"   Duration: {sync_duration:.2f} seconds")
    
    # Clean up session
    print("\n🧹 Cleaning up session...")
    delete_result = agent_bay.delete(session)
    if delete_result.success:
        print("✅ Session deleted successfully")
    else:
        print(f"❌ Session deletion failed: {delete_result.error_message}")
    
    print("✅ Method 2 completed: Sync interface with await")



if __name__ == "__main__":
    asyncio.run(main())

