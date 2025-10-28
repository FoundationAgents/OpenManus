import unittest
from unittest.mock import MagicMock, patch

from agentbay.agent import Agent, ExecutionResult
from agentbay.model import OperationResult
import os


class DummySession:
    def __init__(self):
        self.api_key = "dummy_key"
        self.session_id = "dummy_session"
        self.client = MagicMock()

    def get_api_key(self):
        return self.api_key

    def get_session_id(self):
        return self.session_id

    def get_client(self):
        return self.client


class TestAgent(unittest.TestCase):
    def setUp(self):
        self.session = DummySession()
        self.agent = Agent(self.session)
        self.max_try_times = os.environ.get("AGENT_TASK_TIMEOUT")
        if not self.max_try_times:
            self.max_try_times = 200
            print("we will  for 200 * 3 seconds to finish.")

    @patch("agentbay.agent.Agent._call_mcp_tool")
    def test_task_execute_success(self, mock_call_mcp_tool):
        """
        Test flux_execute_task method with successful response.
        """
        mock_result = OperationResult(
            request_id="request-123",
            success=True,
            data="""{"task_id": "task-123", "status": "finished", "result":"", "product": "Task completed successfully"}""",
        )
        mock_call_mcp_tool.return_value = mock_result

        result = self.agent.execute_task("Say hello", int(self.max_try_times))
        self.assertIsInstance(result, ExecutionResult)
        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "request-123")
        self.assertEqual(result.task_status, "finished")
        self.assertEqual(result.error_message, "")

        # Verify call arguments
        self.assertEqual(mock_call_mcp_tool.call_count, 2)
        args = mock_call_mcp_tool.call_args[0][1]
        self.assertEqual(args["task_id"], "task-123")

    @patch("agentbay.agent.Agent._call_mcp_tool")
    def test_execute_task_error(self, mock_call_mcp_tool):
        """
        Test execute_task method with error response.
        """
        mock_result = OperationResult(
            request_id="request-123",
            success=False,
            error_message="Task execution failed",
            data="""{"task_id": "task-123", "status": "failed", "result":"", "product": "Task Failed"}""",
        )
        mock_call_mcp_tool.return_value = mock_result
        result = self.agent.execute_task("Say hello", self.max_try_times)
        self.assertIsInstance(result, ExecutionResult)
        self.assertFalse(result.success)
        self.assertEqual(result.request_id, "request-123")
        self.assertEqual(result.error_message, "Task execution failed")
        self.assertEqual(result.task_status, "failed")
        args = mock_call_mcp_tool.call_args[0][1]
        self.assertEqual(args["task"], "Say hello")

    @patch("agentbay.agent.Agent._call_mcp_tool")
    def test_task_terminate_success(self, mock_call_mcp_tool):
        """
        Test terminate_task method with successful response.
        """
        mock_result = OperationResult(
            request_id="request-123",
            success=True,
            data="""{"task_id": "task-123", "status": "finished", "result":"", "product": "Task completed successfully"}""",
        )
        mock_call_mcp_tool.return_value = mock_result

        result = self.agent.terminate_task("task-123")
        self.assertIsInstance(result, ExecutionResult)
        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "request-123")
        self.assertEqual(result.task_status, "finished")
        self.assertEqual(result.error_message, "")

        # Verify call arguments
        mock_call_mcp_tool.assert_called_once()
        args = mock_call_mcp_tool.call_args[0][1]
        self.assertEqual(args["task_id"], "task-123")

    @patch("agentbay.agent.Agent._call_mcp_tool")
    def test_task_terminate_error(self, mock_call_mcp_tool):
        """
        Test terminate_task method with successful response.
        """
        mock_result = OperationResult(
            request_id="request-123",
            success=False,
            data="""{"task_id": "task-123", "status": "failed", "result":"", "product": "Task Failed"}""",
        )
        mock_call_mcp_tool.return_value = mock_result

        result = self.agent.terminate_task("task-123")
        self.assertIsInstance(result, ExecutionResult)
        self.assertFalse(result.success)
        self.assertEqual(result.request_id, "request-123")
        self.assertEqual(result.task_status, "failed")

        # Verify call arguments
        mock_call_mcp_tool.assert_called_once()
        args = mock_call_mcp_tool.call_args[0][1]
        print(f"args = {mock_call_mcp_tool.call_args}")
        self.assertEqual(args["task_id"], "task-123")


if __name__ == "__main__":
    unittest.main()
