import unittest
from unittest.mock import MagicMock, patch
from agentbay.session import Session, DeleteResult

class DummyAgentBay:
    def __init__(self):
        self.client = MagicMock()
        self.api_key = "test_api_key"

    def get_api_key(self):
        return self.api_key

    def get_client(self):
        return self.client

class TestSession(unittest.TestCase):
    def setUp(self):
        self.agent_bay = DummyAgentBay()
        self.session_id = "test_session_id"
        self.session = Session(self.agent_bay, self.session_id)

    def test_validate_labels_success(self):
        # Test successful validation with valid labels
        labels = {"key1": "value1", "key2": "value2"}
        result = self.session._validate_labels(labels)
        self.assertIsNone(result)

    def test_validate_labels_none(self):
        # Test validation with None labels
        labels = None
        result = self.session._validate_labels(labels)
        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertIn("Labels cannot be null", result.error_message)

    def test_validate_labels_list(self):
        # Test validation with list instead of dict
        labels = ["key1", "value1"]
        result = self.session._validate_labels(labels)
        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertIn("Labels cannot be an array", result.error_message)

    def test_validate_labels_empty_dict(self):
        # Test validation with empty dict
        labels = {}
        result = self.session._validate_labels(labels)
        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertIn("Labels cannot be empty", result.error_message)

    def test_validate_labels_empty_key(self):
        # Test validation with empty key
        labels = {"": "value1"}
        result = self.session._validate_labels(labels)
        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertIn("Label keys cannot be empty", result.error_message)

    def test_validate_labels_empty_value(self):
        # Test validation with empty value
        labels = {"key1": ""}
        result = self.session._validate_labels(labels)
        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertIn("Label values cannot be empty", result.error_message)

    def test_validate_labels_none_value(self):
        # Test validation with None value
        labels = {"key1": None}
        result = self.session._validate_labels(labels)
        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertIn("Label values cannot be empty", result.error_message)

    def test_initialization(self):
        self.assertEqual(self.session.session_id, self.session_id)
        self.assertEqual(self.session.agent_bay, self.agent_bay)
        self.assertIsNotNone(self.session.file_system)
        self.assertIsNotNone(self.session.command)
        self.assertEqual(self.session.file_system.session, self.session)
        self.assertEqual(self.session.command.session, self.session)

    def test_get_api_key(self):
        self.assertEqual(self.session.get_api_key(), "test_api_key")

    def test_get_client(self):
        self.assertEqual(self.session.get_client(), self.agent_bay.client)

    def test_get_session_id(self):
        self.assertEqual(self.session.get_session_id(), "test_session_id")

    @patch("agentbay.session.extract_request_id")
    @patch("agentbay.session.ReleaseMcpSessionRequest")
    def test_delete_success(
        self, MockReleaseMcpSessionRequest, mock_extract_request_id
    ):
        mock_request = MagicMock()
        mock_response = MagicMock()
        MockReleaseMcpSessionRequest.return_value = mock_request
        mock_extract_request_id.return_value = "request-123"
        self.agent_bay.client.release_mcp_session.return_value = mock_response

        # Mock the response.to_map() method
        mock_response.to_map.return_value = {
            "body": {"Data": {"IsError": False}, "Success": True}
        }

        result = self.session.delete()
        self.assertIsInstance(result, DeleteResult)
        self.assertEqual(result.request_id, "request-123")
        self.assertTrue(result.success)

        MockReleaseMcpSessionRequest.assert_called_once_with(
            authorization="Bearer test_api_key", session_id="test_session_id"
        )
        self.agent_bay.client.release_mcp_session.assert_called_once_with(mock_request)

    @patch("agentbay.session.extract_request_id")
    @patch("agentbay.session.ReleaseMcpSessionRequest")
    def test_delete_without_params(
        self, MockReleaseMcpSessionRequest, mock_extract_request_id
    ):
        # Test default behavior when no parameters are provided
        mock_request = MagicMock()
        mock_response = MagicMock()
        MockReleaseMcpSessionRequest.return_value = mock_request
        mock_extract_request_id.return_value = "request-123"
        self.agent_bay.client.release_mcp_session.return_value = mock_response

        # Mock the response.to_map() method
        mock_response.to_map.return_value = {
            "body": {"Data": {"IsError": False}, "Success": True}
        }

        # Set up context mock object
        self.session.context = MagicMock()

        # Call delete method without parameters
        result = self.session.delete()
        self.assertIsInstance(result, DeleteResult)
        self.assertTrue(result.success)

        # Verify sync was not called
        self.session.context.sync.assert_not_called()

        # Verify API call is correct
        MockReleaseMcpSessionRequest.assert_called_once_with(
            authorization="Bearer test_api_key", session_id="test_session_id"
        )
        self.agent_bay.client.release_mcp_session.assert_called_once_with(mock_request)

    @patch("agentbay.session.extract_request_id")
    @patch("agentbay.session.ReleaseMcpSessionRequest")
    def test_delete_with_sync_context(
        self, MockReleaseMcpSessionRequest, mock_extract_request_id
    ):
        # Test behavior when sync_context=True
        mock_request = MagicMock()
        mock_response = MagicMock()
        MockReleaseMcpSessionRequest.return_value = mock_request
        mock_extract_request_id.return_value = "request-123"
        self.agent_bay.client.release_mcp_session.return_value = mock_response

        # Mock the response.to_map() method
        mock_response.to_map.return_value = {
            "body": {"Data": {"IsError": False}, "Success": True}
        }

        # Set up context mock object
        self.session.context = MagicMock()

        # Mock context.sync return value (now returns a coroutine)
        sync_result = MagicMock()
        sync_result.success = True
        # Since context.sync is now async, we need to mock it as a coroutine
        import asyncio
        async def mock_sync():
            return sync_result
        self.session.context.sync.return_value = mock_sync()

        # Call delete method with sync_context=True
        result = self.session.delete(sync_context=True)
        self.assertIsInstance(result, DeleteResult)
        self.assertTrue(result.success)

        # Verify sync was called (but not info since we're not using callback mode)
        self.session.context.sync.assert_called_once()

        # Verify API call is correct
        MockReleaseMcpSessionRequest.assert_called_once_with(
            authorization="Bearer test_api_key", session_id="test_session_id"
        )
        self.agent_bay.client.release_mcp_session.assert_called_once_with(mock_request)

    @patch("agentbay.session.extract_request_id")
    @patch("agentbay.session.ReleaseMcpSessionRequest")
    def test_delete_failure(
        self, MockReleaseMcpSessionRequest, mock_extract_request_id
    ):
        mock_request = MagicMock()
        MockReleaseMcpSessionRequest.return_value = mock_request
        mock_extract_request_id.return_value = "request-123"
        self.agent_bay.client.release_mcp_session.side_effect = Exception("Test error")

        result = self.session.delete()
        self.assertIsInstance(result, DeleteResult)
        self.assertFalse(result.success)
        self.assertEqual(
            result.error_message,
            f"Failed to delete session {self.session_id}: Test error",
        )

        MockReleaseMcpSessionRequest.assert_called_once_with(
            authorization="Bearer test_api_key", session_id="test_session_id"
        )
        self.agent_bay.client.release_mcp_session.assert_called_once_with(mock_request)

    @patch("agentbay.session.extract_request_id")
    @patch("agentbay.session.ReleaseMcpSessionRequest")
    def test_delete_api_failure_response(
        self, MockReleaseMcpSessionRequest, mock_extract_request_id
    ):
        mock_request = MagicMock()
        mock_response = MagicMock()
        MockReleaseMcpSessionRequest.return_value = mock_request
        mock_extract_request_id.return_value = "request-123"
        self.agent_bay.client.release_mcp_session.return_value = mock_response

        # Mock the response.to_map() method to return a failure response
        mock_response.to_map.return_value = {
            "body": {"Data": {"IsError": True}, "Success": False}
        }

        result = self.session.delete()
        self.assertIsInstance(result, DeleteResult)
        self.assertEqual(result.request_id, "request-123")
        self.assertFalse(result.success)

        MockReleaseMcpSessionRequest.assert_called_once_with(
            authorization="Bearer test_api_key", session_id="test_session_id"
        )
        self.agent_bay.client.release_mcp_session.assert_called_once_with(mock_request)

    @patch("agentbay.session.extract_request_id")
    @patch("agentbay.session.SetLabelRequest")
    def test_set_labels_success(
        self, MockSetLabelRequest, mock_extract_request_id
    ):
        from agentbay.model.response import OperationResult

        mock_request = MagicMock()
        mock_response = MagicMock()
        MockSetLabelRequest.return_value = mock_request
        mock_extract_request_id.return_value = "request-456"
        self.agent_bay.client.set_label.return_value = mock_response

        # Mock the response.to_map() method
        mock_response.to_map.return_value = {
            "body": {"Data": {}, "Success": True}
        }

        labels = {"key1": "value1", "key2": "value2"}
        result = self.session.set_labels(labels)
        self.assertIsInstance(result, OperationResult)
        self.assertEqual(result.request_id, "request-456")
        self.assertTrue(result.success)

        MockSetLabelRequest.assert_called_once_with(
            authorization="Bearer test_api_key",
            session_id="test_session_id",
            labels='{"key1": "value1", "key2": "value2"}',
        )
        self.agent_bay.client.set_label.assert_called_once_with(mock_request)

    @patch("agentbay.session.extract_request_id")
    @patch("agentbay.session.SetLabelRequest")
    def test_set_labels_api_failure(
        self, MockSetLabelRequest, mock_extract_request_id
    ):
        mock_request = MagicMock()
        MockSetLabelRequest.return_value = mock_request
        mock_extract_request_id.return_value = "request-789"
        self.agent_bay.client.set_label.side_effect = Exception("API Error")

        labels = {"key1": "value1"}
        with self.assertRaises(Exception) as context:
            self.session.set_labels(labels)

        self.assertIn("Failed to set labels for session", str(context.exception))

        MockSetLabelRequest.assert_called_once_with(
            authorization="Bearer test_api_key",
            session_id="test_session_id",
            labels='{"key1": "value1"}',
        )
        self.agent_bay.client.set_label.assert_called_once_with(mock_request)

    @patch("agentbay.session.extract_request_id")
    @patch("agentbay.session.GetLabelRequest")
    def test_get_labels_success(
        self, MockGetLabelRequest, mock_extract_request_id
    ):
        from agentbay.model.response import OperationResult

        mock_request = MagicMock()
        mock_response = MagicMock()
        MockGetLabelRequest.return_value = mock_request
        mock_extract_request_id.return_value = "request-101"
        self.agent_bay.client.get_label.return_value = mock_response

        # Mock the response.to_map() method
        mock_response.to_map.return_value = {
            "body": {"Data": {"Labels": '{"key1": "value1"}'}, "Success": True}
        }

        result = self.session.get_labels()
        self.assertIsInstance(result, OperationResult)
        self.assertEqual(result.request_id, "request-101")
        self.assertTrue(result.success)
        # Note: In the actual implementation, result.data would be the parsed labels

        MockGetLabelRequest.assert_called_once_with(
            authorization="Bearer test_api_key",
            session_id="test_session_id",
        )
        self.agent_bay.client.get_label.assert_called_once_with(mock_request)

    @patch("agentbay.session.extract_request_id")
    @patch("agentbay.session.GetLabelRequest")
    def test_get_labels_api_failure(
        self, MockGetLabelRequest, mock_extract_request_id
    ):
        mock_request = MagicMock()
        MockGetLabelRequest.return_value = mock_request
        mock_extract_request_id.return_value = "request-102"
        self.agent_bay.client.get_label.side_effect = Exception("API Error")

        with self.assertRaises(Exception) as context:
            self.session.get_labels()

        self.assertIn("Failed to get labels for session", str(context.exception))

        MockGetLabelRequest.assert_called_once_with(
            authorization="Bearer test_api_key",
            session_id="test_session_id",
        )
        self.agent_bay.client.get_label.assert_called_once_with(mock_request)

    @patch("agentbay.session.extract_request_id")
    @patch("agentbay.session.GetLinkRequest")
    def test_get_link_success(
        self, MockGetLinkRequest, mock_extract_request_id
    ):
        from agentbay.model.response import OperationResult

        mock_request = MagicMock()
        mock_response = MagicMock()
        MockGetLinkRequest.return_value = mock_request
        mock_extract_request_id.return_value = "request-103"
        self.agent_bay.client.get_link.return_value = mock_response

        # Mock the response.to_map() method
        mock_response.to_map.return_value = {
            "body": {
                "Data": {"Url": "http://example.com"},
                "Success": True
            }
        }

        result = self.session.get_link()
        self.assertIsInstance(result, OperationResult)
        self.assertEqual(result.request_id, "request-103")
        self.assertTrue(result.success)
        self.assertEqual(result.data, "http://example.com")

        MockGetLinkRequest.assert_called_once_with(
            authorization="Bearer test_api_key",
            session_id="test_session_id",
            protocol_type=None,
            port=None,
        )
        self.agent_bay.client.get_link.assert_called_once_with(mock_request)

    @patch("agentbay.session.extract_request_id")
    @patch("agentbay.session.GetLinkRequest")
    def test_get_link_with_valid_port(
        self, MockGetLinkRequest, mock_extract_request_id
    ):
        """Test get_link with valid port values in range [30100, 30199]"""
        from agentbay.model.response import OperationResult

        mock_request = MagicMock()
        mock_response = MagicMock()
        MockGetLinkRequest.return_value = mock_request
        mock_extract_request_id.return_value = "request-104"
        self.agent_bay.client.get_link.return_value = mock_response

        # Mock the response.to_map() method
        mock_response.to_map.return_value = {
            "body": {
                "Data": {"Url": "http://example.com:30150"},
                "Success": True
            }
        }

        # Test with valid ports in range [30100, 30199]
        valid_ports = [30100, 30150, 30199]

        for port in valid_ports:
            with self.subTest(port=port):
                MockGetLinkRequest.reset_mock()
                self.agent_bay.client.get_link.reset_mock()

                result = self.session.get_link(port=port)
                self.assertIsInstance(result, OperationResult)
                self.assertEqual(result.request_id, "request-104")
                self.assertTrue(result.success)
                self.assertEqual(result.data, "http://example.com:30150")

                MockGetLinkRequest.assert_called_once_with(
                    authorization="Bearer test_api_key",
                    session_id="test_session_id",
                    protocol_type=None,
                    port=port,
                )
                self.agent_bay.client.get_link.assert_called_once_with(mock_request)

    def test_get_link_with_invalid_port_below_range(self):
        """Test get_link with port below valid range raises SessionError"""
        from agentbay.exceptions import SessionError

        invalid_port = 30099

        with self.assertRaises(SessionError) as context:
            self.session.get_link(port=invalid_port)

        error_message = str(context.exception)
        expected_message = f"Invalid port value: {invalid_port}. Port must be an integer in the range [30100, 30199]."
        self.assertEqual(error_message, expected_message)

    def test_get_link_with_invalid_port_above_range(self):
        """Test get_link with port above valid range raises SessionError"""
        from agentbay.exceptions import SessionError

        invalid_port = 30200

        with self.assertRaises(SessionError) as context:
            self.session.get_link(port=invalid_port)

        error_message = str(context.exception)
        expected_message = f"Invalid port value: {invalid_port}. Port must be an integer in the range [30100, 30199]."
        self.assertEqual(error_message, expected_message)

    def test_get_link_with_invalid_port_non_integer(self):
        """Test get_link with non-integer port raises SessionError"""
        from agentbay.exceptions import SessionError

        invalid_ports = [30150.5, "30150"]

        for invalid_port in invalid_ports:
            with self.subTest(port=invalid_port):
                with self.assertRaises(SessionError) as context:
                    self.session.get_link(port=invalid_port)

                error_message = str(context.exception)
                expected_message = f"Invalid port value: {invalid_port}. Port must be an integer in the range [30100, 30199]."
                self.assertEqual(error_message, expected_message)

    def test_get_link_with_invalid_port_boundary_values(self):
        """Test get_link with boundary values outside valid range"""
        from agentbay.exceptions import SessionError

        # Test boundary values just outside the valid range
        invalid_ports = [30099, 30200, 0, -1, 65536]

        for invalid_port in invalid_ports:
            with self.subTest(port=invalid_port):
                with self.assertRaises(SessionError) as context:
                    self.session.get_link(port=invalid_port)

                error_message = str(context.exception)
                expected_message = f"Invalid port value: {invalid_port}. Port must be an integer in the range [30100, 30199]."
                self.assertEqual(error_message, expected_message)

class TestAgentBayDelete(unittest.TestCase):
    def setUp(self):
        self.agent_bay = DummyAgentBay()
        self.session = MagicMock()
        self.session.session_id = "test_session_id"
        # Add _lock mock
        self.agent_bay._lock = MagicMock()
        self.agent_bay._sessions = {"test_session_id": self.session}

    def test_delete_without_params(self):
        # Test AgentBay.delete without parameters
        # Mock session.delete return value
        delete_result = DeleteResult(request_id="request-123", success=True)
        self.session.delete.return_value = delete_result
        
        # Ensure session doesn't have enableBrowserReplay or it's False
        self.session.enableBrowserReplay = False

        # Import AgentBay class
        from agentbay import AgentBay
        # Monkey patch AgentBay instance
        self.agent_bay.__class__ = AgentBay

        # Call delete method without parameters
        result = self.agent_bay.delete(self.session)

        # Verify session.delete was called with default sync_context=False
        self.session.delete.assert_called_once_with(sync_context=False)
        self.assertEqual(result, delete_result)

    def test_delete_with_sync_context(self):
        # Test AgentBay.delete with sync_context=True
        # Mock session.delete return value
        delete_result = DeleteResult(request_id="request-456", success=True)
        self.session.delete.return_value = delete_result

        # Import AgentBay class
        from agentbay import AgentBay
        # Monkey patch AgentBay instance
        self.agent_bay.__class__ = AgentBay

        # Call delete method with sync_context=True
        result = self.agent_bay.delete(self.session, sync_context=True)

        # Verify session.delete was called with sync_context=True
        self.session.delete.assert_called_once_with(sync_context=True)
        self.assertEqual(result, delete_result)


if __name__ == "__main__":
    unittest.main()
