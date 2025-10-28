"""
Unit tests for Mobile module.
Following TDD principles - tests first, then implementation.
"""

import pytest
from unittest.mock import Mock, patch

from agentbay.mobile import Mobile
from agentbay.model import BoolResult, OperationResult
from agentbay.application.application import ProcessListResult, AppOperationResult
from agentbay.exceptions import AgentBayError


class TestMobile:
    """Test cases for Mobile module."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.mobile = Mobile(self.mock_session)

    def test_mobile_initialization(self):
        """Test Mobile module initialization."""
        assert self.mobile.session == self.mock_session

    # Touch Operations Tests
    def test_tap_success(self):
        """Test successful tap."""
        # Arrange
        mock_result = Mock()
        mock_result.success = True
        mock_result.request_id = "test-123"
        mock_result.error_message = ""
        
        self.mobile._call_mcp_tool = Mock(return_value=mock_result)
        
        # Act
        result = self.mobile.tap(100, 200)
        
        # Assert
        assert isinstance(result, BoolResult)
        assert result.success is True
        assert result.data is True
        self.mobile._call_mcp_tool.assert_called_once_with(
            "tap", {"x": 100, "y": 200}
        )

    def test_swipe_success(self):
        """Test successful swipe."""
        # Arrange
        mock_result = Mock()
        mock_result.success = True
        mock_result.request_id = "test-123"
        
        self.mobile._call_mcp_tool = Mock(return_value=mock_result)
        
        # Act
        result = self.mobile.swipe(100, 100, 200, 200)
        
        # Assert
        assert isinstance(result, BoolResult)
        assert result.success is True
        self.mobile._call_mcp_tool.assert_called_once_with(
            "swipe", {
                "start_x": 100, "start_y": 100,
                "end_x": 200, "end_y": 200,
                "duration_ms": 300
            }
        )

    def test_swipe_with_duration(self):
        """Test swipe with custom duration."""
        # Arrange
        mock_result = Mock()
        mock_result.success = True
        mock_result.request_id = "test-123"
        
        self.mobile._call_mcp_tool = Mock(return_value=mock_result)
        
        # Act
        result = self.mobile.swipe(100, 100, 200, 200, duration_ms=500)
        
        # Assert
        self.mobile._call_mcp_tool.assert_called_once_with(
            "swipe", {
                "start_x": 100, "start_y": 100,
                "end_x": 200, "end_y": 200,
                "duration_ms": 500
            }
        )

    def test_input_text_success(self):
        """Test successful text input."""
        # Arrange
        mock_result = Mock()
        mock_result.success = True
        mock_result.request_id = "test-123"
        
        self.mobile._call_mcp_tool = Mock(return_value=mock_result)
        
        # Act
        result = self.mobile.input_text("Hello Mobile")
        
        # Assert
        assert isinstance(result, BoolResult)
        assert result.success is True
        self.mobile._call_mcp_tool.assert_called_once_with(
            "input_text", {"text": "Hello Mobile"}
        )

    def test_send_key_success(self):
        """Test successful key send."""
        # Arrange
        mock_result = Mock()
        mock_result.success = True
        mock_result.request_id = "test-123"
        
        self.mobile._call_mcp_tool = Mock(return_value=mock_result)
        
        # Act
        result = self.mobile.send_key(4)  # BACK key
        
        # Assert
        assert isinstance(result, BoolResult)
        assert result.success is True
        self.mobile._call_mcp_tool.assert_called_once_with(
            "send_key", {"key": 4}
        )

    # UI Elements Tests
    def test_get_clickable_ui_elements_success(self):
        """Test successful clickable UI elements retrieval."""
        # Arrange
        mock_result = Mock()
        mock_result.success = True
        mock_result.request_id = "test-123"
        mock_result.data = [{"id": "button1", "text": "Click me"}]
        
        self.mobile._call_mcp_tool = Mock(return_value=mock_result)
        
        # Act
        result = self.mobile.get_clickable_ui_elements()
        
        # Assert
        assert result.success is True
        assert len(result.elements) == 1
        assert result.elements[0]["id"] == "button1"
        self.mobile._call_mcp_tool.assert_called_once_with(
            "get_clickable_ui_elements", {"timeout_ms": 2000}
        )

    def test_get_clickable_ui_elements_with_timeout(self):
        """Test clickable UI elements with custom timeout."""
        # Arrange
        mock_result = Mock()
        mock_result.success = True
        mock_result.request_id = "test-123"
        mock_result.data = []
        
        self.mobile._call_mcp_tool = Mock(return_value=mock_result)
        
        # Act
        result = self.mobile.get_clickable_ui_elements(timeout_ms=5000)
        
        # Assert
        self.mobile._call_mcp_tool.assert_called_once_with(
            "get_clickable_ui_elements", {"timeout_ms": 5000}
        )

    def test_get_all_ui_elements_success(self):
        """Test successful all UI elements retrieval."""
        # Arrange
        mock_result = Mock()
        mock_result.success = True
        mock_result.request_id = "test-123"
        mock_result.data = [
            {"id": "button1", "text": "Click me"},
            {"id": "text1", "text": "Hello"}
        ]
        
        self.mobile._call_mcp_tool = Mock(return_value=mock_result)
        
        # Act
        result = self.mobile.get_all_ui_elements()
        
        # Assert
        assert result.success is True
        assert len(result.elements) == 2
        self.mobile._call_mcp_tool.assert_called_once_with(
            "get_all_ui_elements", {"timeout_ms": 2000}
        )

    # Application Management Tests
    def test_get_installed_apps_success(self):
        """Test successful installed apps retrieval."""
        # Arrange - Mock the _call_mcp_tool method
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = '[{"name": "Calculator", "package_name": "com.calculator"}]'
        mock_result.request_id = "test-123"
        
        self.mobile._call_mcp_tool = Mock(return_value=mock_result)
        
        # Act
        result = self.mobile.get_installed_apps(
            start_menu=False,
            desktop=True,
            ignore_system_apps=True
        )
        
        # Assert
        assert result.success is True
        assert len(result.data) == 1
        self.mobile._call_mcp_tool.assert_called_once_with(
            "get_installed_apps",
            {"start_menu": False, "desktop": True, "ignore_system_apps": True}
        )

    def test_get_installed_apps_with_options(self):
        """Test installed apps with custom options."""
        # Arrange - Mock the _call_mcp_tool method
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = '[]'
        mock_result.request_id = "test-123"
        
        self.mobile._call_mcp_tool = Mock(return_value=mock_result)
        
        # Act
        result = self.mobile.get_installed_apps(
            start_menu=True,
            desktop=False,
            ignore_system_apps=False
        )
        
        # Assert
        self.mobile._call_mcp_tool.assert_called_once_with(
            "get_installed_apps",
            {"start_menu": True, "desktop": False, "ignore_system_apps": False}
        )

    def test_start_app_success(self):
        """Test successful app start."""
        # Arrange
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = '[{"pid": 1234, "name": "calculator"}]'
        mock_result.request_id = "test-123"
        
        self.mobile._call_mcp_tool = Mock(return_value=mock_result)
        
        # Act
        result = self.mobile.start_app("com.android.calculator2")
        
        # Assert
        assert isinstance(result, ProcessListResult)
        assert result.success is True
        self.mobile._call_mcp_tool.assert_called_once_with(
            "start_app", {"start_cmd": "com.android.calculator2"}
        )

    def test_start_app_with_activity(self):
        """Test app start with specific activity."""
        # Arrange
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = '[{"pid": 1234, "name": "settings"}]'
        mock_result.request_id = "test-123"
        
        self.mobile._call_mcp_tool = Mock(return_value=mock_result)
        
        # Act
        result = self.mobile.start_app(
            "com.android.settings",
            activity=".MainActivity"
        )
        
        # Assert
        self.mobile._call_mcp_tool.assert_called_once_with(
            "start_app", {
                "start_cmd": "com.android.settings",
                "activity": ".MainActivity"
            }
        )

    def test_stop_app_by_cmd_success(self):
        """Test successful app stop by command."""
        # Arrange - Mock the _call_mcp_tool method
        mock_result = Mock()
        mock_result.success = True
        mock_result.request_id = "test-123"
        mock_result.error_message = ""
        
        self.mobile._call_mcp_tool = Mock(return_value=mock_result)
        
        # Act
        result = self.mobile.stop_app_by_cmd("com.android.calculator2")
        
        # Assert
        assert isinstance(result, AppOperationResult)
        assert result.success is True
        self.mobile._call_mcp_tool.assert_called_once_with(
            "stop_app_by_cmd", {"stop_cmd": "com.android.calculator2"}
        )

    # Screenshot Tests
    def test_screenshot_success(self):
        """Test successful screenshot."""
        # Arrange
        mock_result = Mock()
        mock_result.success = True
        mock_result.request_id = "test-123"
        mock_result.data = "/path/to/mobile_screenshot.png"
        
        self.mobile._call_mcp_tool = Mock(return_value=mock_result)
        
        # Act
        result = self.mobile.screenshot()
        
        # Assert
        assert isinstance(result, OperationResult)
        assert result.success is True
        assert result.data == "/path/to/mobile_screenshot.png"
        self.mobile._call_mcp_tool.assert_called_once_with("system_screenshot", {})

    # Error Handling Tests
    def test_tap_mcp_failure(self):
        """Test tap when MCP tool fails."""
        # Arrange
        mock_result = Mock()
        mock_result.success = False
        mock_result.request_id = "test-123"
        mock_result.error_message = "MCP tool failed"
        
        self.mobile._call_mcp_tool = Mock(return_value=mock_result)
        
        # Act
        result = self.mobile.tap(100, 200)
        
        # Assert
        assert isinstance(result, BoolResult)
        assert result.success is False
        assert result.error_message == "MCP tool failed"

    def test_tap_exception(self):
        """Test tap when exception occurs."""
        # Arrange
        self.mobile._call_mcp_tool = Mock(side_effect=Exception("Network error"))
        
        # Act
        result = self.mobile.tap(100, 200)
        
        # Assert
        assert isinstance(result, BoolResult)
        assert result.success is False
        assert "Failed to tap" in result.error_message

    def test_get_clickable_ui_elements_exception(self):
        """Test UI elements retrieval when exception occurs."""
        # Arrange
        self.mobile._call_mcp_tool = Mock(side_effect=Exception("Network error"))
        
        # Act
        result = self.mobile.get_clickable_ui_elements()
        
        # Assert
        assert result.success is False
        assert "Failed to get clickable UI elements" in result.error_message 