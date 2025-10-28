import unittest
from unittest.mock import MagicMock

from agentbay.context import Context, ContextService, ContextListParams, ContextListResult


class TestContextPagination(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.agent_bay = MagicMock()
        self.agent_bay.api_key = "test-api-key"
        self.agent_bay.client = MagicMock()
        self.context_service = ContextService(self.agent_bay)

    def test_list_contexts_with_default_params(self):
        """Test listing contexts with default pagination parameters."""
        # Mock the response from the API
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "Data": [
                    {
                        "Id": "context-1",
                        "Name": "context-1-name",
                        "State": "available",
                        "CreateTime": "2025-05-29T12:00:00Z",
                        "LastUsedTime": "2025-05-29T12:30:00Z",
                        "OsType": "linux",
                    },
                    {
                        "Id": "context-2",
                        "Name": "context-2-name",
                        "State": "in-use",
                        "CreateTime": "2025-05-29T13:00:00Z",
                        "LastUsedTime": "2025-05-29T13:30:00Z",
                        "OsType": "windows",
                    },
                ],
                "NextToken": "next-page-token",
                "MaxResults": 10,
                "TotalCount": 15,
            }
        }
        self.agent_bay.client.list_contexts.return_value = mock_response

        # Call the method with default params (None)
        result = self.context_service.list(None)

        # Verify the API was called with default parameters
        self.agent_bay.client.list_contexts.assert_called_once()
        call_args = self.agent_bay.client.list_contexts.call_args[0][0]
        self.assertEqual(call_args.max_results, 10)
        self.assertIsNone(call_args.next_token)

        # Verify the results
        self.assertTrue(result.success)
        self.assertEqual(len(result.contexts), 2)
        self.assertEqual(result.contexts[0].id, "context-1")
        self.assertEqual(result.contexts[0].name, "context-1-name")
        self.assertEqual(result.contexts[0].state, "available")
        self.assertEqual(result.contexts[1].id, "context-2")
        self.assertEqual(result.contexts[1].name, "context-2-name")
        self.assertEqual(result.contexts[1].state, "in-use")
        self.assertEqual(result.next_token, "next-page-token")
        self.assertEqual(result.max_results, 10)
        self.assertEqual(result.total_count, 15)

    def test_list_contexts_with_custom_params(self):
        """Test listing contexts with custom pagination parameters."""
        # Mock the response from the API
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "Data": [
                    {
                        "Id": "context-3",
                        "Name": "context-3-name",
                        "State": "available",
                        "CreateTime": "2025-05-29T14:00:00Z",
                        "LastUsedTime": "2025-05-29T14:30:00Z",
                        "OsType": "linux",
                    },
                    {
                        "Id": "context-4",
                        "Name": "context-4-name",
                        "State": "in-use",
                        "CreateTime": "2025-05-29T15:00:00Z",
                        "LastUsedTime": "2025-05-29T15:30:00Z",
                        "OsType": "windows",
                    },
                    {
                        "Id": "context-5",
                        "Name": "context-5-name",
                        "State": "available",
                        "CreateTime": "2025-05-29T16:00:00Z",
                        "LastUsedTime": "2025-05-29T16:30:00Z",
                        "OsType": "macos",
                    },
                ],
                "NextToken": "another-page-token",
                "MaxResults": 5,
                "TotalCount": 15,
            }
        }
        self.agent_bay.client.list_contexts.return_value = mock_response

        # Create custom params
        params = ContextListParams(max_results=5, next_token="page-token")

        # Call the method with custom params
        result = self.context_service.list(params)

        # Verify the API was called with custom parameters
        self.agent_bay.client.list_contexts.assert_called_once()
        call_args = self.agent_bay.client.list_contexts.call_args[0][0]
        self.assertEqual(call_args.max_results, 5)
        self.assertEqual(call_args.next_token, "page-token")

        # Verify the results
        self.assertTrue(result.success)
        self.assertEqual(len(result.contexts), 3)
        self.assertEqual(result.contexts[0].id, "context-3")
        self.assertEqual(result.contexts[1].id, "context-4")
        self.assertEqual(result.contexts[2].id, "context-5")
        self.assertEqual(result.next_token, "another-page-token")
        self.assertEqual(result.max_results, 5)
        self.assertEqual(result.total_count, 15)

    def test_list_contexts_with_default_params_object(self):
        """Test listing contexts with a default ContextListParams object."""
        # Mock the response from the API
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "Data": [
                    {
                        "Id": "context-6",
                        "Name": "context-6-name",
                        "State": "available",
                        "CreateTime": "2025-05-29T17:00:00Z",
                        "LastUsedTime": "2025-05-29T17:30:00Z",
                        "OsType": "linux",
                    },
                ],
                "NextToken": "",
                "MaxResults": 10,
                "TotalCount": 1,
            }
        }
        self.agent_bay.client.list_contexts.return_value = mock_response

        # Create default params object
        params = ContextListParams()

        # Call the method with default params object
        result = self.context_service.list(params)

        # Verify the API was called with default parameters
        self.agent_bay.client.list_contexts.assert_called_once()
        call_args = self.agent_bay.client.list_contexts.call_args[0][0]
        self.assertEqual(call_args.max_results, 10)
        self.assertIsNone(call_args.next_token)

        # Verify the results
        self.assertTrue(result.success)
        self.assertEqual(len(result.contexts), 1)
        self.assertEqual(result.contexts[0].id, "context-6")
        self.assertEqual(result.next_token, "")
        self.assertEqual(result.max_results, 10)
        self.assertEqual(result.total_count, 1)

    def test_list_contexts_error_handling(self):
        """Test error handling in list contexts method."""
        # Mock the API to raise an exception
        self.agent_bay.client.list_contexts.side_effect = Exception("API Error")

        # Call the method
        result = self.context_service.list(None)

        # Verify the results
        self.assertFalse(result.success)
        self.assertEqual(len(result.contexts), 0)
        self.assertIsNone(result.next_token)
        self.assertIsNone(result.max_results)
        self.assertIsNone(result.total_count)
        self.assertEqual(result.request_id, "")


if __name__ == "__main__":
    unittest.main()