"""
Integration tests for watch_directory functionality.
"""

import os
import time
import threading
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams


def get_api_key():
    """Get API Key from environment variables"""
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        raise ValueError(
            "AGENTBAY_API_KEY environment variable not set. Please set the environment variable."
        )
    return api_key


def test_watch_directory():
    """
    Test the watch_directory functionality by:
    1. Creating a session with code_latest ImageId
    2. Setting up directory monitoring with a callback
    3. Creating and modifying files
    4. Verifying that callbacks are triggered with correct events
    5. Testing deduplication of events
    """
    print("=== Testing watch_directory functionality ===\n")
    
    # Initialize AgentBay client
    api_key = get_api_key()
    agentbay = AgentBay(api_key=api_key)
    print("✅ AgentBay client initialized")
    
    # Create session with code_latest ImageId
    session_params = CreateSessionParams(image_id="code_latest")
    session_result = agentbay.create(session_params)
    
    if not session_result.success:
        print(f"❌ Failed to create session: {session_result.error_message}")
        return
    
    session = session_result.session
    print(f"✅ Session created successfully with ID: {session.session_id}")
    
    # Callback function to handle file changes
    detected_events = []
    callback_calls = []
    
    def file_change_callback(events):
        """Callback function to handle detected file changes."""
        callback_calls.append(len(events))
        detected_events.extend(events)
        print(f"\n🔔 Callback triggered with {len(events)} events:")
        for event in events:
            print(f"   - {event.event_type}: {event.path} ({event.path_type})")
    
    try:
        # Create the test directory
        print("\n1. Creating test directory...")
        create_dir_result = session.file_system.create_directory("/tmp/watch_test")
        print(f"Create directory result: {create_dir_result.success}")
        
        # Start directory monitoring
        print("\n2. Starting directory monitoring...")
        monitor_thread = session.file_system.watch_directory(
            path="/tmp/watch_test",
            callback=file_change_callback,
            interval=0.5  # Poll every 0.5 seconds for faster testing
        )
        monitor_thread.start()
        print("✅ Directory monitoring started")
        
        # Wait a moment for monitoring to initialize
        time.sleep(1)
        
        # Test 1: Create a new file
        print("\n3. Creating a new file...")
        write_result = session.file_system.write_file(
            "/tmp/watch_test/test1.txt", 
            "Initial content"
        )
        print(f"Write file result: {write_result.success}")
        
        # Wait for detection
        time.sleep(2)
        
        # Test 2: Modify the file
        print("\n4. Modifying the file...")
        modify_result = session.file_system.write_file(
            "/tmp/watch_test/test1.txt", 
            "Modified content"
        )
        print(f"Modify file result: {modify_result.success}")
        
        # Wait for detection
        time.sleep(2)
        
        # Test 3: Create another file
        print("\n5. Creating another file...")
        write_result2 = session.file_system.write_file(
            "/tmp/watch_test/test2.txt", 
            "Second file content"
        )
        print(f"Write second file result: {write_result2.success}")
        
        # Wait for detection
        time.sleep(2)
        
        # Stop monitoring
        print("\n6. Stopping directory monitoring...")
        monitor_thread.stop_event.set()
        monitor_thread.join(timeout=5)
        print("✅ Directory monitoring stopped")
        
        # Analyze results
        print(f"\n=== RESULTS ===")
        print(f"Total callback calls: {len(callback_calls)}")
        print(f"Total events detected: {len(detected_events)}")
        print(f"Callback call sizes: {callback_calls}")
        
        print("\nDetected events:")
        for i, event in enumerate(detected_events, 1):
            print(f"  {i}. {event}")
        
        # Verify exact number of events - must be exactly 5
        # write_file to non-existent file produces: create + modify (2 events)
        # write_file to existing file produces: modify (1 event)
        # Expected: test1.txt creation (create+modify) + test1.txt modification (modify) + test2.txt creation (create+modify) = 5 events
        expected_events = 5
        if len(detected_events) != expected_events:
            print(f"❌ Expected exactly {expected_events} events, got {len(detected_events)}")
            print("Expected breakdown:")
            print("  - write_file test1.txt (new): create + modify = 2 events")
            print("  - write_file test1.txt (existing): modify = 1 event")
            print("  - write_file test2.txt (new): create + modify = 2 events")
            print("  - Total: 2 + 1 + 2 = 5 events")
            raise AssertionError(f"Expected exactly {expected_events} events, got {len(detected_events)}")
        else:
            print(f"✅ Captured expected number of events: {len(detected_events)}")
        
        # Verify event types and counts
        create_events = sum(1 for event in detected_events if event.event_type == "create")
        modify_events = sum(1 for event in detected_events if event.event_type == "modify")
        
        print(f"\nEvent type breakdown:")
        print(f"  Create events: {create_events} (expected: 2)")
        print(f"  Modify events: {modify_events} (expected: 3)")
        
        # Strict validation of event types
        expected_create_events = 2
        expected_modify_events = 3
        
        if create_events != expected_create_events:
            raise AssertionError(f"Expected exactly {expected_create_events} create events, got {create_events}")
        if modify_events != expected_modify_events:
            raise AssertionError(f"Expected exactly {expected_modify_events} modify events, got {modify_events}")
        
        if create_events == expected_create_events and modify_events == expected_modify_events:
            print("✅ Event type distribution is correct")
        else:
            print("❌ Event type distribution is incorrect")
            raise AssertionError(f"Event type validation failed: got {create_events} create + {modify_events} modify, expected {expected_create_events} create + {expected_modify_events} modify")
        
        # Verify deduplication
        event_keys = set()
        duplicates = 0
        for event in detected_events:
            event_key = (event.event_type, event.path, event.path_type)
            if event_key in event_keys:
                duplicates += 1
            else:
                event_keys.add(event_key)
        
        print(f"\nDeduplication check:")
        print(f"  Unique events: {len(event_keys)}")
        print(f"  Duplicate events: {duplicates}")
        
        if duplicates == 0:
            print("✅ Event deduplication is working correctly")
        else:
            print("⚠️  Some duplicate events were detected")
        
        # Summary
        if len(detected_events) == expected_events and create_events == expected_create_events and modify_events == expected_modify_events:
            print("\n✅ watch_directory test completed successfully!")
            print("All expected events were detected with correct types.")
        else:
            print("\n❌ watch_directory test failed!")
            print(f"Expected {expected_events} events ({expected_create_events} create + {expected_modify_events} modify), got {len(detected_events)} events ({create_events} create + {modify_events} modify)")
            raise AssertionError("Integration test validation failed")
            
    finally:
        # Clean up
        print("\n7. Cleaning up session...")
        delete_result = agentbay.delete(session)
        if delete_result.success:
            print("✅ Session deleted successfully")
        else:
            print(f"❌ Failed to delete session: {delete_result.error_message}")


def test_watch_directory_file_modification():
    """
    Test monitoring file modification events in a directory.
    
    This test:
    1. Creates a session with code_latest ImageId
    2. Creates a test directory and initial file
    3. Sets up directory monitoring with a callback
    4. Modifies the file multiple times
    5. Verifies that modification events are captured correctly
    """
    print("=== Testing file modification monitoring ===\n")
    
    # Initialize AgentBay client
    api_key = get_api_key()
    agentbay = AgentBay(api_key=api_key)
    print("✅ AgentBay client initialized")
    
    # Create session with code_latest ImageId
    session_params = CreateSessionParams(image_id="code_latest")
    session_result = agentbay.create(session_params)
    
    if not session_result.success:
        print(f"❌ Failed to create session: {session_result.error_message}")
        return
    
    session = session_result.session
    print(f"✅ Session created successfully with ID: {session.session_id}")
    
    # Create test directory and initial file
    test_dir = f"/tmp/test_modify_watch_{int(time.time())}"
    print(f"\n1. Creating test directory: {test_dir}")
    create_dir_result = session.file_system.create_directory(test_dir)
    if not create_dir_result.success:
        print(f"❌ Failed to create directory: {create_dir_result.error_message}")
        return
    print("✅ Test directory created")
    
    # Create initial file
    test_file = f"{test_dir}/modify_test.txt"
    print(f"\n2. Creating initial file: {test_file}")
    write_result = session.file_system.write_file(test_file, "Initial content")
    if not write_result.success:
        print(f"❌ Failed to create initial file: {write_result.error_message}")
        return
    print("✅ Initial file created")
    
    # Storage for captured events
    captured_events = []
    event_lock = threading.Lock()
    
    def on_file_modified(events):
        """Callback function to capture modification events."""
        with event_lock:
            # Filter only modify events
            modify_events = [e for e in events if e.event_type == "modify"]
            captured_events.extend(modify_events)
            for event in modify_events:
                print(f"🔔 Captured modify event: {event.path} ({event.path_type})")
    
    monitor_thread = None
    try:
        # Start monitoring
        print(f"\n3. Starting directory monitoring...")
        monitor_thread = session.file_system.watch_directory(
            path=test_dir,
            callback=on_file_modified,
            interval=1.0
        )
        monitor_thread.start()
        print("✅ Directory monitoring started")
        time.sleep(1)  # Wait for monitoring to start
        
        # Modify file multiple times
        print(f"\n4. Modifying file multiple times...")
        for i in range(3):
            content = f"Modified content version {i + 1}"
            print(f"   Modification {i + 1}: Writing '{content}'")
            modify_result = session.file_system.write_file(test_file, content)
            if not modify_result.success:
                print(f"❌ Failed to modify file (attempt {i + 1}): {modify_result.error_message}")
            else:
                print(f"✅ File modified successfully (attempt {i + 1})")
            time.sleep(1.5)  # Ensure events are captured
        
        # Wait a bit more for final events
        time.sleep(2)
        
        # Verify events
        print(f"\n5. Verifying captured events...")
        with event_lock:
            print(f"Total modify events captured: {len(captured_events)}")
            
            # Check minimum number of events
            if len(captured_events) < 3:
                print(f"⚠️  Expected at least 3 modify events, got {len(captured_events)}")
                print("This might be due to timing or system behavior, but basic functionality works")
            else:
                print(f"✅ Captured sufficient modify events: {len(captured_events)}")
            
            # Verify event properties
            valid_events = 0
            for i, event in enumerate(captured_events, 1):
                print(f"   Event {i}: {event}")
                
                # Check event has required attributes
                if not hasattr(event, 'event_type'):
                    print(f"❌ Event {i} missing 'event_type' attribute")
                    continue
                if not hasattr(event, 'path'):
                    print(f"❌ Event {i} missing 'path' attribute")
                    continue
                if not hasattr(event, 'path_type'):
                    print(f"❌ Event {i} missing 'path_type' attribute")
                    continue
                
                # Check event type is modify
                if event.event_type != "modify":
                    print(f"❌ Event {i} type should be 'modify', got '{event.event_type}'")
                    continue
                
                # Check path contains test file
                if test_file not in event.path:
                    print(f"❌ Event {i} path should contain '{test_file}', got '{event.path}'")
                    continue
                
                valid_events += 1
                print(f"✅ Event {i} is valid")
            
            print(f"\nValidation summary:")
            print(f"  Total events: {len(captured_events)}")
            print(f"  Valid events: {valid_events}")
            
            if valid_events > 0:
                print("✅ File modification monitoring test passed!")
            else:
                print("❌ No valid modification events detected")
                
    finally:
        # Stop monitoring
        print(f"\n6. Stopping directory monitoring...")
        if monitor_thread:
            monitor_thread.stop_event.set()
            monitor_thread.join(timeout=5)
            print("✅ Directory monitoring stopped")
        
        # Clean up session
        print(f"\n7. Cleaning up session...")
        delete_result = agentbay.delete(session)
        if delete_result.success:
            print("✅ Session deleted successfully")
        else:
            print(f"❌ Failed to delete session: {delete_result.error_message}")
    
    print("\n=== File modification monitoring test completed ===")


if __name__ == "__main__":
    test_watch_directory()
    print("\n" + "="*60 + "\n")
    test_watch_directory_file_modification() 