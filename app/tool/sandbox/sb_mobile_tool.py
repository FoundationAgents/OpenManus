import asyncio
from typing import Literal, Optional

from pydantic import Field

from app.sandbox.providers import MobileService
from app.tool.base import BaseTool, ToolResult


_MOBILE_DESCRIPTION = """\
Mobile automation tool powered by the sandbox provider.
Supports tap, swipe, text input, key presses, UI inspection, and screenshots on remote devices.
"""


KEY_NAME_TO_CODE = {
    "home": 3,
    "back": 4,
    "volume_up": 24,
    "volume_down": 25,
    "power": 26,
    "menu": 82,
}


class SandboxMobileTool(BaseTool):
    """Provider-agnostic mobile automation tool."""

    name: str = "sandbox_mobile"
    description: str = _MOBILE_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "tap",
                    "swipe",
                    "input_text",
                    "send_key",
                    "screenshot",
                    "list_clickable",
                    "wait",
                ],
                "description": "Mobile action to perform",
            },
            "x": {"type": "number", "description": "X coordinate"},
            "y": {"type": "number", "description": "Y coordinate"},
            "start_x": {"type": "number", "description": "Swipe start X"},
            "start_y": {"type": "number", "description": "Swipe start Y"},
            "end_x": {"type": "number", "description": "Swipe end X"},
            "end_y": {"type": "number", "description": "Swipe end Y"},
            "duration_ms": {
                "type": "integer",
                "description": "Swipe duration in milliseconds",
                "default": 300,
            },
            "text": {"type": "string", "description": "Text to input"},
            "key": {
                "type": "string",
                "enum": list(KEY_NAME_TO_CODE.keys()),
                "description": "Key to press",
            },
            "timeout_ms": {
                "type": "integer",
                "description": "Timeout for UI queries",
                "default": 2000,
            },
            "duration": {
                "type": "number",
                "description": "Seconds to wait",
                "default": 0.5,
            },
        },
        "required": ["action"],
    }

    mobile_service: MobileService = Field(exclude=True)

    def __init__(self, mobile_service: MobileService, **data):
        super().__init__(mobile_service=mobile_service, **data)

    async def execute(
        self,
        action: Literal[
            "tap",
            "swipe",
            "input_text",
            "send_key",
            "screenshot",
            "list_clickable",
            "wait",
        ],
        x: Optional[float] = None,
        y: Optional[float] = None,
        start_x: Optional[float] = None,
        start_y: Optional[float] = None,
        end_x: Optional[float] = None,
        end_y: Optional[float] = None,
        duration_ms: int = 300,
        text: Optional[str] = None,
        key: Optional[str] = None,
        timeout_ms: int = 2000,
        duration: float = 0.5,
        **kwargs,
    ) -> ToolResult:
        try:
            if action == "tap":
                if x is None or y is None:
                    return self.fail_response(
                        "x and y coordinates are required for tap"
                    )
                xi, yi = int(round(float(x))), int(round(float(y)))
                await self.mobile_service.tap(xi, yi)
                return ToolResult(output=f"Tapped at ({xi}, {yi})")

            if action == "swipe":
                required = [start_x, start_y, end_x, end_y]
                if any(value is None for value in required):
                    return self.fail_response(
                        "start_x, start_y, end_x, end_y are required for swipe"
                    )
                sx, sy = int(round(float(start_x))), int(round(float(start_y)))
                ex, ey = int(round(float(end_x))), int(round(float(end_y)))
                duration_clamped = max(50, min(5000, int(duration_ms)))
                await self.mobile_service.swipe(sx, sy, ex, ey, duration_clamped)
                return ToolResult(
                    output=(
                        f"Swiped from ({sx}, {sy}) to ({ex}, {ey}) in {duration_clamped} ms"
                    )
                )

            if action == "input_text":
                if text is None:
                    return self.fail_response("text is required for input_text")
                await self.mobile_service.input_text(text)
                return ToolResult(output=f"Typed: {text}")

            if action == "send_key":
                if not key:
                    return self.fail_response("key is required for send_key")
                key_code = KEY_NAME_TO_CODE.get(key.lower())
                if key_code is None:
                    return self.fail_response(f"Unsupported key: {key}")
                await self.mobile_service.send_key(key_code)
                return ToolResult(output=f"Sent key: {key.lower()}")

            if action == "screenshot":
                data = await self.mobile_service.screenshot()
                message = "Mobile screenshot captured"
                if data.get("url"):
                    message += f": {data['url']}"
                return ToolResult(output=message, base64_image=data.get("base64"))

            if action == "list_clickable":
                timeout_clamped = max(0, int(timeout_ms))
                data = await self.mobile_service.get_clickable_ui_elements(
                    timeout_clamped
                )
                return self.success_response(data)

            if action == "wait":
                safe_duration = max(0.0, min(30.0, float(duration)))
                await asyncio.sleep(safe_duration)
                return ToolResult(output=f"Waited {safe_duration} seconds")

            return self.fail_response(f"Unknown action: {action}")

        except NotImplementedError as exc:
            return self.fail_response(str(exc))
        except Exception as exc:  # noqa: BLE001
            return self.fail_response(f"Mobile action failed: {exc}")
