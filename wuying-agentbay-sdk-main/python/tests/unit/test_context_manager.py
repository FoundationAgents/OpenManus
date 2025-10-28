import unittest
from unittest.mock import MagicMock, patch
import json
import asyncio

from agentbay.context_manager import (
    ContextManager,
    ContextStatusData,
    ContextInfoResult,
    ContextSyncResult,
)


class TestContextManager(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.get_api_key.return_value = "test-api-key"
        self.mock_session.get_session_id.return_value = "test-session-id"
        self.mock_client = MagicMock()
        self.mock_session.get_client.return_value = self.mock_client

        self.context_manager = ContextManager(self.mock_session)

    def test_info_with_empty_response(self):
        """Test info method with empty response."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {"RequestId": "test-request-id", "Data": {}}
        }
        self.mock_client.get_context_info.return_value = mock_response

        # Call the method
        result = self.context_manager.info()

        # Verify the results
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(len(result.context_status_data), 0)

        # Verify the API was called correctly
        self.mock_client.get_context_info.assert_called_once()

    def test_info_with_valid_response(self):
        """Test info method with valid response containing context status data."""
        # Create a sample context status JSON response
        context_status_str = '[{"type":"data","data":"[{\\"contextId\\":\\"ctx-123\\",\\"path\\":\\"/home/user\\",\\"errorMessage\\":\\"\\",\\"status\\":\\"Success\\",\\"startTime\\":1600000000,\\"finishTime\\":1600000100,\\"taskType\\":\\"download\\"}]"}]'

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "RequestId": "test-request-id",
                "Data": {"ContextStatus": context_status_str},
            }
        }
        self.mock_client.get_context_info.return_value = mock_response

        # Call the method
        result = self.context_manager.info()

        # Verify the results
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(len(result.context_status_data), 1)

        # Check the parsed data
        status_data = result.context_status_data[0]
        self.assertEqual(status_data.context_id, "ctx-123")
        self.assertEqual(status_data.path, "/home/user")
        self.assertEqual(status_data.error_message, "")
        self.assertEqual(status_data.status, "Success")
        self.assertEqual(status_data.start_time, 1600000000)
        self.assertEqual(status_data.finish_time, 1600000100)
        self.assertEqual(status_data.task_type, "download")

    def test_info_with_multiple_status_items(self):
        """Test info method with multiple context status items."""
        # Create a sample context status JSON response with multiple items
        context_status_str = '[{"type":"data","data":"[{\\"contextId\\":\\"ctx-123\\",\\"path\\":\\"/home/user\\",\\"errorMessage\\":\\"\\",\\"status\\":\\"Success\\",\\"startTime\\":1600000000,\\"finishTime\\":1600000100,\\"taskType\\":\\"download\\"},{\\"contextId\\":\\"ctx-456\\",\\"path\\":\\"/home/user/docs\\",\\"errorMessage\\":\\"\\",\\"status\\":\\"Success\\",\\"startTime\\":1600000200,\\"finishTime\\":1600000300,\\"taskType\\":\\"upload\\"}]"}]'

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "RequestId": "test-request-id",
                "Data": {"ContextStatus": context_status_str},
            }
        }
        self.mock_client.get_context_info.return_value = mock_response

        # Call the method
        result = self.context_manager.info()

        # Verify the results
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(len(result.context_status_data), 2)

        # Check the first item
        status_data1 = result.context_status_data[0]
        self.assertEqual(status_data1.context_id, "ctx-123")
        self.assertEqual(status_data1.path, "/home/user")
        self.assertEqual(status_data1.task_type, "download")

        # Check the second item
        status_data2 = result.context_status_data[1]
        self.assertEqual(status_data2.context_id, "ctx-456")
        self.assertEqual(status_data2.path, "/home/user/docs")
        self.assertEqual(status_data2.task_type, "upload")

    def test_info_with_invalid_json(self):
        """Test info method with invalid JSON response."""
        # Create an invalid JSON string
        context_status_str = "invalid json"

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "RequestId": "test-request-id",
                "Data": {"ContextStatus": context_status_str},
            }
        }
        self.mock_client.get_context_info.return_value = mock_response

        # Call the method
        result = self.context_manager.info()

        # Verify the results - should not raise exception but return empty list
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(len(result.context_status_data), 0)

    def test_info_with_params(self):
        """Test info method with optional parameters."""
        # Create a sample context status JSON response
        context_status_str = '[{"type":"data","data":"[{\\"contextId\\":\\"ctx-123\\",\\"path\\":\\"/home/user\\",\\"errorMessage\\":\\"\\",\\"status\\":\\"Success\\",\\"startTime\\":1600000000,\\"finishTime\\":1600000100,\\"taskType\\":\\"download\\"}]"}]'

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "RequestId": "test-request-id",
                "Data": {"ContextStatus": context_status_str},
            }
        }
        self.mock_client.get_context_info.return_value = mock_response

        # Call the method with parameters
        result = self.context_manager.info("ctx-123", "/home/user", "download")

        # Verify the results
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(len(result.context_status_data), 1)

        # Verify the API was called with the correct parameters
        self.mock_client.get_context_info.assert_called_once()
        call_args = self.mock_client.get_context_info.call_args[0][0]
        self.assertEqual(call_args.context_id, "ctx-123")
        self.assertEqual(call_args.path, "/home/user")
        self.assertEqual(call_args.task_type, "download")

    def test_sync(self):
        """Test sync method."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {"RequestId": "test-request-id", "Success": True}
        }
        self.mock_client.sync_context.return_value = mock_response

        # Mock the info method to return completed status
        with patch.object(self.context_manager, 'info') as mock_info:
            mock_info.return_value = ContextInfoResult(
                request_id="test-request-id",
                context_status_data=[]
            )

            # Call the method using asyncio.run
            result = asyncio.run(self.context_manager.sync())

            # Verify the results
            self.assertEqual(result.request_id, "test-request-id")
            self.assertTrue(result.success)

            # Verify the API was called correctly
            self.mock_client.sync_context.assert_called_once()

    def test_sync_with_params(self):
        """Test sync method with optional parameters."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {"RequestId": "test-request-id", "Success": True}
        }
        self.mock_client.sync_context.return_value = mock_response

        # Mock the info method to return completed status
        with patch.object(self.context_manager, 'info') as mock_info:
            mock_info.return_value = ContextInfoResult(
                request_id="test-request-id",
                context_status_data=[]
            )

            # Call the method with parameters using asyncio.run
            result = asyncio.run(self.context_manager.sync("ctx-123", "/home/user", "upload"))

            # Verify the results
            self.assertEqual(result.request_id, "test-request-id")
            self.assertTrue(result.success)

            # Verify the API was called with the correct parameters
            self.mock_client.sync_context.assert_called_once()
            call_args = self.mock_client.sync_context.call_args[0][0]
            self.assertEqual(call_args.context_id, "ctx-123")
            self.assertEqual(call_args.path, "/home/user")
            self.assertEqual(call_args.mode, "upload")


if __name__ == "__main__":
    unittest.main()
