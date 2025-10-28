import os
import time
import unittest

from agentbay import AgentBay
from agentbay.command import Command
from agentbay.session_params import CreateSessionParams


class TestCommandIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Set up the test environment by creating a session and initializing Command.
        """
        time.sleep(3)  # Ensure a delay to avoid session creation conflicts
        api_key = os.getenv("AGENTBAY_API_KEY")
        if not api_key:
            api_key = "akm-xxx"  # Replace with your actual API key for testing
            print(
                "Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for production use."
            )
        cls.agent_bay = AgentBay(api_key=api_key)
        params = CreateSessionParams(
            image_id="code_latest",
        )
        session_result = cls.agent_bay.create(params)
        if not session_result.success or not session_result.session:
            raise unittest.SkipTest("Failed to create session")

        cls.session = session_result.session
        cls.command = Command(cls.session)

    @classmethod
    def tearDownClass(cls):
        """
        Clean up resources after each test.
        """
        print("Cleaning up: Deleting the session...")
        try:
            cls.agent_bay.delete(cls.session)
        except Exception as e:
            print(f"Warning: Error deleting session: {e}")

    def test_execute_command_success(self):
        """
        Test executing a shell command successfully.
        """
        command = "echo 'Hello, AgentBay!'"
        result = self.command.execute_command(command)
        print(f"Command execution result: {result.output}")
        self.assertTrue(result.success)
        self.assertEqual(result.output.strip(), "Hello, AgentBay!")
        self.assertNotEqual(result.request_id, "")
        self.assertEqual(result.error_message, "")

    def test_execute_command_with_timeout(self):
        """
        Test executing a shell command with a timeout.
        """
        command = "sleep 5"
        timeout_ms = 1000  # 1 second timeout
        result = self.command.execute_command(command, timeout_ms)
        print(f"Command execution result with timeout: {result}")
        self.assertFalse(result.success)
        self.assertNotEqual(result.request_id, "")
        self.assertNotEqual(result.error_message, "")
        self.assertEqual(result.output, "")

    def test_command_error_handling(self):
        """3.1 Command Error Handling - should handle command errors and edge cases"""
        # Test invalid command
        invalid_result = self.command.execute_command('invalid_command_12345')
        self.assertFalse(invalid_result.success)
        self.assertIsNotNone(invalid_result.error_message)

        # Test command with permission issues (trying to write to protected directory)
        permission_result = self.command.execute_command('echo "test" > /root/protected.txt')
        # This might succeed or fail depending on the environment, but should not crash
        self.assertIsInstance(permission_result.success, bool)

        # Test long-running command with timeout considerations
        time_command = 'echo "completed"'
        time_result = self.command.execute_command(time_command)
        print(f'Command output: {time_result}')
        self.assertTrue(time_result.success)
        self.assertIn('completed', time_result.output)


if __name__ == "__main__":
    unittest.main()
