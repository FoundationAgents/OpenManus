#!/usr/bin/env python3
"""
Watch Directory Example

This example demonstrates how to use the watch_directory functionality
to monitor file changes in a directory.
"""

import os
import time
import threading
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams


def main():
    """Main function demonstrating watch_directory usage."""
    
    # Get API key from environment variable
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        print("❌ Please set the AGENTBAY_API_KEY environment variable")
        return
    
    print("🚀 Watch Directory Example")
    print("=" * 50)
    
    # Initialize AgentBay client
    agentbay = AgentBay(api_key=api_key)
    print("✅ AgentBay client initialized")
    
    # Create session with code_latest ImageId
    session_params = CreateSessionParams(image_id="code_latest")
    session_result = agentbay.create(session_params)
    
    if not session_result.success:
        print(f"❌ Failed to create session: {session_result.error_message}")
        return
    
    session = session_result.session
    print(f"✅ Session created: {session.session_id}")
    
    try:
        # Create a test directory to monitor
        test_dir = "/tmp/watch_example"
        print(f"\n📁 Creating test directory: {test_dir}")
        
        create_result = session.file_system.create_directory(test_dir)
        if not create_result.success:
            print(f"❌ Failed to create directory: {create_result.error_message}")
            return
        
        print("✅ Test directory created")
        
        # Set up file change monitoring
        detected_changes = []
        
        def on_file_change(events):
            """Callback function to handle file changes."""
            if events:  # Only process if there are actual events
                print(f"\n🔔 Detected {len(events)} file changes:")
                for event in events:
                    print(f"   📄 {event.event_type.upper()}: {event.path} ({event.path_type})")
                detected_changes.extend(events)
        
        print(f"\n👁️  Starting directory monitoring...")
        print("   Press Ctrl+C to stop monitoring")
        
        # Start monitoring
        monitor_thread = session.file_system.watch_directory(
            path=test_dir,
            callback=on_file_change,
            interval=1.0  # Check every second
        )
        monitor_thread.start()
        print("✅ Directory monitoring started")
        
        # Demonstrate file operations
        print("\n🔨 Demonstrating file operations...")
        
        # Create some files
        files_to_create = [
            ("example1.txt", "Hello, World!"),
            ("example2.txt", "This is a test file."),
            ("config.json", '{"setting": "value"}')
        ]
        
        for filename, content in files_to_create:
            filepath = f"{test_dir}/{filename}"
            print(f"   Creating: {filename}")
            
            write_result = session.file_system.write_file(filepath, content)
            if write_result.success:
                print(f"   ✅ Created: {filename}")
            else:
                print(f"   ❌ Failed to create {filename}: {write_result.error_message}")
            
            time.sleep(1.5)  # Give time for monitoring to detect changes
        
        # Modify a file
        print("\n   Modifying example1.txt...")
        modify_result = session.file_system.write_file(
            f"{test_dir}/example1.txt", 
            "Hello, World! - Modified content"
        )
        if modify_result.success:
            print("   ✅ Modified example1.txt")
        else:
            print(f"   ❌ Failed to modify file: {modify_result.error_message}")
        
        # Wait a bit more to capture all events
        print("\n⏳ Waiting for final events...")
        time.sleep(3)
        
        # Stop monitoring
        print("\n🛑 Stopping directory monitoring...")
        monitor_thread.stop_event.set()
        monitor_thread.join(timeout=5)
        print("✅ Directory monitoring stopped")
        
        # Summary
        print(f"\n📊 Summary:")
        print(f"   Total events detected: {len(detected_changes)}")
        
        if detected_changes:
            print("   Event breakdown:")
            event_types = {}
            for event in detected_changes:
                event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
            
            for event_type, count in event_types.items():
                print(f"     {event_type}: {count}")
        
        print("\n✨ Example completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped by user")
        
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        
    finally:
        # Clean up session
        print("\n🧹 Cleaning up...")
        delete_result = agentbay.delete(session)
        if delete_result.success:
            print("✅ Session cleaned up successfully")
        else:
            print(f"⚠️  Session cleanup warning: {delete_result.error_message}")


if __name__ == "__main__":
    main() 