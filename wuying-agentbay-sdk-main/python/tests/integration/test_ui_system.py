import os
import time
import unittest

from agentbay import AgentBay
from agentbay.exceptions import AgentBayError
from agentbay.model import BoolResult, OperationResult
from agentbay.session_params import CreateSessionParams
from agentbay.ui.ui import KeyCode, UIElementListResult


class TestUISystemIntegration(unittest.TestCase):
    agent_bay = None
    session = None
    ui = None

    @classmethod
    def setUpClass(cls):
        """
        Set up the test environment by creating a session and initializing UI model.
        """
        api_key = os.getenv("AGENTBAY_API_KEY", "your_api_key")
        cls.agent_bay = AgentBay(api_key=api_key)
        params = CreateSessionParams(
            image_id="mobile_latest",
        )
        result = cls.agent_bay.create(params)
        if not result.success or not result.session:
            raise unittest.SkipTest("Failed to create session")

        cls.session = result.session
        cls.ui = cls.session.ui
        time.sleep(3)
        print(f"Session created with ID: {cls.session.session_id}")

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

    def test_get_clickable_ui_elements(self):
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
        try:
            x, y = 100, 200
            result = self.__class__.ui.click(x, y, button="left")
            self.assertIsInstance(result, BoolResult)
            self.assertTrue(result.success, f"Failed to click: {result.error_message}")
            print(f"\nClicked on coordinates ({x}, {y}) successfully.")
        except AgentBayError as e:
            self.fail(f"click failed with error: {e}")

    def test_send_key(self):
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
