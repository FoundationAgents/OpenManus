import base64
import io
import json
import traceback
from typing import Optional  # Add this import for Optional

from PIL import Image
from pydantic import Field

from app.daytona.tool_base import (  # Ensure Sandbox is imported correctly
    Sandbox,
    SandboxToolsBase,
    ThreadMessage,
)
from app.tool.base import ToolResult
from app.utils.logger import logger


# Context = TypeVar("Context")
_BROWSER_DESCRIPTION = """\
A sandbox-based browser automation tool that allows interaction with web pages through various actions.
* This tool provides commands for controlling a browser session in a sandboxed environment
* It maintains state across calls, keeping the browser session alive until explicitly closed
* Use this when you need to browse websites, fill forms, click buttons, or extract content in a secure sandbox
* Each action requires specific parameters as defined in the tool's dependencies
Key capabilities include:
* Navigation: Go to specific URLs, go back in history
* Interaction: Click elements by index, input text, send keyboard commands
* Scrolling: Scroll up/down by pixel amount or scroll to specific text
* Tab management: Switch between tabs or close tabs
* Content extraction: Get dropdown options or select dropdown options
"""


# noinspection PyArgumentList
class SandboxBrowserTool(SandboxToolsBase):
    """Tool for executing tasks in a Daytona sandbox with browser-use capabilities."""

    name: str = "sandbox_browser"
    description: str = _BROWSER_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "navigate_to",
                    "go_back",
                    "wait",
                    "click_element",
                    "input_text",
                    "send_keys",
                    "switch_tab",
                    "close_tab",
                    "scroll_down",
                    "scroll_up",
                    "scroll_to_text",
                    "get_dropdown_options",
                    "select_dropdown_option",
                    "click_coordinates",
                    "drag_drop",
                ],
                "description": "The browser action to perform",
            },
            "url": {
                "type": "string",
                "description": "URL for 'navigate_to' action",
            },
            "index": {
                "type": "integer",
                "description": "Element index for interaction actions",
            },
            "text": {
                "type": "string",
                "description": "Text for input or scroll actions",
            },
            "amount": {
                "type": "integer",
                "description": "Pixel amount to scroll",
            },
            "page_id": {
                "type": "integer",
                "description": "Tab ID for tab management actions",
            },
            "keys": {
                "type": "string",
                "description": "Keys to send for keyboard actions",
            },
            "seconds": {
                "type": "integer",
                "description": "Seconds to wait",
            },
            "x": {
                "type": "integer",
                "description": "X coordinate for click or drag actions",
            },
            "y": {
                "type": "integer",
                "description": "Y coordinate for click or drag actions",
            },
            "element_source": {
                "type": "string",
                "description": "Source element for drag and drop",
            },
            "element_target": {
                "type": "string",
                "description": "Target element for drag and drop",
            },
        },
        "required": ["action"],
        "dependencies": {
            "navigate_to": ["url"],
            "click_element": ["index"],
            "input_text": ["index", "text"],
            "send_keys": ["keys"],
            "switch_tab": ["page_id"],
            "close_tab": ["page_id"],
            "scroll_down": ["amount"],
            "scroll_up": ["amount"],
            "scroll_to_text": ["text"],
            "get_dropdown_options": ["index"],
            "select_dropdown_option": ["index", "text"],
            "click_coordinates": ["x", "y"],
            "drag_drop": ["element_source", "element_target"],
            "wait": ["seconds"],
        },
    }
    browser_message: Optional[ThreadMessage] = Field(default=None, exclude=True)

    def __init__(
        self, sandbox: Optional[Sandbox] = None, thread_id: Optional[str] = None, **data
    ):
        """Initialize with optional sandbox and thread_id."""
        super().__init__(**data)
        if sandbox is not None:
            self._sandbox = sandbox  # Directly set the base class private attribute

    def _validate_base64_image(
        self, base64_string: str, max_size_mb: int = 10
    ) -> tuple[bool, str]:
        """
        Validate base64 image data.
        Args:
            base64_string: The base64 encoded image data
            max_size_mb: Maximum allowed image size in megabytes
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not base64_string or len(base64_string) < 10:
                return False, "Base64 string is empty or too short"
            if base64_string.startswith("data:"):
                try:
                    base64_string = base64_string.split(",", 1)[1]
                except (IndexError, ValueError):
                    return False, "Invalid data URL format"
            import re

            if not re.match(r"^[A-Za-z0-9+/]*={0,2}$", base64_string):
                return False, "Invalid base64 characters detected"
            if len(base64_string) % 4 != 0:
                return False, "Invalid base64 string length"
            try:
                image_data = base64.b64decode(base64_string, validate=True)
            except Exception as e:
                return False, f"Base64 decoding failed: {str(e)}"
            max_size_bytes = max_size_mb * 1024 * 1024
            if len(image_data) > max_size_bytes:
                return False, f"Image size exceeds limit ({max_size_bytes} bytes)"
            try:
                image_stream = io.BytesIO(image_data)
                with Image.open(image_stream) as img:
                    img.verify()
                    supported_formats = {"JPEG", "PNG", "GIF", "BMP", "WEBP", "TIFF"}
                    if img.format not in supported_formats:
                        return False, f"Unsupported image format: {img.format}"
                    image_stream.seek(0)
                    with Image.open(image_stream) as img_check:
                        width, height = img_check.size
                        max_dimension = 8192
                        if width > max_dimension or height > max_dimension:
                            return (
                                False,
                                f"Image dimensions exceed limit ({max_dimension}x{max_dimension})",
                            )
                        if width < 1 or height < 1:
                            return False, f"Invalid image dimensions: {width}x{height}"
            except Exception as e:
                return False, f"Invalid image data: {str(e)}"
            return True, "Valid image"
        except Exception as e:
            logger.error(f"Unexpected error during base64 image validation: {e}")
            return False, f"Validation error: {str(e)}"

    async def _execute_browser_action(
        self, endpoint: str, params: dict = None, method: str = "POST"
    ) -> ToolResult:
        """Execute a browser automation action through the sandbox API."""
        try:
            await self._ensure_sandbox()
            url = f"http://localhost:8003/api/automation/{endpoint}"
            if method == "GET" and params:
                query_params = "&".join([f"{k}={v}" for k, v in params.items()])
                url = f"{url}?{query_params}"
                curl_cmd = (
                    f"curl -s -X {method} '{url}' -H 'Content-Type: application/json'"
                )
            else:
                curl_cmd = (
                    f"curl -s -X {method} '{url}' -H 'Content-Type: application/json'"
                )
                if params:
                    json_data = json.dumps(params)
                    curl_cmd += f" -d '{json_data}'"
            logger.debug(f"Executing curl command: {curl_cmd}")
            response = self.sandbox.process.exec(curl_cmd, timeout=30)
            if response.exit_code == 0:
                try:
                    result = json.loads(response.result)
                    result.setdefault("content", "")
                    result.setdefault("role", "assistant")
                    if "screenshot_base64" in result:
                        screenshot_data = result["screenshot_base64"]
                        is_valid, validation_message = self._validate_base64_image(
                            screenshot_data
                        )
                        if not is_valid:
                            logger.warning(
                                f"Screenshot validation failed: {validation_message}"
                            )
                            result["image_validation_error"] = validation_message
                        del result["screenshot_base64"]

                    # added_message = await self.thread_manager.add_message(
                    #     thread_id=self.thread_id,
                    #     type="browser_state",
                    #     content=result,
                    #     is_llm_message=False
                    # )
                    message = ThreadMessage(
                        type="browser_state", content=result, is_llm_message=False
                    )
                    self.browser_message = message
                    success_response = {
                        "success": result.get("success", False),
                        "message": result.get("message", "Browser action completed"),
                    }
                    #         if added_message and 'message_id' in added_message:
                    #             success_response['message_id'] = added_message['message_id']
                    for field in [
                        "url",
                        "title",
                        "element_count",
                        "pixels_below",
                        "ocr_text",
                        "image_url",
                    ]:
                        if field in result:
                            success_response[field] = result[field]
                    return (
                        self.success_response(success_response)
                        if success_response["success"]
                        else self.fail_response(success_response)
                    )
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse response JSON: {e}")
                    return self.fail_response(f"Failed to parse response JSON: {e}")
            else:
                logger.error(f"Browser automation request failed: {response}")
                return self.fail_response(
                    f"Browser automation request failed: {response}"
                )
        except Exception as e:
            logger.error(f"Error executing browser action: {e}")
            logger.debug(traceback.format_exc())
            return self.fail_response(f"Error executing browser action: {e}")

    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        index: Optional[int] = None,
        text: Optional[str] = None,
        amount: Optional[int] = None,
        page_id: Optional[int] = None,
        keys: Optional[str] = None,
        seconds: Optional[int] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        element_source: Optional[str] = None,
        element_target: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """
        Execute a browser action in the sandbox environment.
        Args:
            action: The browser action to perform
            url: URL for navigation
            index: Element index for interaction
            text: Text for input or scroll actions
            amount: Pixel amount to scroll
            page_id: Tab ID for tab management
            keys: Keys to send for keyboard actions
            seconds: Seconds to wait
            x: X coordinate for click/drag
            y: Y coordinate for click/drag
            element_source: Source element for drag and drop
            element_target: Target element for drag and drop
        Returns:
            ToolResult with the action's output or error
        """
        # async with self.lock:
        try:
            # Navigation actions
            if action == "navigate_to":
                if not url:
                    return self.fail_response("URL is required for navigation")
                return await self._execute_browser_action("navigate_to", {"url": url})
            elif action == "go_back":
                return await self._execute_browser_action("go_back", {})
                # Interaction actions
            elif action == "click_element":
                if index is None:
                    return self.fail_response("Index is required for click_element")
                return await self._execute_browser_action(
                    "click_element", {"index": index}
                )
            elif action == "input_text":
                if index is None or not text:
                    return self.fail_response(
                        "Index and text are required for input_text"
                    )
                return await self._execute_browser_action(
                    "input_text", {"index": index, "text": text}
                )
            elif action == "send_keys":
                if not keys:
                    return self.fail_response("Keys are required for send_keys")
                return await self._execute_browser_action("send_keys", {"keys": keys})
                # Tab management
            elif action == "switch_tab":
                if page_id is None:
                    return self.fail_response("Page ID is required for switch_tab")
                return await self._execute_browser_action(
                    "switch_tab", {"page_id": page_id}
                )
            elif action == "close_tab":
                if page_id is None:
                    return self.fail_response("Page ID is required for close_tab")
                return await self._execute_browser_action(
                    "close_tab", {"page_id": page_id}
                )
                # Scrolling actions
            elif action == "scroll_down":
                params = {"amount": amount} if amount is not None else {}
                return await self._execute_browser_action("scroll_down", params)
            elif action == "scroll_up":
                params = {"amount": amount} if amount is not None else {}
                return await self._execute_browser_action("scroll_up", params)
            elif action == "scroll_to_text":
                if not text:
                    return self.fail_response("Text is required for scroll_to_text")
                return await self._execute_browser_action(
                    "scroll_to_text", {"text": text}
                )
            # Dropdown actions
            elif action == "get_dropdown_options":
                if index is None:
                    return self.fail_response(
                        "Index is required for get_dropdown_options"
                    )
                return await self._execute_browser_action(
                    "get_dropdown_options", {"index": index}
                )
            elif action == "select_dropdown_option":
                if index is None or not text:
                    return self.fail_response(
                        "Index and text are required for select_dropdown_option"
                    )
                return await self._execute_browser_action(
                    "select_dropdown_option", {"index": index, "text": text}
                )
                # Coordinate-based actions
            elif action == "click_coordinates":
                if x is None or y is None:
                    return self.fail_response(
                        "X and Y coordinates are required for click_coordinates"
                    )
                return await self._execute_browser_action(
                    "click_coordinates", {"x": x, "y": y}
                )
            elif action == "drag_drop":
                if not element_source or not element_target:
                    return self.fail_response(
                        "Source and target elements are required for drag_drop"
                    )
                return await self._execute_browser_action(
                    "drag_drop",
                    {
                        "element_source": element_source,
                        "element_target": element_target,
                    },
                )
            # Utility actions
            elif action == "wait":
                seconds_to_wait = seconds if seconds is not None else 3
                return await self._execute_browser_action(
                    "wait", {"seconds": seconds_to_wait}
                )
            else:
                return self.fail_response(f"Unknown action: {action}")
        except Exception as e:
            logger.error(f"Error executing browser action: {e}")
            return self.fail_response(f"Error executing browser action: {e}")

    async def get_current_state(
        self, message: Optional[ThreadMessage] = None
    ) -> ToolResult:
        """
        Get the current browser state as a ToolResult.
        If context is not provided, uses self.context.
        """
        try:
            # Use provided context or fall back to self.context
            message = message or self.browser_message
            if not message:
                return ToolResult(error="Browser context not initialized")
            state = message.content
            screenshot = state.get("screenshot_base64")
            # Build the state info with all required fields
            state_info = {
                "url": state.get("url", ""),
                "title": state.get("title", ""),
                "tabs": [tab.model_dump() for tab in state.get("tabs", [])],
                "pixels_above": getattr(state, "pixels_above", 0),
                "pixels_below": getattr(state, "pixels_below", 0),
                "help": "[0], [1], [2], etc., represent clickable indices corresponding to the elements listed. Clicking on these indices will navigate to or interact with the respective content behind them.",
            }

            return ToolResult(
                output=json.dumps(state_info, indent=4, ensure_ascii=False),
                base64_image=screenshot,
            )
        except Exception as e:
            return ToolResult(error=f"Failed to get browser state: {str(e)}")

    @classmethod
    def create_with_sandbox(cls, sandbox: Sandbox) -> "SandboxBrowserTool":
        """Factory method to create a tool with sandbox."""
        return cls(sandbox=sandbox)
