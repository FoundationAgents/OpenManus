#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Example demonstrating FileSystem operations with AgentBay SDK.
This example shows how to use various file system operations including:
- Basic file reading and writing
- Directory operations
- File information retrieval
- File editing
- File searching
- Multiple file reading
- Large file operations with chunking
"""

import os
import time

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams


def main():
    # Get API key from environment variable
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        print("Error: AGENTBAY_API_KEY environment variable not set")
        return

    # Initialize AgentBay client
    print("Initializing AgentBay client...")
    agent_bay = AgentBay(api_key=api_key)

    # Create a session
    print("Creating a new session...")
    params = CreateSessionParams(
        image_id="linux_latest",  # Specify the image ID
    )
    session_result = agent_bay.create(params)
    session = session_result.session
    print(f"Session created with ID: {session.session_id}")
    print(f"Request ID: {session_result.request_id}")

    try:
        # Get the FileSystem interface
        fs = session.file_system

        # ===== BASIC FILE OPERATIONS =====
        print("\n===== BASIC FILE OPERATIONS =====")

        # Example 1: Write a simple file
        print("\nExample 1: Writing a simple file...")
        test_content = (
            "This is a test file content.\nIt has multiple lines.\n"
            "This is the third line."
        )
        test_file_path = "/tmp/test_file.txt"

        result = fs.write_file(test_file_path, test_content, "overwrite")
        print(f"File write successful: {result.success}")
        if not result.success:
            print(f"Error: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # Example 2: Read the file
        print("\nExample 2: Reading the file...")
        result = fs.read_file(test_file_path)
        if result.success:
            content = result.content
            print(f"File content ({len(content)} bytes):")
            print(content)
            print(f"Content matches original: {content == test_content}")
        else:
            print(f"Error reading file: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # Example 3: Append to the file
        print("\nExample 3: Appending to the file...")
        append_content = "\nThis is an appended line."
        result = fs.write_file(test_file_path, append_content, "append")
        print(f"File append successful: {result.success}")
        if not result.success:
            print(f"Error: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # Read the file again to verify append
        result = fs.read_file(test_file_path)
        if result.success:
            updated_content = result.content
            print(f"Updated file content ({len(updated_content)} bytes):")
            print(updated_content)
            print(
                f"Content matches: {updated_content == test_content + append_content}"
            )
        else:
            print(f"Error reading updated file: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # ===== DIRECTORY OPERATIONS =====
        print("\n===== DIRECTORY OPERATIONS =====")

        # Example 4: Create a directory
        print("\nExample 4: Creating a directory...")
        test_dir_path = "/tmp/test_directory"
        result = fs.create_directory(test_dir_path)
        print(f"Directory creation successful: {result.success}")
        if not result.success:
            print(f"Error: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # Example 5: List directory contents
        print("\nExample 5: Listing directory contents...")
        result = fs.list_directory("/tmp")
        if result.success:
            entries = result.entries
            print(f"Found {len(entries)} entries in /tmp:")
            for entry in entries:
                entry_type = "Directory" if entry["isDirectory"] else "File"
                print(f"  - {entry['name']} ({entry_type})")
        else:
            print(f"Error listing directory: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # ===== FILE INFORMATION =====
        print("\n===== FILE INFORMATION =====")

        # Example 6: Get file information
        print("\nExample 6: Getting file information...")
        result = fs.get_file_info(test_file_path)
        if result.success:
            file_info = result.file_info
            print(f"File information for {test_file_path}:")
            for key, value in file_info.items():
                print(f"  - {key}: {value}")
        else:
            print(f"Error getting file info: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # ===== FILE EDITING =====
        print("\n===== FILE EDITING =====")

        # Example 7: Edit a file
        print("\nExample 7: Editing a file...")
        edits = [
            {
                "oldText": "This is the third line.",
                "newText": "This line has been edited.",
            }
        ]
        result = fs.edit_file(test_file_path, edits)
        print(f"File edit successful: {result.success}")
        if not result.success:
            print(f"Error: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # Read the file again to verify edit
        result = fs.read_file(test_file_path)
        if result.success:
            edited_content = result.content
            print(f"Edited file content ({len(edited_content)} bytes):")
            print(edited_content)
        else:
            print(f"Error reading edited file: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # ===== FILE MOVING =====
        print("\n===== FILE MOVING =====")

        # Example 8: Move a file
        print("\nExample 8: Moving a file...")
        source_path = "/tmp/test_file.txt"
        dest_path = "/tmp/test_directory/moved_file.txt"
        result = fs.move_file(source_path, dest_path)
        print(f"File move successful: {result.success}")
        if not result.success:
            print(f"Error: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # Verify the file was moved
        result = fs.read_file(dest_path)
        if result.success:
            moved_content = result.content
            print(f"Moved file content length: {len(moved_content)} bytes")
            print(f"Content preserved after move: {moved_content == edited_content}")
        else:
            print(f"Error reading moved file: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # ===== FILE SEARCHING =====
        print("\n===== FILE SEARCHING =====")

        # Create some files for searching
        fs.write_file(
            "/tmp/test_directory/file1.txt",
            "This file contains the word SEARCHABLE",
            "overwrite",
        )
        fs.write_file(
            "/tmp/test_directory/file2.txt",
            "This file does not contain the keyword",
            "overwrite",
        )
        fs.write_file(
            "/tmp/test_directory/file3.txt",
            "This file also contains SEARCHABLE term",
            "overwrite",
        )

        # Example 9: Search for files
        print("\nExample 9: Searching for files...")
        result = fs.search_files("/tmp/test_directory", "SEARCHABLE")
        if result.success:
            search_results = result.matches
            print(f"Found {len(search_results)} files matching the search pattern:")
            for result_file in search_results:
                print(f"  - {result_file}")
        else:
            print(f"Error searching files: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # ===== MULTIPLE FILE READING =====
        print("\n===== MULTIPLE FILE READING =====")

        # Example 10: Read multiple files
        print("\nExample 10: Reading multiple files...")
        file_paths = [
            "/tmp/test_directory/file1.txt",
            "/tmp/test_directory/file2.txt",
            "/tmp/test_directory/file3.txt",
        ]
        result = fs.read_multiple_files(file_paths)
        if result.success:
            multi_file_contents = result.contents
            print(f"Read {len(multi_file_contents)} files:")
            for path, content in multi_file_contents.items():
                print(f"  - {path}: {len(content)} bytes")
                print(f"    Content: {content}")
        else:
            print(f"Error reading multiple files: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # ===== LARGE FILE OPERATIONS =====
        print("\n===== LARGE FILE OPERATIONS =====")

        # Example 11: Write a large file with default chunk size
        print("\nExample 11: Writing a large file with default chunk size...")

        # Generate approximately 1MB of test content
        line_content = "This is a line of test content for large file testing. " * 20
        large_content = line_content * 500  # About 1MB
        test_file_path = "/tmp/large_file_default.txt"

        print(f"Generated test content size: {len(large_content)} bytes")

        # Write the large file (automatic chunking)
        start_time = time.time()
        result = fs.write_file(test_file_path, large_content)
        write_time = time.time() - start_time

        print(f"Write operation completed in {write_time:.2f} seconds")
        print(f"Success: {result.success}")
        if not result.success:
            print(f"Error: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # Example 12: Read the large file (automatic chunking)
        print("\nExample 12: Reading the large file with automatic chunking...")

        start_time = time.time()
        result = fs.read_file(test_file_path)
        read_time = time.time() - start_time

        if result.success:
            read_content = result.content
            print(f"Read operation completed in {read_time:.2f} seconds")
            print(f"Content length: {len(read_content)} bytes")
            print(f"Content matches original: {read_content == large_content}")
        else:
            print(f"Error reading large file: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # Example 13: Write another large file
        print("\nExample 13: Writing another large file...")

        test_file_path2 = "/tmp/large_file_2.txt"

        start_time = time.time()
        result = fs.write_file(test_file_path2, large_content)
        write_time = time.time() - start_time

        print(
            f"Second large file write operation completed in "
            f"{write_time:.2f} seconds"
        )
        print(f"Success: {result.success}")
        if not result.success:
            print(f"Error: {result.error_message}")
        print(f"Request ID: {result.request_id}")

        # Example 14: Read the second large file
        print("\nExample 14: Reading the second large file...")

        start_time = time.time()
        result = fs.read_file(test_file_path2)
        read_time = time.time() - start_time

        if result.success:
            read_content2 = result.content
            print(
                f"Second large file read operation completed in "
                f"{read_time:.2f} seconds"
            )
            print(f"Content length: {len(read_content2)} bytes")
            print(f"Content matches original: {read_content2 == large_content}")
        else:
            print(
                f"Error reading second large file: "
                f"{result.error_message}"
            )
        print(f"Request ID: {result.request_id}")

    finally:
        # Clean up: Delete the session
        print("\nCleaning up: Deleting the session...")
        delete_result = agent_bay.delete(session)
        print(f"Session deleted successfully. Request ID: {delete_result.request_id}")


if __name__ == "__main__":
    main()
