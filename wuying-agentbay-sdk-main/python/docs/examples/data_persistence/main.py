#!/usr/bin/env python3
"""
AgentBay SDK - Data Persistence Example

This example demonstrates real data persistence functionality:
- Context creation for persistent storage
- File persistence across multiple sessions
- Context synchronization and file sharing
"""

import json
import time
from agentbay import AgentBay, CreateSessionParams, ContextSync, SyncPolicy

def main():
    """Main function"""
    print("🗄️ AgentBay Data Persistence Example")
    
    # Initialize AgentBay client
    agent_bay = AgentBay()
    
    try:
        # Run the complete data persistence demonstration
        data_persistence_demo(agent_bay)
        
    except Exception as e:
        print(f"❌ Example execution failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("✅ Data persistence example completed")

def data_persistence_demo(agent_bay):
    """Complete data persistence demonstration"""
    print("\n🔄 === Data Persistence Demonstration ===")
    
    # Step 1: Create a context for persistent storage
    print("\n📦 Step 1: Creating context for persistent storage...")
    context_result = agent_bay.context.get("persistence-demo", create=True)
    
    if not context_result.success:
        print(f"❌ Context creation failed: {context_result.error_message}")
        return
    
    context = context_result.context
    print(f"✅ Context created successfully: {context.id}")
    print(f"   Name: {context.name}")
    print(f"   State: {context.state}")
    
    # Step 2: Create first session with context sync
    print("\n🔧 Step 2: Creating first session with context synchronization...")
    
    # Create sync policy for context synchronization
    sync_policy = SyncPolicy.default()
    
    # Create context sync configuration
    context_sync = ContextSync.new(
        context_id=context.id,
        path="/tmp/persistent_data",  # Mount context to this path in session
        policy=sync_policy
    )
    
    # Create session with context sync
    params1 = CreateSessionParams()
    params1.context_syncs = [context_sync]
    session1_result = agent_bay.create(params1)
    
    if not session1_result.success:
        print(f"❌ First session creation failed: {session1_result.error_message}")
        return
    
    session1 = session1_result.session
    print(f"✅ First session created successfully: {session1.session_id}")
    
    try:
        # Step 3: Write persistent data in first session
        print("\n💾 Step 3: Writing persistent data in first session...")
        
        # Create directory structure
        session1.command.execute_command("mkdir -p /tmp/persistent_data/config")
        session1.command.execute_command("mkdir -p /tmp/persistent_data/logs")
        
        # Write configuration file
        config_data = {
            "app_name": "AgentBay Demo",
            "version": "1.0.0",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "session_id": session1.session_id,
            "features": ["data_persistence", "context_sync", "multi_session"]
        }
        config_content = json.dumps(config_data, indent=2)
        
        config_result = session1.file_system.write_file("/tmp/persistent_data/config/app.json", config_content)
        if config_result.success:
            print("✅ Configuration file written successfully")
        else:
            print(f"❌ Failed to write config file: {config_result.error_message}")
        
        # Write a log file
        log_content = f"""Application Log - Session 1
Created: {time.strftime("%Y-%m-%d %H:%M:%S")}
Session ID: {session1.session_id}
Operation: Data persistence demonstration
Status: Files created successfully
"""
        
        log_result = session1.file_system.write_file("/tmp/persistent_data/logs/session1.log", log_content)
        if log_result.success:
            print("✅ Log file written successfully")
        else:
            print(f"❌ Failed to write log file: {log_result.error_message}")
        
        # Write a data file
        data_content = "This is persistent data that should be available across sessions.\nIt demonstrates the context synchronization functionality."
        
        data_result = session1.file_system.write_file("/tmp/persistent_data/shared_data.txt", data_content)
        if data_result.success:
            print("✅ Data file written successfully")
        else:
            print(f"❌ Failed to write data file: {data_result.error_message}")
        
        # List files to verify
        print("\n📋 Files created in first session:")
        list_result = session1.command.execute_command("find /tmp/persistent_data -type f -ls")
        if list_result.success:
            print(list_result.output)
        
    finally:
        # Clean up first session
        print("\n🧹 Cleaning up first session...")
        delete_result1 = agent_bay.delete(session1, sync_context=True)  # Sync before deletion
        if delete_result1.success:
            print("✅ First session deleted successfully (with context sync)")
        else:
            print(f"❌ First session deletion failed: {delete_result1.error_message}")
    
    # Step 4: Create second session to verify persistence
    print("\n🔧 Step 4: Creating second session to verify data persistence...")
    
    # Create second session with same context sync
    params2 = CreateSessionParams()
    params2.context_syncs = [context_sync]
    session2_result = agent_bay.create(params2)
    
    if not session2_result.success:
        print(f"❌ Second session creation failed: {session2_result.error_message}")
        return
    
    session2 = session2_result.session
    print(f"✅ Second session created successfully: {session2.session_id}")
    
    try:
        # Step 5: Verify persistent data in second session
        print("\n🔍 Step 5: Verifying persistent data in second session...")
        
        # Note: agent_bay.create() already waits for context synchronization to complete
        print("✅ Context synchronization completed (handled by agent_bay.create())")
        
        # Check if files exist
        files_to_check = [
            "/tmp/persistent_data/config/app.json",
            "/tmp/persistent_data/logs/session1.log", 
            "/tmp/persistent_data/shared_data.txt"
        ]
        
        persistent_files_found = 0
        
        for file_path in files_to_check:
            print(f"\n🔍 Checking file: {file_path}")
            read_result = session2.file_system.read_file(file_path)
            
            if read_result.success:
                print(f"✅ File found and readable!")
                if file_path.endswith('.json'):
                    try:
                        data = json.loads(read_result.content)
                        print(f"   📄 Config data: {data['app_name']} v{data['version']}")
                        print(f"   🕒 Created by session: {data['session_id']}")
                    except:
                        print(f"   📄 Content: {read_result.content[:100]}...")
                else:
                    print(f"   📄 Content preview: {read_result.content[:100]}...")
                persistent_files_found += 1
            else:
                print(f"❌ File not found or not readable: {read_result.error_message}")
        
        # Add new data in second session
        print(f"\n💾 Adding new data in second session...")
        session2_log = f"""Application Log - Session 2
Created: {time.strftime("%Y-%m-%d %H:%M:%S")}
Session ID: {session2.session_id}
Operation: Data persistence verification
Persistent files found: {persistent_files_found}/{len(files_to_check)}
Status: Persistence verification completed
"""
        
        session2_result = session2.file_system.write_file("/tmp/persistent_data/logs/session2.log", session2_log)
        if session2_result.success:
            print("✅ Second session log written successfully")
        
        # Summary
        print(f"\n📊 === Persistence Verification Summary ===")
        print(f"✅ Context ID: {context.id}")
        print(f"✅ First session: {session1.session_id} (deleted)")
        print(f"✅ Second session: {session2.session_id} (active)")
        print(f"✅ Persistent files found: {persistent_files_found}/{len(files_to_check)}")
        
        if persistent_files_found == len(files_to_check):
            print("🎉 Data persistence verification SUCCESSFUL!")
            print("   Files created in first session are accessible in second session")
        else:
            print("⚠️  Data persistence verification PARTIAL")
            print("   Some files may still be syncing or failed to persist")
        
    finally:
        # Clean up second session
        print("\n🧹 Cleaning up second session...")
        delete_result2 = agent_bay.delete(session2, sync_context=True)
        if delete_result2.success:
            print("✅ Second session deleted successfully (with context sync)")
        else:
            print(f"❌ Second session deletion failed: {delete_result2.error_message}")


if __name__ == "__main__":
    main() 