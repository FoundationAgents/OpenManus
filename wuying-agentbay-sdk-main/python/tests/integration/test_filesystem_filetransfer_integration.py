"""
Integration tests for the FileTransfer functionality.
These tests verify the complete functionality of the FileTransfer class
with real sessions and actual file transfers.
"""

import os
import unittest
import time
import tempfile
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams, BrowserContext


class TestFileTransferIntegration(unittest.TestCase):
    """Integration tests for FileTransfer class with real sessions."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment before all tests."""
        # Get API key from environment
        cls.api_key = os.getenv("AGENTBAY_API_KEY")
        if not cls.api_key:
            raise unittest.SkipTest("AGENTBAY_API_KEY environment variable not set")

        # Initialize AgentBay client
        cls.agent_bay = AgentBay(cls.api_key)

        # Create a unique context for testing
        context_name = f"file-transfer-test-{int(time.time())}"
        context_result = cls.agent_bay.context.get(context_name, create=True)
        if not context_result.success or not context_result.context:
            raise unittest.SkipTest("Failed to create context")

        cls.context = context_result.context
        print(f"Context created with ID: {cls.context.id}")

        # Create browser session with context for testing
        browser_context = BrowserContext(
            context_id=cls.context.id,
            auto_upload=True
        )

        params = CreateSessionParams(
            image_id="browser_latest",  # Use browser image for more comprehensive testing
            browser_context=browser_context
        )

        session_result = cls.agent_bay.create(params)
        if not session_result.success or not session_result.session:
            raise unittest.SkipTest("Failed to create session")

        cls.session = session_result.session
        print(f"Browser session created with ID: {cls.session.get_session_id()}")

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment after all tests."""
        print("Cleaning up: Deleting the session...")
        if hasattr(cls, "session"):
            try:
                # Delete session with context synchronization
                result = cls.agent_bay.delete(cls.session, sync_context=True)
                if result.success:
                    print("Session successfully deleted with context sync")
                else:
                    print(f"Warning: Error deleting session: {result.error_message}")
            except Exception as e:
                print(f"Warning: Error deleting session: {e}")

        # Clean up context
        if hasattr(cls, "context"):
            try:
                cls.agent_bay.context.delete(cls.context)
                print("Context successfully deleted")
            except Exception as e:
                print(f"Warning: Error deleting context: {e}")

    def setUp(self):
        """Set up before each test."""
        pass

    def test_file_upload_integration(self):
        """Test complete file upload workflow with real session and verification."""
        print("Testing file upload...")
        # Create a temporary file for upload
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
            test_content = "This is a test file for AgentBay FileTransfer upload integration test.\n" * 10
            temp_file.write(test_content)
            temp_file_path = temp_file.name

        try:
            # Upload the file
            remote_path = "/tmp/file_transfer_test/upload_test.txt"
            upload_result = self.session.file_system.upload_file(
                local_path=temp_file_path,
                remote_path=remote_path,
            )

            # Verify upload result
            self.assertTrue(upload_result.success, f"Upload failed: {upload_result.error}")
            self.assertGreater(upload_result.bytes_sent, 0)
            self.assertIsNotNone(upload_result.request_id_upload_url)
            self.assertIsNotNone(upload_result.request_id_sync)


            ls_result = self.session.command.execute_command("ls -la /tmp/file_transfer_test/")
            if not ls_result.success:
                print("    ❌ fileTransfer directory not found")
                return False

            print(f"    ✅ fileTransfer directory exists: /tmp/file_transfer_test/")
            print(f"    Directory content:\n{ls_result.output}")

            # Verify file exists in remote location by listing directory
            list_result = self.session.file_system.list_directory("/tmp/file_transfer_test/")
            self.assertTrue(list_result.success, f"Failed to list directory: {list_result.error_message}")
            
            # Check if our uploaded file is in the directory listing
            file_found = False
            for entry in list_result.entries:
                if entry.get('name') == 'upload_test.txt':
                    file_found = True
                    break
            
            self.assertTrue(file_found, "Uploaded file not found in remote directory")

            # Verify file content by reading it back
            read_result = self.session.file_system.read_file(remote_path)
            self.assertTrue(read_result.success, f"Failed to read uploaded file: {read_result.error_message}")
            self.assertEqual(read_result.content, test_content)

        finally:
            # Clean up local temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_file_download_integration(self):
        """Test complete file download workflow with real session and verification."""
        # First, create a file in the remote location
        remote_path = "/tmp/file_transfer_test/download_test.txt"
        test_content = "This is a test file for AgentBay FileTransfer download integration test.\n" * 15
        print("\n Creating test directory...")
        create_dir_result = self.session.file_system.create_directory("/tmp/file_transfer_test/")
        print(f"Create directory result: {create_dir_result.success}")
        self.assertTrue(create_dir_result.success)
        write_result = self.session.file_system.write_file(remote_path, test_content)
        self.assertTrue(write_result.success, f"Failed to create remote file: {write_result.error_message}")

        ls_result = self.session.command.execute_command("ls -la /tmp/file_transfer_test/")
        if not ls_result.success:
            print("    ❌ fileTransfer directory not found")
            return False

        print(f"    ✅ fileTransfer directory exists: /tmp/file_transfer_test/")
        print(f"    Directory content:\n{ls_result.output}")
        # Create a temporary file path for download
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
            temp_file_path = temp_file.name

        try:
            # Download the file
            download_result = self.session.file_system.download_file(
                remote_path=remote_path,
                local_path=temp_file_path,
            )

            # Verify download result
            self.assertTrue(download_result.success, f"Download failed: {download_result.error}")
            self.assertGreater(download_result.bytes_received, 0)
            self.assertIsNotNone(download_result.request_id_download_url)
            self.assertIsNotNone(download_result.request_id_sync)
            self.assertEqual(download_result.local_path, temp_file_path)

            # Verify downloaded file content
            with open(temp_file_path, 'r') as f:
                downloaded_content = f.read()
            
            print(f"Downloaded file content length: {len(downloaded_content)} bytes")
            self.assertEqual(downloaded_content, test_content)

        finally:
            # Clean up temporary files
            for path in [temp_file_path]:
                if os.path.exists(path):
                    print(f"Deleting temporary file: {path}")
                    os.unlink(path)
if __name__ == '__main__':
    unittest.main()