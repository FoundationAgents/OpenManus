import os
import time
import unittest

from agentbay import AgentBay
from agentbay.agent import Agent
from agentbay.session_params import CreateSessionParams


class TestAgentIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Set up the test environment by creating a session and initializing task.
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
            image_id="waic-playground-demo-windows",
        )
        session_result = cls.agent_bay.create(params)
        if not session_result.success or not session_result.session:
            raise unittest.SkipTest("Failed to create session")

        cls.session = session_result.session
        cls.agent = cls.session.agent

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

    def test_execute_task_success(self):
        """
        Test executing a flux task successfully.
        """

        task = "create a folder named 'agentbay' in C:\\Window\\Temp"
        max_try_times = os.environ.get("AGENT_TASK_TIMEOUT")
        if not max_try_times:
            max_try_times = 300
            print("we will  for 200 * 3 seconds to finish.")

        result = self.agent.execute_task(task, int(max_try_times))
        self.assertTrue(result.success)
        self.assertNotEqual(result.request_id, "")
        self.assertEqual(result.error_message, "")


if __name__ == "__main__":
    unittest.main()
