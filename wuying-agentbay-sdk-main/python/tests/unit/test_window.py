import json
import unittest
from unittest.mock import MagicMock

from agentbay.window import Window, WindowManager


class TestWindow(unittest.TestCase):
    """Test the basic functionality of the Window class"""

    def test_window_initialization(self):
        """Test Window object initialization"""
        window = Window(
            window_id=1,
            title="Test Window",
            absolute_upper_left_x=100,
            absolute_upper_left_y=200,
            width=800,
            height=600,
            pid=12345,
            pname="test_process",
        )

        self.assertEqual(window.window_id, 1)
        self.assertEqual(window.title, "Test Window")
        self.assertEqual(window.absolute_upper_left_x, 100)
        self.assertEqual(window.absolute_upper_left_y, 200)
        self.assertEqual(window.width, 800)
        self.assertEqual(window.height, 600)
        self.assertEqual(window.pid, 12345)
        self.assertEqual(window.pname, "test_process")
        self.assertEqual(window.child_windows, [])

    def test_window_from_dict(self):
        """Test creating a Window object from a dictionary"""
        window_dict = {
            "window_id": 2,
            "title": "Parent Window",
            "absolute_upper_left_x": 50,
            "absolute_upper_left_y": 60,
            "width": 1024,
            "height": 768,
            "pid": 54321,
            "pname": "parent_process",
            "child_windows": [
                {
                    "window_id": 3,
                    "title": "Child Window",
                    "absolute_upper_left_x": 100,
                    "absolute_upper_left_y": 120,
                    "width": 400,
                    "height": 300,
                    "pid": 54322,
                    "pname": "child_process",
                }
            ],
        }

        window = Window.from_dict(window_dict)

        self.assertEqual(window.window_id, 2)
        self.assertEqual(window.title, "Parent Window")
        self.assertEqual(window.absolute_upper_left_x, 50)
        self.assertEqual(window.absolute_upper_left_y, 60)
        self.assertEqual(window.width, 1024)
        self.assertEqual(window.height, 768)
        self.assertEqual(window.pid, 54321)
        self.assertEqual(window.pname, "parent_process")
        self.assertEqual(len(window.child_windows), 1)

        child_window = window.child_windows[0]
        self.assertEqual(child_window.window_id, 3)
        self.assertEqual(child_window.title, "Child Window")


class TestWindowManager(unittest.TestCase):
    """Test the methods of the WindowManager class"""

    def setUp(self):
        """Set up test environment"""
        self.session = MagicMock()
        self.window_manager = WindowManager(self.session)

        # Create a successful response template
        self.success_result = MagicMock()
        self.success_result.success = True
        self.success_result.request_id = "test-request-id"

        # Create a failed response template
        self.failed_result = MagicMock()
        self.failed_result.success = False
        self.failed_result.request_id = "test-request-id"
        self.failed_result.error_message = "Operation failed"

    def test_list_root_windows_success(self):
        """Test successfully retrieving root windows list"""
        # Prepare test data
        windows_data = [
            {
                "window_id": 1,
                "title": "Window 1",
                "absolute_upper_left_x": 0,
                "absolute_upper_left_y": 0,
                "width": 800,
                "height": 600,
            },
            {
                "window_id": 2,
                "title": "Window 2",
                "absolute_upper_left_x": 100,
                "absolute_upper_left_y": 100,
                "width": 400,
                "height": 300,
            },
        ]

        # Mock _call_mcp_tool method to return success result
        self.success_result.data = json.dumps(windows_data)
        self.window_manager._call_mcp_tool = MagicMock(return_value=self.success_result)

        # Call the test method
        result = self.window_manager.list_root_windows()

        # Verify the results
        self.assertTrue(result.success)
        self.assertEqual(len(result.windows), 2)
        self.assertEqual(result.windows[0].window_id, 1)
        self.assertEqual(result.windows[0].title, "Window 1")
        self.assertEqual(result.windows[1].window_id, 2)
        self.assertEqual(result.windows[1].title, "Window 2")

    def test_list_root_windows_failure(self):
        """Test failure when retrieving root windows list"""
        # Mock _call_mcp_tool method to return failed result
        self.window_manager._call_mcp_tool = MagicMock(return_value=self.failed_result)

        # Call the test method
        result = self.window_manager.list_root_windows()

        # Verify the results
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Operation failed")

    def test_get_active_window_success(self):
        """Test successfully retrieving active window"""
        # Prepare test data
        active_window = {
            "window_id": 3,
            "title": "Active Window",
            "absolute_upper_left_x": 50,
            "absolute_upper_left_y": 50,
            "width": 1024,
            "height": 768,
            "pid": 12345,
            "pname": "active_process",
        }

        # Mock _call_mcp_tool method to return success result
        self.success_result.data = json.dumps(active_window)
        self.window_manager._call_mcp_tool = MagicMock(return_value=self.success_result)

        # Call the test method
        result = self.window_manager.get_active_window()

        # Verify the results
        self.assertTrue(result.success)
        self.assertEqual(result.window.window_id, 3)
        self.assertEqual(result.window.title, "Active Window")
        self.assertEqual(result.window.pid, 12345)

    def test_window_operations(self):
        """Test window operation methods"""
        # Mock _call_mcp_tool method to return success result
        self.window_manager._call_mcp_tool = MagicMock(return_value=self.success_result)

        # Test activate window
        result = self.window_manager.activate_window(1)
        self.assertTrue(result.success)
        self.window_manager._call_mcp_tool.assert_called_with(
            "activate_window", {"window_id": 1}
        )

        # Test maximize window
        result = self.window_manager.maximize_window(1)
        self.assertTrue(result.success)
        self.window_manager._call_mcp_tool.assert_called_with(
            "maximize_window", {"window_id": 1}
        )

        # Test minimize window
        result = self.window_manager.minimize_window(1)
        self.assertTrue(result.success)
        self.window_manager._call_mcp_tool.assert_called_with(
            "minimize_window", {"window_id": 1}
        )

        # Test restore window
        result = self.window_manager.restore_window(1)
        self.assertTrue(result.success)
        self.window_manager._call_mcp_tool.assert_called_with(
            "restore_window", {"window_id": 1}
        )

    def test_window_operations_error_handling(self):
        """Test error handling for window operations"""
        # Mock _call_mcp_tool method to throw an exception
        self.window_manager._call_mcp_tool = MagicMock(
            side_effect=Exception("Operation exception")
        )

        # Test activate window error handling
        result = self.window_manager.activate_window(1)
        self.assertFalse(result.success)
        self.assertIn("Failed to activate window", result.error_message)


if __name__ == "__main__":
    unittest.main()
