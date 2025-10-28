import unittest
from unittest.mock import MagicMock

from agentbay.model import OperationResult
from agentbay.ui.ui import UI, KeyCode


class DummySession:
    def __init__(self):
        self.api_key = "dummy_key"
        self.session_id = "dummy_session"
        self.client = MagicMock()

    def get_api_key(self):
        return self.api_key

    def get_session_id(self):
        return self.session_id

    def get_client(self):
        return self.client


class TestUIApi(unittest.TestCase):
    def setUp(self):
        self.session = DummySession()
        self.ui = UI(self.session)

    def test_get_clickable_ui_elements_success(self):
        self.ui._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=True,
                data="""[
            {
                "bounds": "48,90,1032,630",
                "className": "LinearLayout",
                "text": "digital_widget May 31st Saturday",
                "type": "clickable",
                "resourceId": "com.android.deskclock:id/digital_widget",
                "index": 11,
                "isParent": false
            }
        ]""",
            )
        )
        result = self.ui.get_clickable_ui_elements()
        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "request-123")
        elements = result.elements
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["bounds"], "48,90,1032,630")
        self.assertEqual(elements[0]["className"], "LinearLayout")
        self.assertEqual(elements[0]["text"], "digital_widget May 31st Saturday")
        self.assertEqual(elements[0]["type"], "clickable")
        self.assertEqual(
            elements[0]["resourceId"],
            "com.android.deskclock:id/digital_widget",
        )

    def test_get_clickable_ui_elements_failure(self):
        self.ui._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=False,
                error_message="Failed to get clickable UI elements",
            )
        )
        result = self.ui.get_clickable_ui_elements()
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Failed to get clickable UI elements")

    def test_send_key_success(self):
        self.ui._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123", success=True, data=True
            )
        )
        result = self.ui.send_key(KeyCode.HOME)
        self.assertTrue(result.success)
        self.assertTrue(result.data)

    def test_send_key_failure(self):
        self.ui._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=False,
                error_message="Failed to send key",
            )
        )
        result = self.ui.send_key(KeyCode.HOME)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Failed to send key")

    def test_swipe_success(self):
        self.ui._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123", success=True, data=None
            )
        )
        result = self.ui.swipe(100, 200, 300, 400, duration_ms=500)
        self.assertTrue(result.success)

    def test_swipe_failure(self):
        self.ui._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=False,
                error_message="Failed to perform swipe",
            )
        )
        result = self.ui.swipe(100, 200, 300, 400, duration_ms=500)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Failed to perform swipe")

    def test_click_success(self):
        self.ui._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123", success=True, data=None
            )
        )
        result = self.ui.click(150, 250, button="left")
        self.assertTrue(result.success)

    def test_click_failure(self):
        self.ui._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=False,
                error_message="Failed to perform click",
            )
        )
        result = self.ui.click(150, 250, button="left")
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Failed to perform click")

    def test_input_text_success(self):
        self.ui._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123", success=True, data=None
            )
        )
        result = self.ui.input_text("Hello, world!")
        self.assertTrue(result.success)

    def test_input_text_failure(self):
        self.ui._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=False,
                error_message="Failed to input text",
            )
        )
        result = self.ui.input_text("Hello, world!")
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Failed to input text")

    def test_get_all_ui_elements_success(self):
        self.ui._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=True,
                data="""[
            {
                "bounds": "48,90,1032,630",
                "className": "LinearLayout",
                "text": "Sample Text",
                "type": "UIElement",
                "resourceId": "com.example:id/sample",
                "index": 0,
                "isParent": true,
                "children": [
                    {
                        "bounds": "50,100,200,300",
                        "className": "TextView",
                        "text": "Child Text",
                        "type": "UIElement",
                        "resourceId": "com.example:id/child",
                        "index": 1,
                        "isParent": false,
                        "children": []
                    }
                ]
            }
        ]""",
            )
        )
        result = self.ui.get_all_ui_elements()
        self.assertTrue(result.success)
        elements = result.elements
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["bounds"], "48,90,1032,630")
        self.assertEqual(elements[0]["className"], "LinearLayout")
        self.assertEqual(elements[0]["text"], "Sample Text")
        self.assertEqual(elements[0]["type"], "UIElement")
        self.assertEqual(elements[0]["resourceId"], "com.example:id/sample")
        self.assertEqual(len(elements[0]["children"]), 1)
        self.assertEqual(elements[0]["children"][0]["text"], "Child Text")

    def test_get_all_ui_elements_failure(self):
        self.ui._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=False,
                error_message="Failed to get all UI elements",
            )
        )
        result = self.ui.get_all_ui_elements()
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Failed to get all UI elements")

    def test_screenshot_success(self):
        OSS_URL = "https://oss-url/screenshot.png"
        self.ui._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123", success=True, data=OSS_URL
            )
        )
        result = self.ui.screenshot()
        self.assertTrue(result.success)
        self.assertEqual(result.data, OSS_URL)

    def test_screenshot_failure(self):
        self.ui._call_mcp_tool = MagicMock(
            return_value=OperationResult(
                request_id="request-123",
                success=False,
                error_message="Error in response: Failed to take screenshot",
            )
        )
        result = self.ui.screenshot()
        self.assertFalse(result.success)
        self.assertEqual(
            result.error_message,
            "Error in response: Failed to take screenshot",
        )

    def test_screenshot_exception(self):
        self.ui._call_mcp_tool = MagicMock(side_effect=Exception("Network error"))
        result = self.ui.screenshot()
        self.assertFalse(result.success)
        self.assertIn("Network error", result.error_message)


if __name__ == "__main__":
    unittest.main()
