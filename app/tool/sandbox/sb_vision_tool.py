from typing import Optional

from pydantic import Field

from app.sandbox.providers import VisionService
from app.tool.base import BaseTool, ToolResult


_VISION_DESCRIPTION = """\
Read and encode image files from the sandbox environment as base64 strings.
"""


class SandboxVisionTool(BaseTool):
    """Provider-agnostic vision tool."""

    name: str = "sandbox_vision"
    description: str = _VISION_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["see_image"],
            },
            "file_path": {
                "type": "string",
                "description": "Image path inside sandbox",
            },
        },
        "required": ["action", "file_path"],
    }

    vision_service: VisionService = Field(exclude=True)

    def __init__(self, vision_service: VisionService, **data):
        super().__init__(vision_service=vision_service, **data)

    async def execute(
        self,
        action: str,
        file_path: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        if action != "see_image":
            return self.fail_response(f"Unsupported vision action: {action}")
        if not file_path:
            return self.fail_response("file_path is required")
        try:
            data = await self.vision_service.read_image(file_path)
            return ToolResult(
                output=f"Loaded image '{file_path}' successfully.",
                base64_image=data.get("base64"),
            )
        except Exception as exc:
            return self.fail_response(f"see_image failed: {exc}")
