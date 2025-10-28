import json
import unittest
from unittest import mock

from agentbay import AgentBay
from agentbay.session_params import ListSessionParams


class TestSessionPagination(unittest.TestCase):
    """Test case for session pagination functionality."""

    @mock.patch("agentbay.agentbay.mcp_client")
    def test_list_by_labels_with_pagination(self, mock_client):
        """Test list_by_labels method with pagination support."""
        # Mock response data
        mock_response = mock.MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "RequestId": "test-request-id",
                "Data": [
                    {"SessionId": "session-1"},
                    {"SessionId": "session-2"},
                    {"SessionId": "session-3"},
                ],
                "NextToken": "next-page-token",
                "MaxResults": "5",
                "TotalCount": "15",
            }
        }

        # Setup mock client
        mock_client_instance = mock.MagicMock()
        mock_client_instance.list_session.return_value = mock_response
        mock_client.return_value = mock_client_instance

        # Create AgentBay instance
        agent_bay = AgentBay(api_key="test-api-key")

        # Create pagination params
        params = ListSessionParams(
            max_results=5,
            next_token="",
            labels={"env": "test", "project": "demo"},
        )

        # Call list_by_labels with pagination
        result = agent_bay.list_by_labels(params)

        # Check the call to list_session
        call_args = mock_client_instance.list_session.call_args[0][0]
        self.assertEqual(call_args.authorization, "Bearer test-api-key")
        self.assertEqual(call_args.max_results, 5)  # int type, not string
        self.assertEqual(
            json.loads(call_args.labels), {"env": "test", "project": "demo"}
        )

        # Check result
        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(len(result.session_ids), 3)
        self.assertEqual(result.next_token, "next-page-token")
        self.assertEqual(result.max_results, 5)
        self.assertEqual(result.total_count, 15)

    @mock.patch("agentbay.agentbay.mcp_client")
    def test_list_by_labels_with_next_token(self, mock_client):
        """Test list_by_labels method with next_token."""
        # Mock response for second page
        mock_response = mock.MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "RequestId": "test-request-id-2",
                "Data": [
                    {"SessionId": "session-4"},
                    {"SessionId": "session-5"},
                ],
                "NextToken": "",  # No more pages
                "MaxResults": "5",
                "TotalCount": "15",
            }
        }

        # Setup mock client
        mock_client_instance = mock.MagicMock()
        mock_client_instance.list_session.return_value = mock_response
        mock_client.return_value = mock_client_instance

        # Create AgentBay instance
        agent_bay = AgentBay(api_key="test-api-key")

        # Create pagination params with next_token
        params = ListSessionParams(
            max_results=5,
            next_token="next-page-token",  # Using token from previous test
            labels={"env": "test", "project": "demo"},
        )

        # Call list_by_labels with pagination
        result = agent_bay.list_by_labels(params)

        # Check the call to list_session with next_token
        call_args = mock_client_instance.list_session.call_args[0][0]
        self.assertEqual(call_args.next_token, "next-page-token")

        # Check result
        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "test-request-id-2")
        self.assertEqual(len(result.session_ids), 2)
        self.assertEqual(result.next_token, "")  # No more pages

    @mock.patch("agentbay.agentbay.mcp_client")
    def test_list_by_labels_default_params(self, mock_client):
        """Test list_by_labels method with default parameters."""
        # Mock response
        mock_response = mock.MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "RequestId": "test-request-id",
                "Data": [{"SessionId": "session-1"}],
                "MaxResults": "10",
                "TotalCount": "1",
            }
        }

        # Setup mock client
        mock_client_instance = mock.MagicMock()
        mock_client_instance.list_session.return_value = mock_response
        mock_client.return_value = mock_client_instance

        # Create AgentBay instance
        agent_bay = AgentBay(api_key="test-api-key")

        # Call list_by_labels without params (should use defaults)
        result = agent_bay.list_by_labels()

        # Check the call to list_session uses default values
        call_args = mock_client_instance.list_session.call_args[0][0]
        self.assertEqual(call_args.max_results, 10)  # Default max_results (int type)
        self.assertEqual(json.loads(call_args.labels), {})  # Default empty labels

        # Check result
        self.assertTrue(result.success)
        self.assertEqual(result.max_results, 10)
        self.assertEqual(result.total_count, 1)


if __name__ == "__main__":
    unittest.main()
