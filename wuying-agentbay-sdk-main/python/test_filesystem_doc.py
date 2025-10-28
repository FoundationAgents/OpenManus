#!/usr/bin/env python3
import os
import sys
import time

from agentbay import AgentBay, CreateSessionParams

def main():
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        print("AGENTBAY_API_KEY environment variable not set")
        sys.exit(1)

    agent_bay = AgentBay(api_key=api_key)
    
    params = CreateSessionParams(image_id="code_latest")
    session_result = agent_bay.create(params=params)
    if not session_result.success:
        print(f"Failed to create session: {session_result.error_message}")
        sys.exit(1)
    
    session = session_result.session
    filesystem = session.file_system
    
    try:
        print("=== Test 1: Create Directory ===")
        test_dir = "/tmp/agentbay_test"
        create_result = filesystem.create_directory(test_dir)
        print(f"Success: {create_result.success}, Data: {create_result.data}, RequestID: {create_result.request_id}")
        
        print("\n=== Test 2: Write File ===")
        test_file = "/tmp/agentbay_test/test.txt"
        write_result = filesystem.write_file(test_file, "Hello, AgentBay!", mode="overwrite")
        print(f"Success: {write_result.success}, Data: {write_result.data}, RequestID: {write_result.request_id}")
        
        print("\n=== Test 3: Read File ===")
        read_result = filesystem.read_file(test_file)
        print(f"Success: {read_result.success}")
        print(f"Content: {read_result.content}")
        print(f"RequestID: {read_result.request_id}")
        
        print("\n=== Test 4: Edit File ===")
        edits = [{"oldText": "Hello", "newText": "Hi"}]
        edit_result = filesystem.edit_file(test_file, edits, dry_run=False)
        print(f"Success: {edit_result.success}, Data: {edit_result.data}, RequestID: {edit_result.request_id}")
        
        print("\n=== Test 5: Get File Info ===")
        info_result = filesystem.get_file_info(test_file)
        print(f"Success: {info_result.success}")
        if info_result.file_info:
            print(f"File Info: {info_result.file_info}")
        print(f"RequestID: {info_result.request_id}")
        
        print("\n=== Test 6: List Directory ===")
        list_result = filesystem.list_directory(test_dir)
        print(f"Success: {list_result.success}")
        print(f"Entries (Total: {len(list_result.entries) if list_result.entries else 0}):")
        if list_result.entries:
            for entry in list_result.entries:
                entry_type = "Directory" if entry.get("isDirectory") else "File"
                print(f"  - {entry_type}: {entry.get('name')}")
        print(f"RequestID: {list_result.request_id}")
        
        print("\n=== Test 7: Move File ===")
        new_path = "/tmp/agentbay_test/moved.txt"
        move_result = filesystem.move_file(test_file, new_path)
        print(f"Success: {move_result.success}, Data: {move_result.data}, RequestID: {move_result.request_id}")
        
        print("\n=== Test 8: Read Multiple Files ===")
        filesystem.write_file("/tmp/agentbay_test/file1.txt", "Content 1", mode="overwrite")
        filesystem.write_file("/tmp/agentbay_test/file2.txt", "Content 2", mode="overwrite")
        
        paths = ["/tmp/agentbay_test/file1.txt", "/tmp/agentbay_test/file2.txt"]
        multi_read_result = filesystem.read_multiple_files(paths)
        print(f"Success: {multi_read_result.success}")
        print(f"Files read: {len(multi_read_result.contents) if multi_read_result.contents else 0}")
        if multi_read_result.contents:
            for path, content in multi_read_result.contents.items():
                print(f"  - {path}: {content}")
        
        print("\n=== Test 9: Search Files ===")
        search_result = filesystem.search_files(test_dir, "*.txt")
        print(f"Success: {search_result.success}")
        print(f"Found {len(search_result.matches) if search_result.matches else 0} files:")
        if search_result.matches:
            for file in search_result.matches:
                print(f"  - {file}")
        print(f"RequestID: {search_result.request_id}")
        
        print("\n=== Test 10: Watch Directory ===")
        watch_dir = "/tmp/agentbay_watch_test"
        filesystem.create_directory(watch_dir)
        
        def on_change(events):
            print(f"Callback detected {len(events)} file changes:")
            for event in events:
                print(f"  - {event.event_type}: {event.path} ({event.path_type})")
        
        monitor_thread = filesystem.watch_directory(
            path=watch_dir,
            callback=on_change,
            interval=1.0
        )
        monitor_thread.start()
        
        time.sleep(2)
        
        print("Creating a test file in watched directory...")
        test_watch_file = watch_dir + "/watch_test.txt"
        filesystem.write_file(test_watch_file, "Watch test content", mode="overwrite")
        
        time.sleep(2)
        
        print("Modifying the test file...")
        filesystem.write_file(test_watch_file, "Modified watch test content", mode="overwrite")
        
        time.sleep(2)
        
        print("Stopping directory monitoring...")
        monitor_thread.stop_event.set()
        monitor_thread.join()
        print("Watch directory test completed")
        
        print("\n=== All tests completed ===")
        
    finally:
        print("\n=== Cleaning up session ===")
        agent_bay.delete(session)

if __name__ == "__main__":
    main()
