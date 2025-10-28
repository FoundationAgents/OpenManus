import os
import unittest
from unittest.mock import MagicMock, patch

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams, ListSessionParams
from agentbay.api.models import ExtraConfigs, MobileExtraConfig, AppManagerRule


class TestAgentBay(unittest.TestCase):
    """Test the functionality of the main AgentBay class"""

    @patch.dict(os.environ, {"AGENTBAY_API_KEY": "test-api-key"})
    @patch("agentbay.agentbay.load_config")
    @patch("agentbay.agentbay.mcp_client")
    def test_initialization_with_env_var(self, mock_mcp_client, mock_load_config):
        """Test initializing AgentBay with an API key from environment variable"""
        # Mock configuration
        mock_load_config.return_value = {
            "endpoint": "test.endpoint.com",
            "timeout_ms": 30000,
        }

        # Mock client
        mock_client = MagicMock()
        mock_mcp_client.return_value = mock_client

        # Create AgentBay instance
        agent_bay = AgentBay()

        # Verify results
        self.assertEqual(agent_bay.api_key, "test-api-key")
        self.assertEqual(agent_bay.client, mock_client)
        self.assertDictEqual(agent_bay._sessions, {})
        self.assertIsNotNone(agent_bay._lock)
        self.assertIsNotNone(agent_bay.context)

    @patch("agentbay.agentbay.load_config")
    @patch("agentbay.agentbay.mcp_client")
    def test_initialization_with_provided_key(self, mock_mcp_client, mock_load_config):
        """Test initializing AgentBay with a provided API key"""
        # Mock configuration
        mock_load_config.return_value = {
            "endpoint": "another.endpoint.com",
            "timeout_ms": 60000,
        }

        # Mock client
        mock_client = MagicMock()
        mock_mcp_client.return_value = mock_client

        # Create AgentBay instance
        agent_bay = AgentBay(api_key="provided-api-key")

        # Verify results
        self.assertEqual(agent_bay.api_key, "provided-api-key")

    @patch.dict(os.environ, {}, clear=True)
    @patch("agentbay.agentbay.load_config")
    def test_initialization_without_api_key(self, mock_load_config):
        """Test initialization failure when no API key is available"""
        # Mock configuration
        mock_load_config.return_value = {
            "endpoint": "test.endpoint.com",
            "timeout_ms": 30000,
        }

        # Test initialization failure
        with self.assertRaises(ValueError) as context:
            AgentBay()

        self.assertIn("API key is required", str(context.exception))

    @patch("agentbay.agentbay.extract_request_id")
    @patch("agentbay.agentbay.load_config")
    @patch("agentbay.agentbay.mcp_client")
    def test_create_session_success(
        self, mock_mcp_client, mock_load_config, mock_extract_request_id
    ):
        """Test successfully creating a session"""
        # Mock configuration and request ID
        mock_load_config.return_value = {
            "region_id": "cn-shanghai",
            "endpoint": "test.endpoint.com",
            "timeout_ms": 30000,
        }
        mock_extract_request_id.return_value = "create-request-id"

        # Mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "Data": {
                    "SessionId": "new-session-id",
                    "ResourceUrl": "http://resource.url",
                }
            }
        }
        mock_client.create_mcp_session.return_value = mock_response
        mock_mcp_client.return_value = mock_client

        # Create AgentBay instance and session parameters
        agent_bay = AgentBay(api_key="test-key")
        params = CreateSessionParams(labels={"env": "test"})

        # Test creating a session
        result = agent_bay.create(params)

        # Verify results
        self.assertEqual(result.request_id, "create-request-id")
        self.assertIsNotNone(result.session)
        self.assertEqual(result.session.session_id, "new-session-id")


        # Verify session was added to the internal dictionary
        self.assertIn("new-session-id", agent_bay._sessions)
        self.assertEqual(agent_bay._sessions["new-session-id"], result.session)

    @patch("agentbay.agentbay.load_config")
    @patch("agentbay.agentbay.mcp_client")
    def test_create_session_invalid_response(self, mock_mcp_client, mock_load_config):
        """Test handling invalid response when creating a session"""
        # Mock configuration
        mock_load_config.return_value = {
            "endpoint": "test.endpoint.com",
            "timeout_ms": 30000,
        }

        # Mock client and invalid response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {"Data": None}  # Invalid Data field
        }
        mock_client.create_mcp_session.return_value = mock_response
        mock_mcp_client.return_value = mock_client

        # Create AgentBay instance
        agent_bay = AgentBay(api_key="test-key")

        # Test session creation with invalid response
        result = agent_bay.create()

        # Verify the result indicates failure
        self.assertFalse(result.success)
        self.assertIsNone(result.session)
        self.assertIn("Invalid response format", result.error_message)

    @patch("agentbay.agentbay.extract_request_id")
    @patch("agentbay.agentbay.load_config")
    @patch("agentbay.agentbay.mcp_client")
    def test_list_by_labels(
        self, mock_mcp_client, mock_load_config, mock_extract_request_id
    ):
        """Test listing sessions by labels"""
        # Mock configuration and request ID
        mock_load_config.return_value = {
            "region_id": "cn-shanghai",
            "endpoint": "test.endpoint.com",
            "timeout_ms": 30000,
        }
        mock_extract_request_id.return_value = "list-request-id"

        # Mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "Data": [
                    {"SessionId": "session-1"},
                    {"SessionId": "session-2"},
                ]
            }
        }
        mock_client.list_session.return_value = mock_response
        mock_mcp_client.return_value = mock_client

        # Create AgentBay instance
        agent_bay = AgentBay(api_key="test-key")

        # Create ListSessionParams object with labels
        params = ListSessionParams(labels={"env": "prod", "app": "test"})

        # Test listing sessions by labels
        result = agent_bay.list_by_labels(params)

        # Verify results
        self.assertEqual(result.request_id, "list-request-id")
        self.assertEqual(len(result.session_ids), 2)
        self.assertEqual(result.session_ids[0], "session-1")
        self.assertEqual(result.session_ids[1], "session-2")

        # Verify cached sessions
        self.assertEqual(len(agent_bay._sessions), 2)
        self.assertIn("session-1", agent_bay._sessions)
        self.assertIn("session-2", agent_bay._sessions)

    @patch("agentbay.agentbay.extract_request_id")
    @patch("agentbay.agentbay.load_config")
    @patch("agentbay.agentbay.mcp_client")
    def test_list(
        self, mock_mcp_client, mock_load_config, mock_extract_request_id
    ):
        """Test listing sessions using the new list API"""
        # Mock configuration and request ID
        mock_load_config.return_value = {
            "region_id": "cn-shanghai",
            "endpoint": "test.endpoint.com",
            "timeout_ms": 30000,
        }
        mock_extract_request_id.return_value = "list-request-id"

        # Mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "Success": True,
                "Data": [
                    {"SessionId": "session-1"},
                    {"SessionId": "session-2"},
                    {"SessionId": "session-3"},
                ],
                "TotalCount": 3,
                "MaxResults": 10,
            }
        }
        mock_client.list_session.return_value = mock_response
        mock_mcp_client.return_value = mock_client

        # Create AgentBay instance
        agent_bay = AgentBay(api_key="test-key")

        # Test listing all sessions (no labels)
        result = agent_bay.list()
        self.assertEqual(result.request_id, "list-request-id")
        self.assertEqual(len(result.session_ids), 3)
        self.assertEqual(result.total_count, 3)
        self.assertTrue(result.success)

        # Test listing sessions with labels
        result = agent_bay.list(labels={"env": "prod"})
        self.assertEqual(result.request_id, "list-request-id")
        self.assertEqual(len(result.session_ids), 3)

        # Test listing sessions with pagination
        result = agent_bay.list(labels={"env": "prod"}, page=1, limit=2)
        self.assertEqual(result.request_id, "list-request-id")
        self.assertEqual(len(result.session_ids), 3)

    @patch("agentbay.agentbay.extract_request_id")
    @patch("agentbay.agentbay.load_config")
    @patch("agentbay.agentbay.mcp_client")
    def test_list_pagination(
        self, mock_mcp_client, mock_load_config, mock_extract_request_id
    ):
        """Test list API pagination logic"""
        # Mock configuration and request ID
        mock_load_config.return_value = {
            "region_id": "cn-shanghai",
            "endpoint": "test.endpoint.com",
            "timeout_ms": 30000,
        }
        mock_extract_request_id.return_value = "list-request-id"

        # Mock client and responses for pagination
        mock_client = MagicMock()

        # First page response
        mock_response_page1 = MagicMock()
        mock_response_page1.to_map.return_value = {
            "body": {
                "Success": True,
                "Data": [{"SessionId": "session-1"}, {"SessionId": "session-2"}],
                "TotalCount": 4,
                "MaxResults": 2,
                "NextToken": "token-page2",
            }
        }

        # Second page response
        mock_response_page2 = MagicMock()
        mock_response_page2.to_map.return_value = {
            "body": {
                "Success": True,
                "Data": [{"SessionId": "session-3"}, {"SessionId": "session-4"}],
                "TotalCount": 4,
                "MaxResults": 2,
                "NextToken": "",
            }
        }

        # Set up mock to return different responses
        mock_client.list_session.side_effect = [
            mock_response_page1,
            mock_response_page2,
        ]
        mock_mcp_client.return_value = mock_client

        # Create AgentBay instance
        agent_bay = AgentBay(api_key="test-key")

        # Test getting page 2
        result = agent_bay.list(labels={"env": "prod"}, page=2, limit=2)
        self.assertEqual(result.request_id, "list-request-id")
        self.assertEqual(len(result.session_ids), 2)
        self.assertEqual(result.session_ids[0], "session-3")
        self.assertEqual(result.session_ids[1], "session-4")

    @patch("agentbay.agentbay.extract_request_id")
    @patch("agentbay.agentbay.load_config")
    @patch("agentbay.agentbay.mcp_client")
    def test_create_session_with_policy_id(self, mock_mcp_client, mock_load_config, mock_extract_request_id):
        """Ensure policy_id is passed to create_mcp_session body"""
        mock_load_config.return_value = {
            "region_id": "cn-shanghai",
            "endpoint": "test.endpoint.com",
            "timeout_ms": 30000,
        }
        mock_extract_request_id.return_value = "create-request-id"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "Data": {
                    "SessionId": "new-session-id",
                    "ResourceUrl": "http://resource.url",
                },
                "RequestId": "create-request-id",
            }
        }
        mock_client.create_mcp_session.return_value = mock_response
        mock_mcp_client.return_value = mock_client

        agent_bay = AgentBay(api_key="test-key")
        params = CreateSessionParams(policy_id="policy-xyz")

        result = agent_bay.create(params)
        self.assertTrue(result.success)
        mock_client.create_mcp_session.assert_called_once()
        call_arg = mock_client.create_mcp_session.call_args[0][0]
        # Ensure policy_id is carried on the request object; client will include it in request body
        self.assertEqual(getattr(call_arg, "mcp_policy_id", None) or getattr(call_arg, "McpPolicyId", None), "policy-xyz")
        # Basic success assertion remains; deep body behavior is validated in client integration tests

    @patch("agentbay.agentbay.load_config")
    @patch("agentbay.agentbay.mcp_client")
    def test_create_with_mobile_extra_configs(self, mock_mcp_client, mock_load_config):
        """Test creating a session with mobile extra configurations"""
        # Mock configuration
        mock_load_config.return_value = {
            "endpoint": "test.endpoint.com",
            "timeout_ms": 30000,
        }

        # Mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "Data": {
                    "SessionId": "mobile-session-id",
                    "ResourceUrl": "http://mobile.resource.url",
                },
                "RequestId": "mobile-create-request-id",
            }
        }
        mock_client.create_mcp_session.return_value = mock_response
        mock_mcp_client.return_value = mock_client

        # Create mobile configuration
        app_rule = AppManagerRule(
            rule_type="White",
            app_package_name_list=["com.allowed.app", "com.trusted.service"]
        )
        mobile_config = MobileExtraConfig(
            lock_resolution=True,
            app_manager_rule=app_rule
        )
        extra_configs = ExtraConfigs(mobile=mobile_config)

        agent_bay = AgentBay(api_key="test-key")
        params = CreateSessionParams(
            labels={"project": "mobile-testing"},
            extra_configs=extra_configs
        )

        result = agent_bay.create(params)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.session)
        if result.session:
            self.assertEqual(result.session.session_id, "mobile-session-id")
        
        # Verify the client was called with extra configs
        mock_client.create_mcp_session.assert_called_once()
        call_arg = mock_client.create_mcp_session.call_args[0][0]
        
        # Check that extra_configs is present in the request
        self.assertIsNotNone(call_arg.extra_configs)
        self.assertIsNotNone(call_arg.extra_configs.mobile)
        self.assertTrue(call_arg.extra_configs.mobile.lock_resolution)
        self.assertEqual(call_arg.extra_configs.mobile.app_manager_rule.rule_type, "White")
        self.assertEqual(len(call_arg.extra_configs.mobile.app_manager_rule.app_package_name_list), 2)

    @patch("agentbay.agentbay.load_config")
    @patch("agentbay.agentbay.mcp_client")
    def test_create_with_mobile_blacklist_config(self, mock_mcp_client, mock_load_config):
        """Test creating a session with mobile blacklist configuration"""
        # Mock configuration
        mock_load_config.return_value = {
            "endpoint": "test.endpoint.com",
            "timeout_ms": 30000,
        }

        # Mock client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_map.return_value = {
            "body": {
                "Data": {
                    "SessionId": "secure-session-id",
                    "ResourceUrl": "http://secure.resource.url",
                },
                "RequestId": "secure-create-request-id",
            }
        }
        mock_client.create_mcp_session.return_value = mock_response
        mock_mcp_client.return_value = mock_client

        # Create mobile blacklist configuration
        app_rule = AppManagerRule(
            rule_type="Black",
            app_package_name_list=["com.malware.app", "com.blocked.service"]
        )
        mobile_config = MobileExtraConfig(
            lock_resolution=False,
            app_manager_rule=app_rule
        )
        extra_configs = ExtraConfigs(mobile=mobile_config)

        agent_bay = AgentBay(api_key="test-key")
        params = CreateSessionParams(
            labels={"project": "security-testing"},
            extra_configs=extra_configs
        )

        result = agent_bay.create(params)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.session)
        if result.session:
            self.assertEqual(result.session.session_id, "secure-session-id")
        
        # Verify the client was called with blacklist extra configs
        mock_client.create_mcp_session.assert_called_once()
        call_arg = mock_client.create_mcp_session.call_args[0][0]
        
        # Check that extra_configs with blacklist is present in the request
        self.assertIsNotNone(call_arg.extra_configs)
        self.assertIsNotNone(call_arg.extra_configs.mobile)
        self.assertFalse(call_arg.extra_configs.mobile.lock_resolution)
        self.assertEqual(call_arg.extra_configs.mobile.app_manager_rule.rule_type, "Black")
        self.assertIn("com.malware.app", call_arg.extra_configs.mobile.app_manager_rule.app_package_name_list)


if __name__ == "__main__":
    unittest.main()
