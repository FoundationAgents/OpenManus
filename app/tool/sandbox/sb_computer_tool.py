import asyncio
from typing import List, Optional

from pydantic import Field

from app.sandbox.providers import ComputerService
from app.tool.base import BaseTool, ToolResult
from app.tool.computer_constants import KEYBOARD_KEYS, MOUSE_BUTTONS


_COMPUTER_DESCRIPTION = """\
Desktop automation tool powered by the sandbox provider agentbay. It's a Linux desktop.
Supports mouse movement, clicks, scrolling, keyboard input, hotkeys, and screenshots.
"""


class SandboxComputerTool(BaseTool):
    """Provider-agnostic computer automation tool."""

    name: str = "computer_use"
    description: str = _COMPUTER_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "move_to",
                    "click",
                    "scroll",
                    "typing",
                    "press",
                    "wait",
                    "mouse_down",
                    "mouse_up",
                    "drag_to",
                    "hotkey",
                    "screenshot",
                ],
                "description": "The computer action to perform",
            },
            "x": {"type": "number", "description": "X coordinate for mouse actions"},
            "y": {"type": "number", "description": "Y coordinate for mouse actions"},
            "button": {
                "type": "string",
                "enum": MOUSE_BUTTONS,
                "description": "Mouse button for click/drag actions",
                "default": "left",
            },
            "num_clicks": {
                "type": "integer",
                "description": "Number of clicks",
                "enum": [1, 2, 3],
                "default": 1,
            },
            "amount": {
                "type": "integer",
                "description": "Scroll amount (positive for up, negative for down)",
                "minimum": -10,
                "maximum": 10,
            },
            "text": {"type": "string", "description": "Text to type"},
            "key": {
                "type": "string",
                "enum": KEYBOARD_KEYS,
                "description": "Key to press",
            },
            "keys": {
                "type": "string",
                "enum": KEYBOARD_KEYS,
                "description": "Key combination to press",
            },
            "duration": {
                "type": "number",
                "description": "Duration in seconds to wait",
                "default": 0.5,
            },
        },
        "required": ["action"],
    }

    computer_service: ComputerService = Field(exclude=True)
    mouse_x: Optional[int] = Field(default=None, exclude=True)
    mouse_y: Optional[int] = Field(default=None, exclude=True)

    def __init__(self, computer_service: ComputerService, **data):
        super().__init__(computer_service=computer_service, **data)

    async def execute(
        self,
        action: str,
        x: Optional[float] = None,
        y: Optional[float] = None,
        button: str = "left",
        num_clicks: int = 1,
        amount: Optional[int] = None,
        text: Optional[str] = None,
        key: Optional[str] = None,
        keys: Optional[str] = None,
        duration: float = 0.5,
        **kwargs,
    ) -> ToolResult:
        try:
            if action == "move_to":
                if x is None or y is None:
                    return self.fail_response("x and y coordinates are required")
                x_int, y_int = self._coerce_point(x, y)
                await self.computer_service.move_mouse(x_int, y_int)
                self._update_position(x_int, y_int)
                return ToolResult(output=f"Moved to ({x_int}, {y_int})")

            if action == "click":
                target_x, target_y = await self._resolve_target(x, y)
                clicks = max(1, min(3, int(num_clicks)))
                await self.computer_service.click_mouse(
                    target_x, target_y, button=button, count=clicks
                )
                self._update_position(target_x, target_y)
                return ToolResult(
                    output=f"{clicks} {button} click(s) performed at ({target_x}, {target_y})"
                )

            if action == "scroll":
                if amount is None:
                    return self.fail_response("Scroll amount is required")
                scroll_amount = max(-10, min(10, int(amount)))
                current_x, current_y = await self._ensure_position()
                await self.computer_service.scroll(
                    current_x, current_y, amount=scroll_amount
                )
                direction = "up" if scroll_amount > 0 else "down"
                steps = abs(scroll_amount)
                return ToolResult(
                    output=f"Scrolled {direction} {steps} step(s) at ({current_x}, {current_y})"
                )

            if action == "typing":
                if text is None:
                    return self.fail_response("Text is required for typing")
                await self.computer_service.input_text(str(text))
                return ToolResult(output=f"Typed: {text}")

            if action == "press":
                if key is None:
                    return self.fail_response("key is required for press action")
                key_sequence = self._split_keys(str(key))
                await self.computer_service.press_keys(key_sequence, hold=False)
                return ToolResult(output=f"Pressed keys: {'+'.join(key_sequence)}")

            if action == "hotkey":
                if keys is None:
                    return self.fail_response("keys are required for hotkey action")
                key_sequence = self._split_keys(str(keys))
                await self.computer_service.press_keys(key_sequence, hold=False)
                return ToolResult(
                    output=f"Pressed key combination: {'+'.join(key_sequence)}"
                )

            if action == "wait":
                safe_duration = max(0.0, min(10.0, float(duration)))
                await asyncio.sleep(safe_duration)
                return ToolResult(output=f"Waited {safe_duration} seconds")

            if action in {"mouse_down", "mouse_up"}:
                return self.fail_response(
                    "Mouse down/up is not supported in the AgentBay computer API yet"
                )

            if action == "drag_to":
                if x is None or y is None:
                    return self.fail_response("x and y coordinates are required")
                start_x, start_y = await self._ensure_position()
                target_x, target_y = self._coerce_point(x, y)
                await self.computer_service.drag_mouse(
                    start_x, start_y, target_x, target_y, button=button
                )
                self._update_position(target_x, target_y)
                return ToolResult(
                    output=f"Dragged from ({start_x}, {start_y}) to ({target_x}, {target_y})"
                )

            if action == "screenshot":
                data = await self.computer_service.screenshot()
                message = "Screenshot captured"
                if data.get("url"):
                    message += f": {data['url']}"
                return ToolResult(
                    output=message,
                    base64_image=data.get("base64"),
                )

            return self.fail_response(f"Unknown action: {action}")

        except NotImplementedError as exc:
            return self.fail_response(str(exc))
        except Exception as exc:  # noqa: BLE001
            return self.fail_response(f"Computer action failed: {exc}")

    async def _resolve_target(
        self, x: Optional[float], y: Optional[float]
    ) -> tuple[int, int]:
        if x is None or y is None:
            return await self._ensure_position()
        return self._coerce_point(x, y)

    async def _ensure_position(self) -> tuple[int, int]:
        if self.mouse_x is not None and self.mouse_y is not None:
            return self.mouse_x, self.mouse_y
        try:
            position = await self.computer_service.get_cursor_position()
        except NotImplementedError:
            position = {"x": 0, "y": 0}
        self.mouse_x = int(position.get("x", 0))
        self.mouse_y = int(position.get("y", 0))
        return self.mouse_x, self.mouse_y

    def _update_position(self, x: int, y: int) -> None:
        self.mouse_x = x
        self.mouse_y = y

    @staticmethod
    def _coerce_point(x: float, y: float) -> tuple[int, int]:
        return int(round(float(x))), int(round(float(y)))

    @staticmethod
    def _split_keys(key_spec: str) -> List[str]:
        return [part.strip() for part in key_spec.split("+") if part.strip()]
