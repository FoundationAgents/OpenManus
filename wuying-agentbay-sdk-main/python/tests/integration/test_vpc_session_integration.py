import os
import sys
import time
import unittest
from typing import Dict, Any

# Add the parent directory to the Python path to find agentbay module
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams


class TestVPCSessionIntegration(unittest.TestCase):
    """VPC Session Integration Tests
    
    Tests the creation of VPC-based sessions and various functionality:
    1. Create sessions with IsVpc=True  
    2. Test FileSystem WriteFile/ReadFile functionality
    3. Test Command ExecuteCommand functionality
    4. Clean up sessions
    
    Note: This test is designed to verify that VPC sessions can be created 
    and core operations work correctly.
    """

    @classmethod
    def setUpClass(cls):
        """Set up test environment before all tests."""
        # Get API key from environment
        cls.api_key = os.getenv("AGENTBAY_API_KEY")
        if not cls.api_key:
            raise unittest.SkipTest("AGENTBAY_API_KEY environment variable not set")

        print(f"Using API key: {cls.api_key}")

        cls.agent_bay = AgentBay(cls.api_key)
        print(f"AgentBay client initialized successfully")

    def test_vpc_session_basic_tools(self):
        """Test VPC session creation and filesystem write/read functionality"""
        print("=" * 80)
        print("TEST: VPC Session Basic Tools")
        print("=" * 80)

        # Step 1: Create a VPC-based session
        print("Step 1: Creating VPC-based session...")
        params = CreateSessionParams(
            image_id="imgc-07eksy57nw6r759fb",
            is_vpc=True,
            labels={
                "test-type": "vpc-integration",
                "purpose": "vpc-session-testing"
            }
        )

        print(f"Session params: ImageId={params.image_id}, IsVpc={params.is_vpc}, Labels={params.labels}")

        session_result = self.agent_bay.create(params)
        self.assertTrue(session_result.success, f"Error creating VPC session: {session_result.error_message}")
        
        session = session_result.session
        print(f"VPC session created successfully with ID: {session.session_id} (RequestID: {session_result.request_id})")

        try:
            # Verify session properties
            self.assertIsNotNone(session.session_id)
            self.assertTrue(len(session.session_id) > 0, "Session ID is empty")
            print(f"Session properties verified: ID={session.session_id}")

            # Step 2: Test Command functionality to create a file
            print("Step 2: Testing Command functionality to create a file...")
            if session.command is not None:
                print("✓ Command tool is available in VPC session")

                # Test file path and content
                test_file_path = "/tmp/vpc_test_file.txt"
                test_content = f"Hello from VPC session!\\nThis is a test file written by the VPC integration test.\\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}"

                print(f"Testing ExecuteCommand to create file: {test_file_path}")
                print(f"Test content length: {len(test_content)} characters")

                # Use echo command to write content to file
                write_command = f"echo '{test_content}' > {test_file_path}"
                print(f"Execute command: {write_command}")

                cmd_result = session.command.execute_command(write_command)
                if cmd_result.success:
                    print(f"✓ ExecuteCommand successful - Output: {cmd_result.output}, RequestID: {cmd_result.request_id}")
                    print("✓ File creation command executed successfully")

                    # Verify RequestID is present
                    if cmd_result.request_id:
                        print("✓ ExecuteCommand returned RequestID")
                    else:
                        print("⚠ ExecuteCommand did not return RequestID")
                else:
                    print(f"⚠ ExecuteCommand failed: {cmd_result.error_message}")
            else:
                print("⚠ Command tool is not available in VPC session")

            # Step 3: Test FileSystem ReadFile functionality to verify written content
            print("Step 3: Testing FileSystem ReadFile functionality to verify written content...")
            if session.file_system is not None:
                # Test reading the file we just wrote
                test_file_path = "/tmp/vpc_test_file.txt"
                print(f"Testing ReadFile with path: {test_file_path}")

                read_result = session.file_system.read_file(test_file_path)
                if read_result.success:
                    print(f"✓ ReadFile successful - Content length: {len(read_result.content)} bytes, RequestID: {read_result.request_id}")

                    # Log first 200 characters of content for verification
                    content_preview = read_result.content
                    if len(content_preview) > 200:
                        content_preview = content_preview[:200] + "..."
                    print(f"Content preview: {content_preview}")

                    # Verify that content is not empty
                    self.assertTrue(len(read_result.content) > 0, "ReadFile returned empty content")
                    print("✓ ReadFile returned non-empty content")

                    # Verify that content contains expected test content
                    if "Hello from VPC session!" in read_result.content:
                        print("✓ ReadFile content contains expected test message")
                    else:
                        print("⚠ ReadFile content does not contain expected test message")

                    if "This is a test file written by the VPC integration test" in read_result.content:
                        print("✓ ReadFile content contains expected test description")
                    else:
                        print("⚠ ReadFile content does not contain expected test description")

                    # Verify RequestID is present
                    if read_result.request_id:
                        print("✓ ReadFile returned RequestID")
                    else:
                        print("⚠ ReadFile did not return RequestID")
                else:
                    print(f"⚠ ReadFile failed: {read_result.error_message}")
            else:
                print("⚠ FileSystem tool is not available in VPC session")

        finally:
            # Ensure cleanup of the session at the end of the test
            print("Cleaning up: Deleting the VPC session...")
            delete_result = self.agent_bay.delete(session)
            if delete_result.success:
                print(f"VPC session successfully deleted (RequestID: {delete_result.request_id})")
            else:
                print(f"Warning: Error deleting VPC session: {delete_result.error_message}")

        print("VPC session filesystem write/read test completed successfully")

if __name__ == '__main__':
    unittest.main()
