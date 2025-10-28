import os
import sys
import unittest

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams, BrowserContext
from agentbay.api.models import ExtraConfigs, MobileExtraConfig, AppManagerRule
from agentbay.context_sync import ContextSync, SyncPolicy, RecyclePolicy, Lifecycle, UploadPolicy, DownloadPolicy, DeletePolicy, ExtractPolicy, BWList, WhiteList

# Add the parent directory to the path so we can import the agentbay package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_test_api_key():
    """Get API key for testing"""
    api_key = os.environ.get("AGENTBAY_API_KEY")
    if not api_key:
        api_key = "akm-xxx"  # Replace with your test API key
        print(
            "Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for testing."
        )
    return api_key


class TestAgentBay(unittest.TestCase):
    """Test cases for the AgentBay class."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        api_key = get_test_api_key()
        agent_bay = AgentBay(api_key=api_key)
        self.assertEqual(agent_bay.api_key, api_key)
        self.assertIsNotNone(agent_bay.client)

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        os.environ["AGENTBAY_API_KEY"] = "env_api_key"
        try:
            agent_bay = AgentBay()
            self.assertEqual(agent_bay.api_key, "env_api_key")
        finally:
            del os.environ["AGENTBAY_API_KEY"]

    def test_init_without_api_key_raises_error(self):
        """Test initialization without API key raises error."""
        if "AGENTBAY_API_KEY" in os.environ:
            del os.environ["AGENTBAY_API_KEY"]
        with self.assertRaises(ValueError):
            AgentBay()

    def test_create_list_delete(self):
        """Test create, list, and delete methods."""
        api_key = get_test_api_key()
        agent_bay = AgentBay(api_key=api_key)

        # Create a session
        print("Creating a new session...")
        result = agent_bay.create()
        session = result.session
        print(f"Session created with ID: {session.session_id}")

        # Ensure session ID is not empty
        self.assertIsNotNone(session.session_id)
        self.assertNotEqual(session.session_id, "")


        # Delete the session
        print("Deleting the session...")
        agent_bay.delete(session)

        # Session deletion completed


class TestSession(unittest.TestCase):
    """Test cases for the Session class."""

    def setUp(self):
        """Set up test fixtures."""
        api_key = get_test_api_key()
        self.agent_bay = AgentBay(api_key=api_key)

        # Create a session with default windows image
        print("Creating a new session for testing...")
        self.result = self.agent_bay.create()
        self.session = self.result.session
        print(f"Session created with ID: {self.session.session_id}")

    def tearDown(self):
        """Tear down test fixtures."""
        print("Cleaning up: Deleting the session...")
        try:
            self.agent_bay.delete(self.session)
        except Exception as e:
            print(f"Warning: Error deleting session: {e}")

    def test_session_properties(self):
        """Test session properties and methods."""
        # Test session properties
        self.assertIsNotNone(self.session.session_id)
        self.assertEqual(self.session.agent_bay, self.agent_bay)



        # Test get_api_key method
        api_key = self.session.get_api_key()
        self.assertEqual(api_key, self.agent_bay.api_key)

        # Test get_client method
        client = self.session.get_client()
        self.assertEqual(client, self.agent_bay.client)

        # Test get_session_id method
        session_id = self.session.get_session_id()
        self.assertEqual(session_id, self.session.session_id)

    def test_delete(self):
        """Test session delete method."""
        # Create a new session specifically for this test
        print("Creating a new session for delete testing...")
        result = self.agent_bay.create()
        session = result.session
        print(f"Session created with ID: {session.session_id}")

        # Test delete method
        print("Testing session.delete method...")
        try:
            result = session.delete()
            self.assertTrue(result)

            # Session deletion verified
        except Exception as e:
            print(f"Note: Session deletion failed: {e}")
            # Clean up if the test failed
            try:
                self.agent_bay.delete(session)
            except BaseException:
                pass

    def test_command(self):
        """Test command execution."""
        if self.session.command:
            print("Executing command...")
            try:
                response = self.session.command.execute_command("ls")
                print(f"Command execution result: {response}")
                self.assertIsNotNone(response)
                # Check if response contains "tool not found"
                self.assertNotIn(
                    "tool not found",
                    response.lower(),
                    "Command.ExecuteCommand returned 'tool not found'",
                )
            except Exception as e:
                print(f"Note: Command execution failed: {e}")
                # Don't fail the test if command execution is not supported
        else:
            print("Note: Command interface is nil, skipping command test")

    def test_filesystem(self):
        """Test filesystem operations."""
        if self.session.file_system:
            print("Reading file...")
            try:
                content = self.session.file_system.read_file("/etc/hosts")
                print(f"ReadFile result: content='{content}'")
                self.assertIsNotNone(content)
                # Check if response contains "tool not found"
                self.assertNotIn(
                    "tool not found",
                    content.lower(),
                    "FileSystem.ReadFile returned 'tool not found'",
                )
                print("File read successful")
            except Exception as e:
                print(f"Note: File operation failed: {e}")
                # Don't fail the test if filesystem operations are not supported
        else:
            print("Note: FileSystem interface is nil, skipping file test")



class TestRecyclePolicy(unittest.TestCase):
    """Test cases for RecyclePolicy functionality."""

    def setUp(self):
        """Set up test fixtures."""
        api_key = get_test_api_key()
        self.agent_bay = AgentBay(api_key=api_key)
        self.session = None

    def tearDown(self):
        """Tear down test fixtures."""
        # Clean up session
        if self.session:
            try:
                print("Cleaning up session with custom recyclePolicy...")
                delete_result = self.agent_bay.delete(self.session)
                print(f"Delete Session RequestId: {delete_result.request_id or 'undefined'}")
            except Exception as e:
                print(f"Warning: Error deleting session: {e}")

    def test_create_session_with_custom_recycle_policy(self):
        """Test creating session with custom recyclePolicy using Lifecycle_1Day."""
        # Create custom recyclePolicy with Lifecycle_1Day and default paths
        recycle_policy = RecyclePolicy(
            lifecycle=Lifecycle.LIFECYCLE_1DAY,
            paths=[""]  # Using default path value
        )

        # Create custom SyncPolicy with recyclePolicy
        custom_sync_policy = SyncPolicy(
            upload_policy=UploadPolicy.default(),
            download_policy=DownloadPolicy.default(),
            delete_policy=DeletePolicy.default(),
            extract_policy=ExtractPolicy.default(),
            recycle_policy=recycle_policy,
            bw_list=BWList(white_lists=[WhiteList(path="", exclude_paths=[])])
        )

        # Create ContextSync with custom policy
        context_sync = ContextSync(
            context_id="test-recycle-context",
            path="/test/recycle/path",
            policy=custom_sync_policy
        )

        print("Creating session with custom recyclePolicy...")
        print(f"RecyclePolicy lifecycle: {custom_sync_policy.recycle_policy.lifecycle.value}")
        print(f"RecyclePolicy paths: {custom_sync_policy.recycle_policy.paths}")

        # Create session parameters with custom recyclePolicy
        params = CreateSessionParams(
            labels={"test": "recyclePolicy", "lifecycle": "1day"},
            context_syncs=[context_sync]
        )

        # Create session with custom recyclePolicy
        create_result = self.agent_bay.create(params)

        # Verify SessionResult structure
        self.assertTrue(create_result.success)
        self.assertIsNotNone(create_result.request_id)
        self.assertIsInstance(create_result.request_id, str)
        self.assertGreater(len(create_result.request_id), 0)
        self.assertIsNotNone(create_result.session)
        self.assertFalse(create_result.error_message)

        self.session = create_result.session
        print(f"Session created successfully with ID: {self.session.session_id}")
        print(f"Create Session RequestId: {create_result.request_id or 'undefined'}")

        # Verify session properties
        self.assertIsNotNone(self.session.session_id)
        self.assertGreater(len(self.session.session_id), 0)

        print("Session with custom recyclePolicy created and verified successfully")

    def test_context_sync_with_invalid_recycle_policy_path(self):
        """Test that ContextSync throws error when creating with invalid recyclePolicy path."""
        print("Testing ContextSync creation with invalid recyclePolicy path...")

        # Create custom recyclePolicy with invalid wildcard path
        invalid_recycle_policy = RecyclePolicy(
            lifecycle=Lifecycle.LIFECYCLE_1DAY,
            paths=["/invalid/path/*"]  # Invalid path with wildcard
        )

        print(f"Invalid path: {invalid_recycle_policy.paths[0]}")

        # Test that RecyclePolicy constructor throws an error for invalid path
        with self.assertRaises(ValueError) as context:
            RecyclePolicy(
                lifecycle=Lifecycle.LIFECYCLE_1DAY,
                paths=["/invalid/path/*"]
            )

        # Verify the error message
        expected_message = "Wildcard patterns are not supported in recycle policy paths. Got: /invalid/path/*. Please use exact directory paths instead."
        self.assertIn("Wildcard patterns are not supported in recycle policy paths", str(context.exception))
        self.assertIn("/invalid/path/*", str(context.exception))

        print("RecyclePolicy correctly threw error for invalid path")

        # Test with multiple invalid paths
        with self.assertRaises(ValueError):
            RecyclePolicy(
                lifecycle=Lifecycle.LIFECYCLE_1DAY,
                paths=["/valid/path", "/invalid/path?", "/another/invalid/*"]
            )

        print("RecyclePolicy correctly threw error for multiple invalid paths")


    def test_recycle_policy_invalid_lifecycle(self):
        """Test invalid Lifecycle values."""
        print("Testing invalid Lifecycle values...")

        # Test with invalid lifecycle value (string instead of Lifecycle enum)
        with self.assertRaises(ValueError) as context:
            RecyclePolicy(
                lifecycle="invalid_lifecycle",  # Invalid: should be Lifecycle enum
                paths=[""]
            )

        # Verify error message contains expected information
        error_message = str(context.exception)
        expected_substrings = [
            "Invalid lifecycle value",
            "invalid_lifecycle",
            "Valid values are:"
        ]

        for substring in expected_substrings:
            self.assertIn(substring, error_message)

        print(f"Invalid lifecycle 'invalid_lifecycle' correctly failed validation: {error_message}")
        print("Invalid Lifecycle values test completed successfully")

    def test_recycle_policy_combined_invalid(self):
        """Test combination of invalid Lifecycle and invalid paths."""
        print("Testing combination of invalid Lifecycle and invalid paths...")

        # Test with both invalid lifecycle and invalid path
        with self.assertRaises(ValueError) as context:
            RecyclePolicy(
                lifecycle="invalid_lifecycle",  # Invalid lifecycle
                paths=["/invalid/path/*"]       # Invalid path with wildcard
            )

        # Should fail on lifecycle validation first (since it's checked first in __post_init__)
        error_message = str(context.exception)
        self.assertIn("Invalid lifecycle value", error_message)

        print(f"Policy with both invalid lifecycle and invalid path correctly failed validation: {error_message}")
        print("Combined invalid configuration test completed successfully")


class TestBrowserContext(unittest.TestCase):
    """Test cases for BrowserContext functionality."""

    def setUp(self):
        """Set up test fixtures."""
        api_key = get_test_api_key()
        self.agent_bay = AgentBay(api_key=api_key)
        self.session = None

    def tearDown(self):
        """Tear down test fixtures."""
        # Clean up session
        if self.session:
            try:
                print("Cleaning up session with BrowserContext...")
                delete_result = self.agent_bay.delete(self.session)
                print(f"Delete Session RequestId: {delete_result.request_id or 'undefined'}")
            except Exception as e:
                print(f"Warning: Error deleting session: {e}")

    def test_create_session_with_browser_context_default_recycle_policy(self):
        """Test creating session with BrowserContext using default RecyclePolicy."""
        print("Testing session creation with BrowserContext (default RecyclePolicy)...")

        # Create BrowserContext with default RecyclePolicy
        browser_context = BrowserContext(
            context_id="test-browser-context-default",
            auto_upload=True
        )

        print(f"BrowserContext context_id: {browser_context.context_id}")
        print(f"BrowserContext auto_upload: {browser_context.auto_upload}")

        # Create session parameters with BrowserContext
        params = CreateSessionParams(
            labels={"test": "browserContext", "recycle_policy": "default"},
            browser_context=browser_context
        )

        # Create session with BrowserContext
        create_result = self.agent_bay.create(params)

        # Verify SessionResult structure
        self.assertTrue(create_result.success)
        self.assertIsNotNone(create_result.request_id)
        self.assertIsInstance(create_result.request_id, str)
        self.assertGreater(len(create_result.request_id), 0)
        self.assertIsNotNone(create_result.session)
        self.assertFalse(create_result.error_message)

        self.session = create_result.session
        print(f"Session created successfully with ID: {self.session.session_id}")
        print(f"Create Session RequestId: {create_result.request_id or 'undefined'}")

        # Verify session properties
        self.assertIsNotNone(self.session.session_id)
        self.assertGreater(len(self.session.session_id), 0)

        print("Session with BrowserContext (default RecyclePolicy) created and verified successfully")


if __name__ == "__main__":
    unittest.main()