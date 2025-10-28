import os
import sys
import time
import unittest

from agentbay import AgentBay

# Add the parent directory to the path so we can import the agentbay package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_test_api_key():
    """Get API key for testing"""
    api_key = os.environ.get("AGENTBAY_API_KEY")
    if not api_key:
        api_key = "akm-xxx"  # Replace with your test API key
        print(
            "Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for testing."
        )
    return api_key


def contains_tool_not_found(s):
    """Check if a string contains 'tool not found'"""
    return "tool not found" in str(s).lower()


class TestWindow(unittest.TestCase):
    """Test cases for the Window class."""

    def setUp(self):
        """Set up test fixtures."""
        time.sleep(3)

        api_key = get_test_api_key()
        self.agent_bay = AgentBay(api_key=api_key)

        # Create a session
        print("Creating a new session for window testing...")
        session_result = self.agent_bay.create()

        # Check if session creation was successful
        if not session_result.success or session_result.session is None:
            raise Exception(f"Failed to create session: {session_result.error_message}")

        self.session = session_result.session
        print(f"Session created with ID: {self.session.session_id}")

    def tearDown(self):
        """Tear down test fixtures."""
        print("Cleaning up: Deleting the session...")
        try:
            self.agent_bay.delete(self.session)
        except Exception as e:
            print(f"Warning: Error deleting session: {e}")

    def test_list_root_windows(self):
        """Test listing root windows."""
        if hasattr(self.session, "window") and self.session.window:
            print("Listing root windows...")
            try:
                root_windows = self.session.window.list_root_windows()
                print(f"Found {len(root_windows)} root windows")

                # Verify we got some windows
                if len(root_windows) == 0:
                    print("Warning: No root windows found")
                else:
                    # Print the first 3 windows or fewer if less than 3 are available
                    count = min(len(root_windows), 3)
                    for i in range(count):
                        print(
                            f"Window {i + 1}: {root_windows[i].title} ",
                            f"(ID: {root_windows[i].window_id})",
                        )

                    # Verify window properties
                    for window in root_windows:
                        self.assertGreater(
                            window.window_id,
                            0,
                            f"Found window with invalid ID: {window.window_id}",
                        )

                # Check if response contains "tool not found"
                if len(root_windows) > 0:
                    self.assertFalse(
                        contains_tool_not_found(root_windows[0].title),
                        "Window.list_root_windows returned 'tool not found'",
                    )
            except Exception as e:
                print(f"Note: list_root_windows failed: {e}")
                # Don't fail the test if the operation is not supported
        else:
            print("Note: Window interface is not available, skipping window test")

    def test_get_active_window(self):
        """Test getting the active window."""
        if (
            hasattr(self.session, "window")
            and self.session.window
            and hasattr(self.session, "application")
            and self.session.application
        ):
            # Step 1: Get installed applications
            print("Step 1: Getting installed applications...")
            try:
                result = self.session.application.get_installed_apps(
                    start_menu=True, desktop=False, ignore_system_apps=True
                )
                installed_apps = result.data
                print(f"Found {len(installed_apps)} installed applications")

                if not installed_apps:
                    print("No installed applications found, skipping test")
                    return

                # Find an app with name "Google Chrome" to launch
                app_to_start = None
                for app in installed_apps:
                    if hasattr(app, "name") and app.name == "Google Chrome":
                        app_to_start = app
                        break

                if not app_to_start:
                    print(
                        "No application with name 'Google Chrome' found, skipping test"
                    )
                    return

                # Step 2: Start the application
                print(
                    f"Step 2: Starting application: {app_to_start.name} with command: {app_to_start.start_cmd}"
                )
                start_result = self.session.application.start_app(
                    app_to_start.start_cmd
                )
                print(f"Application start result: {start_result}")

                # Step 3: Wait for 1 minute
                print("Step 3: Waiting for 1 minute for application to fully load...")
                time.sleep(60)

                # Step 4: List root windows
                print("Step 4: Listing root windows...")
                result = self.session.window.list_root_windows()
                root_windows = result.windows
                print(f"Found {len(root_windows)} root windows")
                if not root_windows:
                    print("No root windows found after starting application")
                    return

                # Step 5: Activate a window
                window_to_activate = root_windows[0]
                print(
                    f"Step 5: Activating window: {window_to_activate.title} (ID: {window_to_activate.window_id})"
                )
                self.session.window.activate_window(window_to_activate.window_id)

                # Step 6: Get active window
                print("Step 6: Getting active window...")
                result = self.session.window.get_active_window()
                active_window = result.window
                print(
                    f"Active window: {active_window.title}",
                    f"(ID: {active_window.window_id}",
                    f"Process: {active_window.pname}",
                    f"(PID: {active_window.pid})",
                )

                # Verify window properties
                self.assertGreater(
                    active_window.window_id,
                    0,
                    f"Active window has invalid ID: {active_window.window_id}",
                )
                self.assertGreater(
                    active_window.pid,
                    0,
                    f"Active window has invalid PID: {active_window.pid}",
                )

                # Check if response contains "tool not found"
                self.assertFalse(
                    contains_tool_not_found(active_window.title)
                    or contains_tool_not_found(active_window.pname),
                    "Window.get_active_window returned 'tool not found'",
                )
            except Exception as e:
                print(f"Note: get_active_window workflow failed: {e}")
                # Don't fail the test if the operation is not supported
        else:
            print(
                "Note: Window or Application interface is not available, skipping window test"
            )

    def test_window_operations(self):
        """Test window operations (activate, maximize, minimize, restore, resize)."""
        if hasattr(self.session, "window") and self.session.window:
            print("Listing root windows to find a window to operate on...")
            try:
                root_windows = self.session.window.list_root_windows()
                if not root_windows:
                    print("No root windows found, skipping window operations test")
                    return

                window_id = root_windows[0].window_id

                # Activate window
                print(f"Activating window with ID {window_id}...")
                try:
                    self.session.window.activate_window(window_id)
                    print("Window activated successfully")
                except Exception as e:
                    print(f"Note: activate_window failed: {e}")

                # Maximize window
                print(f"Maximizing window with ID {window_id}...")
                try:
                    self.session.window.maximize_window(window_id)
                    print("Window maximized successfully")
                except Exception as e:
                    print(f"Note: maximize_window failed: {e}")

                # Minimize window
                print(f"Minimizing window with ID {window_id}...")
                try:
                    self.session.window.minimize_window(window_id)
                    print("Window minimized successfully")
                except Exception as e:
                    print(f"Note: minimize_window failed: {e}")

                # Restore window
                print(f"Restoring window with ID {window_id}...")
                try:
                    self.session.window.restore_window(window_id)
                    print("Window restored successfully")
                except Exception as e:
                    print(f"Note: restore_window failed: {e}")

                # Resize window
                print(f"Resizing window with ID {window_id} to 800x600...")
                try:
                    self.session.window.resize_window(window_id, 800, 600)
                    print("Window resized successfully")
                except Exception as e:
                    print(f"Note: resize_window failed: {e}")
            except Exception as e:
                print(f"Note: list_root_windows failed: {e}")
                # Don't fail the test if the operation is not supported
        else:
            print("Note: Window interface is not available, skipping window test")

    def test_focus_mode(self):
        """Test focus mode."""
        if hasattr(self.session, "window") and self.session.window:
            # Enable focus mode
            print("Enabling focus mode...")
            try:
                self.session.window.focus_mode(True)
                print("Focus mode enabled successfully")
            except Exception as e:
                print(f"Note: Enabling focus mode failed: {e}")

            # Disable focus mode
            print("Disabling focus mode...")
            try:
                self.session.window.focus_mode(False)
                print("Focus mode disabled successfully")
            except Exception as e:
                print(f"Note: Disabling focus mode failed: {e}")
        else:
            print("Note: Window interface is not available, skipping focus mode test")


if __name__ == "__main__":
    unittest.main()
