import unittest
from unittest.mock import MagicMock

from agentbay.context import Context, ContextService


class TestContext(unittest.TestCase):
    def test_context_initialization(self):
        """Test that Context initializes with the correct attributes."""
        context = Context(
            id="test-id",
            name="test-context",
            state="available",
            created_at="2025-05-29T12:00:00Z",
            last_used_at="2025-05-29T12:30:00Z",
            os_type="linux",
        )

        self.assertEqual(context.id, "test-id")
        self.assertEqual(context.name, "test-context")
        self.assertEqual(context.state, "available")
        self.assertEqual(context.created_at, "2025-05-29T12:00:00Z")
        self.assertEqual(context.last_used_at, "2025-05-29T12:30:00Z")
        self.assertEqual(context.os_type, "linux")


class TestContextService(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.agent_bay = MagicMock()
        self.agent_bay.api_key = "test-api-key"
        self.agent_bay.client = MagicMock()
        self.context_service = ContextService(self.agent_bay)

    def test_list_contexts(self):
        """Test listing contexts."""
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
                ]
            }
        }
        self.agent_bay.client.list_contexts.return_value = mock_response

        # Call the method
        result = self.context_service.list()

        # Verify the results
        self.assertEqual(len(result.contexts), 2)
        self.assertEqual(result.contexts[0].id, "context-1")
        self.assertEqual(result.contexts[0].name, "context-1-name")
        self.assertEqual(result.contexts[0].state, "available")
        self.assertEqual(result.contexts[1].id, "context-2")
        self.assertEqual(result.contexts[1].name, "context-2-name")
        self.assertEqual(result.contexts[1].state, "in-use")

    def test_get_context(self):
        """Test getting a context."""
        # Mock the response from the API
        mock_get_response = MagicMock()
        mock_get_response.to_map.return_value = {"body": {"Data": {"Id": "context-1"}}}
        self.agent_bay.client.get_context.return_value = mock_get_response

        # Mock the list response to get full context details
        mock_list_response = MagicMock()
        mock_list_response.to_map.return_value = {
            "body": {
                "Data": [
                    {
                        "Id": "context-1",
                        "Name": "test-context",
                        "State": "available",
                        "CreateTime": "2025-05-29T12:00:00Z",
                        "LastUsedTime": "2025-05-29T12:30:00Z",
                        "OsType": "linux",
                    }
                ]
            }
        }
        self.agent_bay.client.list_contexts.return_value = mock_list_response

        # Call the method
        result = self.context_service.get("test-context")

        # Verify the results
        self.assertTrue(result.success)
        self.assertEqual(result.context_id, "context-1")
        self.assertEqual(result.context.id, "context-1")
        self.assertEqual(result.context.name, "test-context")
        self.assertEqual(result.context.state, "available")

    def test_create_context(self):
        """Test creating a context."""
        # Mock the response from the API
        mock_get_response = MagicMock()
        mock_get_response.to_map.return_value = {
            "body": {"Data": {"Id": "new-context-id"}}
        }
        self.agent_bay.client.get_context.return_value = mock_get_response

        # Mock the list response to get full context details
        mock_list_response = MagicMock()
        mock_list_response.to_map.return_value = {
            "body": {
                "Data": [
                    {
                        "Id": "new-context-id",
                        "Name": "new-context",
                        "State": "available",
                        "CreateTime": "2025-05-29T12:00:00Z",
                        "LastUsedTime": "2025-05-29T12:30:00Z",
                        "OsType": None,
                    }
                ]
            }
        }
        self.agent_bay.client.list_contexts.return_value = mock_list_response

        # Call the method
        result = self.context_service.create("new-context")

        # Verify the results
        self.assertTrue(result.success)
        self.assertEqual(result.context_id, "new-context-id")
        self.assertEqual(result.context.id, "new-context-id")
        self.assertEqual(result.context.name, "new-context")
        self.assertEqual(result.context.state, "available")

    def test_update_context(self):
        """Test updating a context."""
        # Create a context to update
        context = Context(
            id="context-to-update", name="updated-name", state="available"
        )

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "Code": "ok",
                "HttpStatusCode": 200,
                "RequestId": "557DCB66-03AA-1907-AFBC-4B62939AC4A9",
                "Success": True,
            }
        }
        self.agent_bay.client.modify_context.return_value = mock_response

        # Call the method
        result = self.context_service.update(context)

        # Verify the API was called correctly
        self.agent_bay.client.modify_context.assert_called_once()

        # Verify the results - should return the original context if update successful
        self.assertTrue(result.success)

    def test_delete_context(self):
        """Test deleting a context."""
        # Create a context to delete
        context = Context(
            id="context-to-delete", name="context-name", state="available"
        )

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "Code": "ok",
                "HttpStatusCode": 200,
                "RequestId": "557DCB66-03AA-1907-AFBC-4B62939AC4A9",
                "Success": True,
            }
        }
        self.agent_bay.client.delete_context.return_value = mock_response

        # Call the method
        result = self.context_service.delete(context)

        # Verify the API was called correctly
        self.agent_bay.client.delete_context.assert_called_once()

        # Verify the results
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
