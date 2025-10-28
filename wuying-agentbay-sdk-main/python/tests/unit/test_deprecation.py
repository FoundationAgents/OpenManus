"""
Unit tests for deprecation warnings.
Tests that deprecated APIs properly emit DeprecationWarning.
"""

import warnings
import pytest
from unittest.mock import Mock

from agentbay.window import WindowManager
from agentbay.ui import UI
from agentbay.application import ApplicationManager


class TestDeprecationWarnings:
    """Test cases for deprecation warnings."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()

    def test_window_manager_deprecation_warnings(self):
        """Test that WindowManager APIs emit deprecation warnings."""
        window_manager = WindowManager(self.mock_session)
        
        # Mock the MCP tool call to avoid actual API calls
        window_manager._call_mcp_tool = Mock()
        window_manager._call_mcp_tool.return_value = Mock(success=False, request_id="test", error_message="test")
        
        # Test that deprecated methods emit warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Call deprecated methods
            window_manager.activate_window(123)
            window_manager.maximize_window(123)
            window_manager.minimize_window(123)
            
            # Check that warnings were emitted
            assert len(w) == 3
            for warning in w:
                assert issubclass(warning.category, DeprecationWarning)
                assert "deprecated" in str(warning.message).lower()
                assert "Computer module" in str(warning.message)

    def test_ui_deprecation_warnings(self):
        """Test that UI APIs emit deprecation warnings."""
        ui = UI(self.mock_session)
        
        # Mock the MCP tool call
        ui._call_mcp_tool = Mock()
        ui._call_mcp_tool.return_value = Mock(success=False, request_id="test", error_message="test")
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Call deprecated methods
            ui.click(100, 200)
            ui.input_text("test")
            ui.screenshot()
            
            # Check that warnings were emitted
            assert len(w) == 3
            for warning in w:
                assert issubclass(warning.category, DeprecationWarning)
                assert "deprecated" in str(warning.message).lower()
                assert "platform-specific modules" in str(warning.message)

    def test_application_manager_deprecation_warnings(self):
        """Test that ApplicationManager APIs emit deprecation warnings."""
        app_manager = ApplicationManager(self.mock_session)
        
        # Mock the MCP tool call
        app_manager._call_mcp_tool = Mock()
        app_manager._call_mcp_tool.return_value = Mock(success=False, request_id="test", error_message="test")
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Call deprecated methods
            app_manager.get_installed_apps(True, True, True)
            app_manager.start_app("test_app")
            app_manager.stop_app_by_pname("test_process")
            
            # Check that warnings were emitted
            assert len(w) == 3
            for warning in w:
                assert issubclass(warning.category, DeprecationWarning)
                assert "deprecated" in str(warning.message).lower()
                assert "platform-specific modules" in str(warning.message)

    def test_list_visible_apps_now_deprecated(self):
        """Test that list_visible_apps is NOW deprecated."""
        app_manager = ApplicationManager(self.mock_session)
        
        # Mock the MCP tool call
        app_manager._call_mcp_tool = Mock()
        app_manager._call_mcp_tool.return_value = Mock(success=False, request_id="test", error_message="test")
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Call the method that should NOW be deprecated
            app_manager.list_visible_apps()
            
            # Check that a warning was emitted
            assert len(w) == 1
            warning = w[0]
            assert issubclass(warning.category, DeprecationWarning)
            assert "deprecated" in str(warning.message).lower()
            assert "session.computer.list_visible_apps()" in str(warning.message)

    def test_deprecation_message_content(self):
        """Test that deprecation messages contain proper replacement information."""
        window_manager = WindowManager(self.mock_session)
        window_manager._call_mcp_tool = Mock()
        window_manager._call_mcp_tool.return_value = Mock(success=False, request_id="test", error_message="test")
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            window_manager.activate_window(123)
            
            # Check warning message content
            warning_message = str(w[0].message)
            assert "activate_window" in warning_message
            assert "deprecated" in warning_message.lower()
            assert "session.computer.activate_window()" in warning_message
            assert "2.0.0" in warning_message 