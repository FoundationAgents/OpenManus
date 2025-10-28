import os
import unittest

from agentbay import AgentBay
from agentbay.application.application import InstalledAppListResult, ProcessListResult
from agentbay.exceptions import AgentBayError
from agentbay.model import BoolResult, OperationResult
from agentbay.session_params import CreateSessionParams
from agentbay.ui import KeyCode
from agentbay.ui.ui import UIElementListResult


class TestMobileSystemIntegration(unittest.TestCase):
    agent_bay = None
    session = None
    ui = None
    application = None

    @classmethod
    def setUpClass(cls):
        """
        Set up the test environment by creating a session and initializing ui model.
        """
        api_key = os.getenv(
            "AGENTBAY_API_KEY", "your_api_key"
        )  # Replace with your actual API key
        cls.agent_bay = AgentBay(api_key=api_key)
        params = CreateSessionParams(
            image_id="mobile_latest",
        )
        result = cls.agent_bay.create(params)
        cls.session = result.session
        cls.ui = cls.session.ui
        cls.application = cls.session.application

    @classmethod
    def tearDownClass(cls):
        """
        Clean up the test environment by deleting the session.
        """
        try:
            if cls.session:
                delete_result = cls.agent_bay.delete(cls.session)
                if delete_result.success:
                    print("Session deleted successfully")
                else:
                    print(f"Failed to delete session: {delete_result.error_message}")
        except AgentBayError as e:
            print(f"Failed to delete session: {e}")

    def test_get_installed_apps(self):
        """
        Test retrieving installed applications.
        """
        try:
            result = self.__class__.application.get_installed_apps(
                start_menu=True, desktop=False, ignore_system_apps=True
            )
            self.assertIsInstance(result, InstalledAppListResult)
            self.assertTrue(
                result.success,
                f"Failed to get installed apps: {result.error_message}",
            )

            installed_apps = result.data
            print("\nInstalled Applications:")
            for app in installed_apps:
                print(f"Name: {app.name}, Start Command: {app.start_cmd}")
        except AgentBayError as e:
            self.fail(f"get_installed_apps failed with error: {e}")

    def test_start_and_stop_app(self):
        """
        Test starting and stopping an application.
        """
        try:
            # Start an application
            start_cmd = (
                "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1"
            )
            start_result = self.__class__.application.start_app(start_cmd)
            self.assertIsInstance(start_result, ProcessListResult)
            self.assertTrue(
                start_result.success,
                f"Failed to start app: {start_result.error_message}",
            )

            processes = start_result.data
            print("\nStart App Result:", processes)

            # Stop the application
            stop_cmd = "am force-stop com.autonavi.minimap"
            stop_result = self.__class__.application.stop_app_by_cmd(stop_cmd)
            self.assertTrue(
                stop_result.success,
                f"Failed to stop app: {stop_result.error_message}",
            )
            print("\nApplication stopped successfully.")
        except AgentBayError as e:
            self.fail(f"start_and_stop_app failed with error: {e}")

    def test_get_clickable_ui_elements(self):
        """
        Test retrieving clickable UI elements.
        """
        try:
            result = self.__class__.ui.get_clickable_ui_elements(timeout_ms=10000)
            self.assertIsInstance(result, UIElementListResult)
            self.assertTrue(
                result.success,
                f"Failed to get clickable UI elements: {result.error_message}",
            )

            clickable_elements = result.elements
            print("\nClickable UI Elements:")
            for element in clickable_elements:
                print(element)
        except AgentBayError as e:
            self.fail(f"get_clickable_ui_elements failed with error: {e}")

    def test_click(self):
        """
        Test clicking on a specific coordinate.
        """
        try:
            x, y = 100, 200
            result = self.__class__.ui.click(x, y, button="left")
            self.assertIsInstance(result, BoolResult)
            self.assertTrue(result.success, f"Failed to click: {result.error_message}")
            print(f"\nClicked on coordinates ({x}, {y}) successfully.")
        except AgentBayError as e:
            self.fail(f"click failed with error: {e}")

    def test_send_key(self):
        """
        Test sending a key press event.
        """
        try:
            result = self.__class__.ui.send_key(KeyCode.HOME)
            self.assertIsInstance(result, BoolResult)
            self.assertTrue(
                result.success, f"Failed to send key: {result.error_message}"
            )
            print("\nSent HOME key successfully.")
        except AgentBayError as e:
            self.fail(f"send_key failed with error: {e}")

    def test_swipe(self):
        """
        Test performing a swipe gesture.
        """
        try:
            start_x, start_y, end_x, end_y, duration_ms = (
                100,
                200,
                300,
                400,
                500,
            )
            result = self.__class__.ui.swipe(
                start_x, start_y, end_x, end_y, duration_ms
            )
            self.assertIsInstance(result, BoolResult)
            self.assertTrue(result.success, f"Failed to swipe: {result.error_message}")
            print(
                f"\nSwipe performed successfully from ({start_x}, {start_y}) to ({end_x}, {end_y}) in {duration_ms}ms."
            )
        except AgentBayError as e:
            self.fail(f"swipe failed with error: {e}")

    def test_input_text(self):
        """
        Test inputting text into the active field.
        """
        try:
            text = "Hello, world!"
            result = self.__class__.ui.input_text(text)
            self.assertIsInstance(result, BoolResult)
            self.assertTrue(
                result.success, f"Failed to input text: {result.error_message}"
            )
            print(f"\nInput text '{text}' successfully.")
        except AgentBayError as e:
            self.fail(f"input_text failed with error: {e}")

    def test_get_all_ui_elements(self):
        """
        Test retrieving all UI elements.
        """
        try:
            result = self.__class__.ui.get_all_ui_elements(timeout_ms=10000)
            self.assertIsInstance(result, UIElementListResult)
            self.assertTrue(
                result.success,
                f"Failed to get all UI elements: {result.error_message}",
            )

            ui_elements = result.elements
            print("\nAll UI Elements:")
            for element in ui_elements:
                print(element)
        except AgentBayError as e:
            self.fail(f"get_all_ui_elements failed with error: {e}")

    def test_screenshot(self):
        """
        Test taking a screenshot.
        """
        try:
            result = self.__class__.ui.screenshot()
            self.assertIsInstance(result, OperationResult)
            self.assertTrue(
                result.success,
                f"Failed to take screenshot: {result.error_message}",
            )
            screenshot_path = result.data
            self.assertIsInstance(screenshot_path, str)
            print(f"\nScreenshot saved to: {screenshot_path}")
        except AgentBayError as e:
            self.fail(f"screenshot failed with error: {e}")


if __name__ == "__main__":
    unittest.main()
