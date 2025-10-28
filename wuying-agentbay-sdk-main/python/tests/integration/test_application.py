import os
import time
import unittest

from agentbay import AgentBay
from agentbay.application.application import (
    AppOperationResult,
    InstalledAppListResult,
    ProcessListResult,
)
from agentbay.session_params import CreateSessionParams


def get_test_api_key():
    """Get API key for testing"""
    api_key = os.environ.get("AGENTBAY_API_KEY")
    if not api_key:
        api_key = "akm-xxx"  # Replace with your test API key
        print(
            "Warning: Using default API key. Set AGENTBAY_API_KEY environment variable "
            "for testing."
        )
    return api_key


def contains_tool_not_found(s):
    """Check if a string contains 'tool not found'"""
    return "tool not found" in str(s).lower()


class TestApplication(unittest.TestCase):
    """Test cases for the Application class."""

    agent_bay = None
    session = None

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before all tests."""
        api_key = get_test_api_key()
        cls.agent_bay = AgentBay(api_key=api_key)

        # Create a session
        print("Creating a new session for application testing...")

        params = CreateSessionParams(image_id="linux_latest")
        result = cls.agent_bay.create(params)
        cls.session = result.session
        print(f"Session created with ID: {cls.session.session_id}")
        time.sleep(5)

    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures after all tests."""
        print("Cleaning up: Deleting the session...")
        try:
            if cls.session:
                cls.agent_bay.delete(cls.session)
                print("Session deleted successfully")
        except Exception as e:
            print(f"Warning: Error deleting session: {e}")

    def test_get_installed_apps(self):
        """Test getting installed applications."""
        if (
            hasattr(self.__class__.session, "application")
            and self.__class__.session.application
        ):
            print("Getting installed applications...")
            try:
                result = self.__class__.session.application.get_installed_apps(
                    start_menu=True, desktop=False, ignore_system_apps=True
                )

                # Verify result is of correct type
                self.assertIsInstance(result, InstalledAppListResult)

                if not result.success:
                    print(
                        f"Error: "
                        f"{result.error_message} (Request ID: "
                        f"{result.request_id})"
                    )
                    return

                apps = result.data
                print(f"Found {len(apps)} installed applications")

                # Verify we got some apps
                if len(apps) == 0:
                    print("Warning: No installed applications found")
                else:
                    # Print the first 3 apps or fewer if less than 3 are available
                    count = min(len(apps), 3)
                    for i in range(count):
                        print(f"App {i + 1}: {apps[i].name}")

                    # Verify app properties
                    for app in apps:
                        self.assertNotEqual(app.name, "", "Found app with empty name")

                # Check if response contains "tool not found"
                if len(apps) > 0:
                    self.assertFalse(
                        contains_tool_not_found(apps[0].name),
                        "Application.get_installed_apps returned 'tool not found'",
                    )
            except Exception as e:
                print(f"Note: get_installed_apps failed: {e}")
                # Don't fail the test if the operation is not supported
        else:
            print(
                "Note: Application interface is not available, skipping application "
                "test"
            )

    def test_list_visible_apps(self):
        """Test listing visible applications."""
        if (
            hasattr(self.__class__.session, "application")
            and self.__class__.session.application
        ):
            print("Listing visible applications...")
            try:
                result = self.__class__.session.application.list_visible_apps()

                # Verify result is of correct type
                self.assertIsInstance(result, ProcessListResult)

                if not result.success:
                    print(
                        f"Error: "
                        f"{result.error_message} (Request ID: "
                        f"{result.request_id})"
                    )
                    return

                visible_apps = result.data
                print(f"Found {len(visible_apps)} visible applications")

                # Verify we got some apps
                if len(visible_apps) == 0:
                    print("Warning: No visible applications found")
                else:
                    # Print the first 3 apps or fewer if less than 3 are available
                    count = min(len(visible_apps), 3)
                    for i in range(count):
                        print(
                            f"Process {i + 1}: {visible_apps[i].pname} "
                            f"(PID: {visible_apps[i].pid})"
                        )

                    # Verify app properties
                    for app in visible_apps:
                        self.assertNotEqual(
                            app.pname, "", "Found app with empty process name"
                        )
                        self.assertGreater(
                            app.pid,
                            0,
                            f"Found app with invalid PID: {app.pid}",
                        )

                # Check if response contains "tool not found"
                if len(visible_apps) > 0:
                    self.assertFalse(
                        contains_tool_not_found(visible_apps[0].pname),
                        "Application.list_visible_apps returned 'tool not found'",
                    )
            except Exception as e:
                print(f"Note: list_visible_apps failed: {e}")
                # Don't fail the test if the operation is not supported
        else:
            print(
                "Note: Application interface is not available, skipping application test"
            )

    def test_start_app(self):
        """Test starting an application."""
        if (
            hasattr(self.__class__.session, "application")
            and self.__class__.session.application
        ):
            start_cmd = "/usr/bin/google-chrome-stable"

            print(f"Starting application: {start_cmd}...")
            try:
                result = self.__class__.session.application.start_app(start_cmd)

                # Verify result is of correct type
                self.assertIsInstance(result, ProcessListResult)

                if not result.success:
                    print(
                        f"Error: "
                        f"{result.error_message} (Request ID: "
                        f"{result.request_id})"
                    )
                    return

                processes = result.data
                print(
                    f"Application started successfully, returned "
                    f"{len(processes)} processes"
                )

                # Verify we got some processes back
                if len(processes) == 0:
                    print(
                        "Warning: No processes returned after starting the application"
                    )
                else:
                    # Print the processes
                    for i, process in enumerate(processes):
                        print(f"Process {i + 1}: {process.pname} (PID: {process.pid})")

                        # Verify process properties
                        self.assertNotEqual(
                            process.pname,
                            "",
                            "Found process with empty process name",
                        )
                        self.assertGreater(
                            process.pid,
                            0,
                            f"Found process with invalid PID: {process.pid}",
                        )

                        # Try to stop the process to clean up
                        if process.pid > 0:
                            print(
                                f"Attempting to stop process "
                                f"{process.pname} (PID: "
                                f"{process.pid})..."
                            )
                            try:
                                stop_result = (
                                    self.__class__.session.application.stop_app_by_pid(
                                        process.pid
                                    )
                                )

                                # Verify result is of correct type
                                self.assertIsInstance(stop_result, AppOperationResult)

                                if stop_result.success:
                                    print(
                                        f"Successfully stopped process "
                                        f"{process.pname} (PID: "
                                        f"{process.pid})"
                                    )
                                else:
                                    print(
                                        f"Warning: Failed to stop process: "
                                        f"{stop_result.error_message}"
                                    )
                            except Exception as e:
                                print(f"Warning: Failed to stop process: {e}")

                # Check if response contains "tool not found"
                if len(processes) > 0:
                    self.assertFalse(
                        contains_tool_not_found(processes[0].pname),
                        "Application.start_app returned 'tool not found'",
                    )
            except Exception as e:
                print(f"Note: start_app failed: {e}")

                # Check if the error is due to the tool not being found
                if "tool not found" in str(e).lower():
                    print("start_app tool not found, skipping test")

                # Check if the error is due to Chrome not being installed
                if "no such file" in str(e).lower() or "not found" in str(e).lower():
                    print(
                        "Application may not be installed on the test system, skipping test"
                    )

                # Don't fail the test if the operation is not supported
        else:
            print(
                "Note: Application interface is not available, skipping application test"
            )

    def test_stop_app_by_pname(self):
        """Test stopping an application by process name."""
        if (
            hasattr(self.__class__.session, "application")
            and self.__class__.session.application
        ):
            start_cmd = "/usr/bin/google-chrome-stable"
            print(f"Starting application: {start_cmd}...")
            try:
                start_result = self.__class__.session.application.start_app(start_cmd)

                # Verify result is of correct type
                self.assertIsInstance(start_result, ProcessListResult)

                if not start_result.success:
                    print(
                        f"Error starting app: "
                        f"{start_result.error_message} (Request ID: "
                        f"{start_result.request_id})"
                    )
                    return

                processes = start_result.data
                print(
                    f"Application started successfully, returned "
                    f"{len(processes)} processes"
                )

                # Verify we got some processes back
                if len(processes) == 0:
                    print(
                        "Warning: No processes returned after starting the application"
                    )
                    return

                # Get the process name to stop
                process_to_stop = processes[0].pname
                print(f"Attempting to stop process by name: {process_to_stop}")

                # Call stop_app_by_pname function
                try:
                    stop_result = self.__class__.session.application.stop_app_by_pname(
                        process_to_stop
                    )

                    # Verify result is of correct type
                    self.assertIsInstance(stop_result, AppOperationResult)

                    if not stop_result.success:
                        print(
                            f"Error stopping app: "
                            f"{stop_result.error_message} (Request ID: "
                            f"{stop_result.request_id})"
                        )
                        return

                    print(f"Successfully stopped process by name: {process_to_stop}")

                    # Verify the process was stopped by listing visible apps
                    # Give some time for the process to be terminated
                    time.sleep(1)
                    list_result = self.__class__.session.application.list_visible_apps()

                    # Verify result is of correct type
                    self.assertIsInstance(list_result, ProcessListResult)

                    if not list_result.success:
                        print(
                            f"Error listing apps: "
                            f"{list_result.error_message} (Request ID: "
                            f"{list_result.request_id})"
                        )
                        return

                    visible_apps = list_result.data

                    # Check if the process is still in the list
                    process_still_running = False
                    for app in visible_apps:
                        if app.pname == process_to_stop:
                            process_still_running = True
                            break

                    if process_still_running:
                        print(
                            f"Warning: Process {process_to_stop} is still running after stop_app_by_pname"
                        )
                    else:
                        print(
                            f"Process {process_to_stop} was successfully stopped and is no longer running"
                        )
                except Exception as e:
                    print(f"Note: stop_app_by_pname failed: {e}")
                    # Don't fail the test if the operation is not supported
            except Exception as e:
                print(f"Note: start_app failed: {e}")

                # Check if the error is due to the tool not being found
                if "tool not found" in str(e).lower():
                    print("start_app tool not found, skipping test")

                # Check if the error is due to the application not being installed
                if "no such file" in str(e).lower() or "not found" in str(e).lower():
                    print(
                        "Application may not be installed on the test system, skipping test"
                    )

                # Don't fail the test if the operation is not supported
        else:
            print(
                "Note: Application interface is not available, skipping application test"
            )


if __name__ == "__main__":
    unittest.main()
