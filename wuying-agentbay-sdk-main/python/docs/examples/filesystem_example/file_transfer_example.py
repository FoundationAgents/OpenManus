#!/usr/bin/env python3
"""
File Transfer Example

This example demonstrates how to use the file transfer functionality
to upload and download files between local storage and the AgentBay cloud environment.
"""

import os
import tempfile
import time
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams, BrowserContext


def create_test_file(content: str, suffix: str = ".txt") -> str:
    """Create a temporary test file with the given content."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=suffix) as f:
        f.write(content)
        return f.name


def file_transfer_example():
    """Demonstrates file upload and download operations."""
    
    # Get API key from environment variable
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        print("❌ Please set the AGENTBAY_API_KEY environment variable")
        return False
    
    print("🚀 File Transfer Example")
    print("=" * 50)
    
    # Initialize AgentBay client
    agentbay = AgentBay(api_key=api_key)
    print("✅ AgentBay client initialized")
    
    # Create a context for file operations
    context_name = f"file-transfer-example-{int(time.time())}"
    context_result = agentbay.context.get(context_name, create=True)
    if not context_result.success or not context_result.context:
        error_msg = getattr(context_result, 'error_message', 'Unknown error')
        print(f"❌ Failed to create context: {error_msg}")
        return False
    
    context = context_result.context
    print(f"✅ Context created: {context.id}")
    
    # Create browser session with context for testing
    browser_context = BrowserContext(
        context_id=context.id,
        auto_upload=True
    )

    session_params = CreateSessionParams(
        image_id="browser_latest",  # Use browser image for more comprehensive testing
        browser_context=browser_context
    )
    
    session_result = agentbay.create(session_params)
    if not session_result.success or not session_result.session:
        error_msg = getattr(session_result, 'error_message', 'Unknown error')
        print(f"❌ Failed to create session: {error_msg}")
        return False
    
    session = session_result.session
    print(f"✅ Session created: {session.get_session_id()}")
    
    # Initialize variables for cleanup
    local_file_path = None
    download_file_path = None
    
    try:
        # Create a test file to upload
        test_content = "Hello, AgentBay! This is a test file for file transfer operations.\n" * 10
        local_file_path = create_test_file(test_content, ".txt")
        print(f"✅ Created test file: {local_file_path}")
        
        # Upload the file using the simplified FileSystem API
        remote_path = "/tmp/file_transfer_test/upload_test.txt"
        print(f"\n📤 Uploading file to {remote_path}...")
        
        # Create test directory first
        print("Creating test directory...")
        create_dir_result = session.file_system.create_directory("/tmp/file_transfer_test/")
        if not create_dir_result.success:
            print(f"❌ Failed to create directory: {create_dir_result.error_message}")
            return False
        print("✅ Test directory created")
        
        upload_result = session.file_system.upload_file(
            local_path=local_file_path,
            remote_path=remote_path,
            wait=True,
            wait_timeout=60.0
        )
        
        if upload_result.success:
            print(f"✅ Upload successful!")
            print(f"   - Bytes sent: {upload_result.bytes_sent}")
            print(f"   - HTTP status: {upload_result.http_status}")
            print(f"   - Request ID: {upload_result.request_id_upload_url}")
        else:
            error_msg = getattr(upload_result, 'error', 'Unknown error')
            print(f"❌ Upload failed: {error_msg}")
            return False
        
        # Verify the file exists in the remote location
        list_result = session.file_system.list_directory("/tmp/file_transfer_test/")
        if list_result.success:
            file_found = any(entry.get('name') == 'upload_test.txt' for entry in list_result.entries)
            if file_found:
                print("✅ File verified in remote directory")
            else:
                print("⚠️  File not found in remote directory")
        else:
            error_msg = getattr(list_result, 'error_message', 'Unknown error')
            print(f"⚠️  Could not list remote directory: {error_msg}")
        
        # Create a local path for download
        download_file_path = local_file_path + ".downloaded"
        
        # Download the file using the simplified FileSystem API
        print(f"\n📥 Downloading file from {remote_path}...")
        download_result = session.file_system.download_file(
            remote_path=remote_path,
            local_path=download_file_path,
            wait=True,
            wait_timeout=60.0
        )
        
        if download_result.success:
            print(f"✅ Download successful!")
            print(f"   - Bytes received: {download_result.bytes_received}")
            print(f"   - HTTP status: {download_result.http_status}")
            print(f"   - Saved to: {download_result.local_path}")
            
            # Verify content matches
            with open(download_file_path, 'r') as f:
                downloaded_content = f.read()
            
            if downloaded_content == test_content:
                print("✅ Content verification successful!")
            else:
                print("❌ Content mismatch!")
                return False
        else:
            error_msg = getattr(download_result, 'error', 'Unknown error')
            print(f"❌ Download failed: {error_msg}")
            return False
            
        print("\n🎉 File transfer example completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during file transfer example: {e}")
        return False
    finally:
        # Clean up local files
        for path in [local_file_path, download_file_path]:
            if path and os.path.exists(path):
                os.unlink(path)
                print(f"🧹 Cleaned up local file: {path}")
        
        # Clean up resources
        print("\n🧹 Cleaning up...")
        try:
            delete_result = agentbay.delete(session, sync_context=True)
            if delete_result.success:
                print("✅ Session cleaned up successfully")
            else:
                print(f"⚠️  Session cleanup warning: {delete_result.error_message}")
        except Exception as e:
            print(f"⚠️  Error deleting session: {e}")
        
        try:
            agentbay.context.delete(context)
            print("✅ Context deleted")
        except Exception as e:
            print(f"⚠️  Error deleting context: {e}")


def file_transfer_with_progress_example():
    """Demonstrates file transfer with progress tracking."""
    
    # Get API key from environment variable
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        print("❌ Please set the AGENTBAY_API_KEY environment variable")
        return False
    
    print("\n🚀 File Transfer with Progress Tracking Example")
    print("=" * 50)
    
    # Initialize AgentBay client
    agentbay = AgentBay(api_key=api_key)
    print("✅ AgentBay client initialized")
    
    # Create a context for file operations
    context_name = f"file-transfer-progress-example-{int(time.time())}"
    context_result = agentbay.context.get(context_name, create=True)
    if not context_result.success or not context_result.context:
        error_msg = getattr(context_result, 'error_message', 'Unknown error')
        print(f"❌ Failed to create context: {error_msg}")
        return False
    
    context = context_result.context
    print(f"✅ Context created: {context.id}")
    
    # Create browser session with context for testing
    browser_context = BrowserContext(
        context_id=context.id,
        auto_upload=True
    )

    session_params = CreateSessionParams(
        image_id="browser_latest",  # Use browser image for more comprehensive testing
        browser_context=browser_context
    )
    
    session_result = agentbay.create(session_params)
    if not session_result.success or not session_result.session:
        error_msg = getattr(session_result, 'error_message', 'Unknown error')
        print(f"❌ Failed to create session: {error_msg}")
        return False
    
    session = session_result.session
    print(f"✅ Session created: {session.get_session_id()}")
    
    # Initialize variables for cleanup
    local_file_path = None
    download_file_path = None
    
    try:
        # Create a larger test file to demonstrate progress
        large_content = "This is a larger test file to demonstrate progress tracking.\n" * 1000
        local_file_path = create_test_file(large_content, ".txt")
        print(f"✅ Created large test file: {local_file_path} ({len(large_content)} bytes)")
        
        # Track upload progress
        upload_progress = []
        
        def upload_progress_callback(bytes_transferred):
            upload_progress.append(bytes_transferred)
            if len(upload_progress) % 10 == 1:  # Print every 10th update
                print(f"   📤 Upload progress: {bytes_transferred} bytes transferred")
        
        # Upload the file with progress tracking
        remote_path = "/tmp/file_transfer_test/large_test_file.txt"
        print(f"\n📤 Uploading large file to {remote_path} with progress tracking...")
        
        start_time = time.time()
        upload_result = session.file_system.upload_file(
            local_path=local_file_path,
            remote_path=remote_path,
            progress_cb=upload_progress_callback,
            wait=True,
            wait_timeout=120.0
        )
        end_time = time.time()
        
        if upload_result.success:
            print(f"✅ Upload successful!")
            print(f"   - Bytes sent: {upload_result.bytes_sent}")
            print(f"   - Time taken: {end_time - start_time:.2f} seconds")
            print(f"   - Progress updates: {len(upload_progress)}")
            if upload_progress:
                print(f"   - Final progress: {upload_progress[-1]} bytes")
        else:
            error_msg = getattr(upload_result, 'error', 'Unknown error')
            print(f"❌ Upload failed: {error_msg}")
            return False
        
        # Track download progress
        download_progress = []
        download_file_path = local_file_path + ".downloaded"
        
        def download_progress_callback(bytes_received):
            download_progress.append(bytes_received)
            if len(download_progress) % 10 == 1:  # Print every 10th update
                print(f"   📥 Download progress: {bytes_received} bytes received")
        
        # Download the file with progress tracking
        print(f"\n📥 Downloading file from {remote_path} with progress tracking...")
        
        start_time = time.time()
        download_result = session.file_system.download_file(
            remote_path=remote_path,
            local_path=download_file_path,
            progress_cb=download_progress_callback,
            wait=True,
            wait_timeout=120.0
        )
        end_time = time.time()
        
        if download_result.success:
            print(f"✅ Download successful!")
            print(f"   - Bytes received: {download_result.bytes_received}")
            print(f"   - Time taken: {end_time - start_time:.2f} seconds")
            print(f"   - Progress updates: {len(download_progress)}")
            if download_progress:
                print(f"   - Final progress: {download_progress[-1]} bytes")
            
            # Verify content matches
            with open(download_file_path, 'r') as f:
                downloaded_content = f.read()
            
            if downloaded_content == large_content:
                print("✅ Content verification successful!")
            else:
                print("❌ Content mismatch!")
                return False
        else:
            error_msg = getattr(download_result, 'error', 'Unknown error')
            print(f"❌ Download failed: {error_msg}")
            return False
            
        print("\n🎉 File transfer with progress example completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during file transfer with progress example: {e}")
        return False
    finally:
        # Clean up local files
        for path in [local_file_path, download_file_path]:
            if path and os.path.exists(path):
                os.unlink(path)
                print(f"🧹 Cleaned up local file: {path}")
        
        # Clean up resources
        print("\n🧹 Cleaning up...")
        try:
            delete_result = agentbay.delete(session, sync_context=True)
            if delete_result.success:
                print("✅ Session cleaned up successfully")
            else:
                print(f"⚠️  Session cleanup warning: {delete_result.error_message}")
        except Exception as e:
            print(f"⚠️  Error deleting session: {e}")
        
        try:
            agentbay.context.delete(context)
            print("✅ Context deleted")
        except Exception as e:
            print(f"⚠️  Error deleting context: {e}")


def main():
    """Main function to run all examples."""
    print("AgentBay File Transfer Examples")
    print("=" * 50)
    
    # Check API key
    if not os.getenv("AGENTBAY_API_KEY"):
        print("❌ Please set AGENTBAY_API_KEY environment variable")
        return
    
    # Run basic file transfer example
    success1 = file_transfer_example()
    
    # Run file transfer with progress tracking example
    success2 = file_transfer_with_progress_example()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 All examples completed successfully!")
    else:
        print("⚠️  Some examples encountered issues")


if __name__ == "__main__":
    main()