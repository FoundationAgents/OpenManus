import os
import sys
import unittest
from unittest.mock import Mock, patch

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

# Add the parent directory to the path so we can import the agentbay package
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestRefactoredMethods(unittest.TestCase):
    """Test cases for refactored methods in AgentBay class."""

    def setUp(self):
        """Set up test fixtures."""
        self.agent_bay = AgentBay(api_key="test-api-key")

    def test_build_session_from_response(self):
        """Test _build_session_from_response method."""
        # Mock response data
        response_data = {
            "SessionId": "test-session-123",
            "ResourceUrl": "https://test.example.com",
            "NetworkInterfaceIp": "192.168.1.1",
            "HttpPort": 8080,
            "Token": "test-token"
        }

        # Mock params
        params = Mock()
        params.is_vpc = True
        params.enable_browser_replay = True
        params.image_id = "test-image"
        params.extra_configs = None

        # Mock session
        with patch('agentbay.session.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # Call the method
            result = self.agent_bay._build_session_from_response(response_data, params)

            # Verify session was created with correct parameters
            mock_session_class.assert_called_once_with(self.agent_bay, "test-session-123")

            # Verify session properties were set
            self.assertEqual(mock_session.is_vpc, True)
            self.assertEqual(mock_session.network_interface_ip, "192.168.1.1")
            self.assertEqual(mock_session.http_port, 8080)
            self.assertEqual(mock_session.token, "test-token")
            self.assertEqual(mock_session.resource_url, "https://test.example.com")
            self.assertEqual(mock_session.enableBrowserReplay, True)

            # Verify result
            self.assertEqual(result, mock_session)

    def test_fetch_mcp_tools_for_vpc_session(self):
        """Test _fetch_mcp_tools_for_vpc_session method."""
        # Mock session
        mock_session = Mock()
        mock_tools_result = Mock()
        mock_tools_result.tools = ["tool1", "tool2", "tool3"]
        mock_tools_result.request_id = "test-request-123"
        mock_session.list_mcp_tools.return_value = mock_tools_result

        # Call the method
        self.agent_bay._fetch_mcp_tools_for_vpc_session(mock_session)

        # Verify list_mcp_tools was called
        mock_session.list_mcp_tools.assert_called_once()

    def test_fetch_mcp_tools_for_vpc_session_with_error(self):
        """Test _fetch_mcp_tools_for_vpc_session method with error."""
        # Mock session that raises an exception
        mock_session = Mock()
        mock_session.list_mcp_tools.side_effect = Exception("Test error")

        # Call the method - should not raise an exception
        self.agent_bay._fetch_mcp_tools_for_vpc_session(mock_session)

        # Verify list_mcp_tools was called
        mock_session.list_mcp_tools.assert_called_once()

    def test_wait_for_context_synchronization(self):
        """Test _wait_for_context_synchronization method."""
        # Mock session
        mock_session = Mock()
        mock_context = Mock()
        mock_session.context = mock_context

        # Mock context info result
        mock_context_item = Mock()
        mock_context_item.context_id = "test-context-123"
        mock_context_item.status = "Success"
        mock_context_item.path = "/test/path"
        mock_context_item.error_message = None

        mock_info_result = Mock()
        mock_info_result.context_status_data = [mock_context_item]
        mock_context.info.return_value = mock_info_result

        # Call the method
        self.agent_bay._wait_for_context_synchronization(mock_session)

        # Verify context.info was called
        mock_context.info.assert_called_once()

    def test_log_request_debug_info(self):
        """Test _log_request_debug_info method."""
        # Mock request
        mock_request = Mock()
        mock_request.to_map.return_value = {
            "Authorization": "Bearer test-token-1234567890",
            "OtherField": "test-value"
        }

        # Call the method
        self.agent_bay._log_request_debug_info(mock_request)

        # Verify to_map was called
        mock_request.to_map.assert_called_once()

    def test_log_request_debug_info_with_short_auth(self):
        """Test _log_request_debug_info method with short authorization."""
        # Mock request with short authorization
        mock_request = Mock()
        mock_request.to_map.return_value = {
            "Authorization": "short",
            "OtherField": "test-value"
        }

        # Call the method
        self.agent_bay._log_request_debug_info(mock_request)

        # Verify to_map was called
        mock_request.to_map.assert_called_once()

    def test_log_request_debug_info_with_exception(self):
        """Test _log_request_debug_info method with exception."""
        # Mock request that raises an exception
        mock_request = Mock()
        mock_request.to_map.side_effect = Exception("Test error")

        # Call the method - should not raise an exception
        self.agent_bay._log_request_debug_info(mock_request)

        # Verify to_map was called
        mock_request.to_map.assert_called_once()

    def test_update_browser_replay_context_success(self):
        """Test _update_browser_replay_context method with successful update."""
        # Mock response data
        response_data = {
            "AppInstanceId": "ai-0d67g8gz0l6tsd17i",
            "SessionId": "session-123",
            "Success": True
        }
        record_context_id = "record-context-123"

        # Mock context update result
        mock_update_result = Mock()
        mock_update_result.success = True
        mock_update_result.error_message = None

        # Mock context service
        with patch.object(self.agent_bay, 'context') as mock_context:
            mock_context.update.return_value = mock_update_result

            # Call the method
            self.agent_bay._update_browser_replay_context(response_data, record_context_id)

            # Verify context.update was called with a Context object
            mock_context.update.assert_called_once()
            call_args = mock_context.update.call_args[0]
            context_obj = call_args[0]
            self.assertEqual(context_obj.id, record_context_id)
            self.assertEqual(context_obj.name, "browserreplay-ai-0d67g8gz0l6tsd17i")

    def test_update_browser_replay_context_no_record_context_id(self):
        """Test _update_browser_replay_context method when no record context ID provided."""
        # Mock response data
        response_data = {
            "AppInstanceId": "ai-0d67g8gz0l6tsd17i",
            "SessionId": "session-123",
            "Success": True
        }
        record_context_id = ""  # Empty record context ID

        # Mock context service
        with patch.object(self.agent_bay, 'context') as mock_context:
            # Call the method
            self.agent_bay._update_browser_replay_context(response_data, record_context_id)

            # Verify context.update was not called
            mock_context.update.assert_not_called()

    def test_update_browser_replay_context_no_app_instance_id(self):
        """Test _update_browser_replay_context method when AppInstanceId is missing."""
        # Mock response data without AppInstanceId
        response_data = {
            "SessionId": "session-123",
            "Success": True
        }
        record_context_id = "record-context-123"

        # Mock context service
        with patch.object(self.agent_bay, 'context') as mock_context:
            # Call the method
            self.agent_bay._update_browser_replay_context(response_data, record_context_id)

            # Verify context.update was not called
            mock_context.update.assert_not_called()

    def test_update_browser_replay_context_with_error(self):
        """Test _update_browser_replay_context method with context update error."""
        # Mock response data
        response_data = {
            "AppInstanceId": "ai-0d67g8gz0l6tsd17i",
            "SessionId": "session-123",
            "Success": True
        }
        record_context_id = "record-context-123"

        # Mock context update result with error
        mock_update_result = Mock()
        mock_update_result.success = False
        mock_update_result.error_message = "Context update failed"

        # Mock context service
        with patch.object(self.agent_bay, 'context') as mock_context:
            mock_context.update.return_value = mock_update_result

            # Call the method - should not raise an exception
            self.agent_bay._update_browser_replay_context(response_data, record_context_id)

            # Verify context.update was called
            mock_context.update.assert_called_once()
            call_args = mock_context.update.call_args[0]
            context_obj = call_args[0]
            self.assertEqual(context_obj.id, record_context_id)
            self.assertEqual(context_obj.name, "browserreplay-ai-0d67g8gz0l6tsd17i")

    def test_update_browser_replay_context_with_exception(self):
        """Test _update_browser_replay_context method with exception."""
        # Mock response data
        response_data = {
            "AppInstanceId": "ai-0d67g8gz0l6tsd17i",
            "SessionId": "session-123",
            "Success": True
        }
        record_context_id = "record-context-123"

        # Mock context service that raises an exception
        with patch.object(self.agent_bay, 'context') as mock_context:
            mock_context.update.side_effect = Exception("Test error")

            # Call the method - should not raise an exception
            self.agent_bay._update_browser_replay_context(response_data, record_context_id)

            # Verify context.update was called
            mock_context.update.assert_called_once()
            call_args = mock_context.update.call_args[0]
            context_obj = call_args[0]
            self.assertEqual(context_obj.id, record_context_id)
            self.assertEqual(context_obj.name, "browserreplay-ai-0d67g8gz0l6tsd17i")



if __name__ == "__main__":
    unittest.main()
