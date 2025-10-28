"""
Integration tests for Computer and Mobile modules.
Tests the integration with Session and actual usage patterns.
"""

import pytest
from unittest.mock import Mock, patch

from agentbay import AgentBay, Session
from agentbay.computer import Computer
from agentbay.mobile import Mobile


class TestComputerMobileIntegration:
    """Integration tests for Computer and Mobile modules."""

    def setup_method(self):
        """Set up test fixtures."""
        self.api_key = "test-api-key"

    def test_session_has_computer_and_mobile_modules(self):
        """Test that Session includes Computer and Mobile modules."""
        # Arrange - Create a mock AgentBay instance
        mock_agent_bay = Mock()
        
        # Act - Create a Session directly
        session = Session(mock_agent_bay, "test-session-123")

        # Assert
        assert hasattr(session, 'computer')
        assert hasattr(session, 'mobile')
        assert isinstance(session.computer, Computer)
        assert isinstance(session.mobile, Mobile)

    def test_computer_module_usage_in_session(self):
        """Test Computer module usage through Session."""
        # Arrange
        mock_agent_bay = Mock()
        session = Session(mock_agent_bay, "test-session-123")

        # Mock the MCP tool call
        with patch.object(session.computer, '_call_mcp_tool') as mock_mcp:
            mock_mcp_result = Mock()
            mock_mcp_result.success = True
            mock_mcp_result.request_id = "test-123"
            mock_mcp.return_value = mock_mcp_result

            # Act
            result = session.computer.click_mouse(100, 200)

            # Assert
            assert result.success is True
            mock_mcp.assert_called_once_with("click_mouse", {"x": 100, "y": 200, "button": "left"})

    def test_mobile_module_usage_in_session(self):
        """Test Mobile module usage through Session."""
        # Arrange
        mock_agent_bay = Mock()
        session = Session(mock_agent_bay, "test-session-123")

        # Mock the MCP tool call
        with patch.object(session.mobile, '_call_mcp_tool') as mock_mcp:
            mock_mcp_result = Mock()
            mock_mcp_result.success = True
            mock_mcp_result.request_id = "test-123"
            mock_mcp.return_value = mock_mcp_result

            # Act
            result = session.mobile.tap(150, 250)

            # Assert
            assert result.success is True
            mock_mcp.assert_called_once_with("tap", {"x": 150, "y": 250})

    def test_computer_delegates_to_existing_modules(self):
        """Test that Computer module properly delegates to existing modules."""
        # Arrange
        mock_agent_bay = Mock()
        session = Session(mock_agent_bay, "test-session-123")

        # Mock the ApplicationManager
        with patch('agentbay.application.ApplicationManager') as mock_app_manager:
            mock_instance = Mock()
            mock_result = Mock()
            mock_result.success = True
            mock_instance.get_installed_apps.return_value = mock_result
            mock_app_manager.return_value = mock_instance

            # Act
            result = session.computer.get_installed_apps()

            # Assert
            assert result.success is True
            mock_instance.get_installed_apps.assert_called_once_with(False, True, True)

    def test_mobile_delegates_to_existing_modules(self):
        """Test that Mobile module properly delegates to existing modules."""
        # Arrange
        mock_agent_bay = Mock()
        session = Session(mock_agent_bay, "test-session-123")

        # Mock the ApplicationManager
        with patch('agentbay.application.ApplicationManager') as mock_app_manager:
            mock_instance = Mock()
            mock_result = Mock()
            mock_result.success = True
            mock_instance.get_installed_apps.return_value = mock_result
            mock_app_manager.return_value = mock_instance

            # Act
            result = session.mobile.get_installed_apps()

            # Assert
            assert result.success is True
            mock_instance.get_installed_apps.assert_called_once_with(False, True, True) 