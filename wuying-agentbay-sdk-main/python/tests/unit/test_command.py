import unittest
from unittest.mock import MagicMock, patch

from agentbay.command.command import Command, CommandResult
from agentbay.model import OperationResult


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


class TestCommand(unittest.TestCase):
    def setUp(self):
        self.session = DummySession()
        self.command = Command(self.session)

    @patch("agentbay.command.command.Command._call_mcp_tool")
    def test_execute_command_success(self, mock_call_mcp_tool):
        """
        Test execute_command method with successful response.
        """
        mock_result = OperationResult(
            request_id="request-123", success=True, data="line1\nline2\n"
        )
        mock_call_mcp_tool.return_value = mock_result

        result = self.command.execute_command("ls -la")
        self.assertIsInstance(result, CommandResult)
        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "request-123")
        self.assertEqual(result.output, "line1\nline2\n")
        self.assertEqual(result.error_message, "")

        # Verify call arguments
        mock_call_mcp_tool.assert_called_once()
        args = mock_call_mcp_tool.call_args[0][1]
        self.assertEqual(args["command"], "ls -la")
        self.assertEqual(args["timeout_ms"], 1000)  # Default timeout

    @patch("agentbay.command.command.Command._call_mcp_tool")
    def test_execute_command_with_custom_timeout(self, mock_call_mcp_tool):
        """
        Test execute_command method with custom timeout.
        """
        mock_result = OperationResult(
            request_id="request-123", success=True, data="line1\nline2\n"
        )
        mock_call_mcp_tool.return_value = mock_result

        custom_timeout = 2000
        result = self.command.execute_command("ls -la", timeout_ms=custom_timeout)
        self.assertIsInstance(result, CommandResult)
        self.assertTrue(result.success)
        self.assertEqual(result.output, "line1\nline2\n")

        # Verify custom timeout was used
        mock_call_mcp_tool.assert_called_once()
        args = mock_call_mcp_tool.call_args[0][1]
        self.assertEqual(args["timeout_ms"], custom_timeout)

    @patch("agentbay.command.command.Command._call_mcp_tool")
    def test_execute_command_error(self, mock_call_mcp_tool):
        """
        Test execute_command method with error response.
        """
        mock_result = OperationResult(
            request_id="request-123",
            success=False,
            error_message="Command execution failed",
        )
        mock_call_mcp_tool.return_value = mock_result

        result = self.command.execute_command("ls -la")
        self.assertIsInstance(result, CommandResult)
        self.assertFalse(result.success)
        self.assertEqual(result.request_id, "request-123")
        self.assertEqual(result.error_message, "Command execution failed")
        self.assertEqual(result.output, "")

    @patch("agentbay.command.command.Command._call_mcp_tool")
    def test_execute_command_exception(self, mock_call_mcp_tool):
        """
        Test execute_command method with exception.
        """
        mock_call_mcp_tool.side_effect = Exception("mock error")

        result = self.command.execute_command("ls -la")
        self.assertIsInstance(result, CommandResult)
        self.assertFalse(result.success)
        self.assertEqual(result.request_id, "")
        self.assertIn("Failed to execute command: mock error", result.error_message)
        self.assertEqual(result.output, "")


if __name__ == "__main__":
    unittest.main()
