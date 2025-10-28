import os
import time
import unittest
from uuid import uuid4

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.context_sync import ContextSync


def get_test_api_key():
    """Get API key for testing"""
    return os.environ.get("AGENTBAY_API_KEY")


class TestDeleteIntegration(unittest.TestCase):
    """Integration test for session deletion functionality"""

    @classmethod
    def setUpClass(cls):
        # Get API Key
        api_key = get_test_api_key()
        if not api_key:
            raise unittest.SkipTest("AGENTBAY_API_KEY environment variable not set")

        # Initialize AgentBay client
        cls.agent_bay = AgentBay(api_key=api_key)

    def test_delete_without_params(self):
        """Test session deletion functionality without parameters"""
        # Create a session
        print("Creating session for parameter-less deletion test...")
        result = self.agent_bay.create()
        self.assertTrue(result.success)
        self.assertIsNotNone(result.session)
        session = result.session
        print(f"Session created successfully, ID: {session.session_id}")

        # Delete session using default parameters
        print("Deleting session using parameter-less delete method...")
        delete_result = session.delete()
        self.assertTrue(delete_result.success)
        print(f"Session deleted successfully (RequestID: {delete_result.request_id})")

        # Verify session has been deleted
        # Wait for a while to ensure deletion operation is completed
        time.sleep(2)
        
        # Use list_by_labels to get latest session list from server
        list_result = self.agent_bay.list_by_labels()
        self.assertTrue(list_result.success)
        
        # Check if session has been deleted
        self.assertNotIn(
            session.session_id,
            list_result.session_ids,
            f"Session ID {session.session_id} still exists after deletion",
        )

    def test_delete_with_sync_context(self):
        """Test session deletion functionality with sync_context parameter"""
        # Create context
        context_name = f"test-context-{uuid4().hex[:8]}"
        print(f"Creating context: {context_name}...")
        context_result = self.agent_bay.context.create(context_name)
        self.assertTrue(context_result.success)
        self.assertIsNotNone(context_result.context)
        context = context_result.context
        print(f"Context created successfully, ID: {context.id}")

        # Create persistence configuration
        persistence_data = [
            ContextSync(
                context_id=context.id,
                path="/home/wuying/test"
            )
        ]

        # Create session with context
        params = CreateSessionParams(
            image_id="linux_latest",
            context_syncs=persistence_data
        )

        print("Creating session with context...")
        result = self.agent_bay.create(params)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.session)
        session = result.session
        print(f"Session created successfully, ID: {session.session_id}")

        # Create test file in session
        test_cmd = "echo 'test file content' > /home/wuying/test/testfile.txt"
        try:
            cmd_result = session.command.execute_command(test_cmd)
            print(f"Create test file: {cmd_result}")
        except Exception as e:
            print(f"Warning: Failed to create test file: {e}")

        # Delete session using sync_context=True
        print("Deleting session using sync_context=True...")
        delete_result = session.delete(sync_context=True)
        self.assertTrue(delete_result.success)
        print(f"Session deleted successfully (RequestID: {delete_result.request_id})")

        # Verify session has been deleted
        # Wait for a while to ensure deletion operation is completed
        time.sleep(2)
        
        # Use list_by_labels to get latest session list from server
        list_result = self.agent_bay.list_by_labels()
        self.assertTrue(list_result.success)
        
        # Check if session has been deleted
        self.assertNotIn(
            session.session_id,
            list_result.session_ids,
            f"Session ID {session.session_id} still exists after deletion",
        )

        # Clean up context
        try:
            delete_context_result = self.agent_bay.context.delete(context)
            if delete_context_result.success:
                print(f"Context {context.id} deleted")
            else:
                print(f"Warning: Failed to delete context")
        except Exception as e:
            print(f"Warning: Error deleting context: {e}")

    def test_agentbay_delete_with_sync_context(self):
        """Test AgentBay.delete functionality with sync_context parameter"""
        # Create context
        context_name = f"test-context-{uuid4().hex[:8]}"
        print(f"Creating context: {context_name}...")
        context_result = self.agent_bay.context.create(context_name)
        self.assertTrue(context_result.success)
        self.assertIsNotNone(context_result.context)
        context = context_result.context
        print(f"Context created successfully, ID: {context.id}")

        # Create persistence configuration
        persistence_data = [
            ContextSync(
                context_id=context.id,
                path="/home/wuying/test2"
            )
        ]

        # Create session with context
        params = CreateSessionParams(
            image_id="linux_latest",
            context_syncs=persistence_data
        )

        print("Creating session with context...")
        result = self.agent_bay.create(params)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.session)
        session = result.session
        print(f"Session created successfully, ID: {session.session_id}")

        # Create test file in session
        test_cmd = "echo 'test file for agentbay delete' > /home/wuying/test2/testfile2.txt"
        try:
            cmd_result = session.command.execute_command(test_cmd)
            print(f"Create test file: {cmd_result}")
        except Exception as e:
            print(f"Warning: Failed to create test file: {e}")

        # Delete session using agent_bay.delete with sync_context=True
        print("Deleting session using agent_bay.delete with sync_context=True...")
        delete_result = self.agent_bay.delete(session, sync_context=True)
        self.assertTrue(delete_result.success)
        print(f"Session deleted successfully (RequestID: {delete_result.request_id})")

        # Verify session has been deleted
        # Wait for a while to ensure deletion operation is completed
        time.sleep(2)
        
        # Use list_by_labels to get latest session list from server
        list_result = self.agent_bay.list_by_labels()
        self.assertTrue(list_result.success)
        
        # Check if session has been deleted
        self.assertNotIn(
            session.session_id,
            list_result.session_ids,
            f"Session ID {session.session_id} still exists after deletion",
        )

        # Clean up context
        try:
            delete_context_result = self.agent_bay.context.delete(context)
            if delete_context_result.success:
                print(f"Context {context.id} deleted")
            else:
                print(f"Warning: Failed to delete context")
        except Exception as e:
            print(f"Warning: Error deleting context: {e}")


if __name__ == "__main__":
    unittest.main()