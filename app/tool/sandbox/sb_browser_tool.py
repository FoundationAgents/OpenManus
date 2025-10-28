from typing import Any, Dict, Optional

from pydantic import Field

from app.sandbox.providers import BrowserService
from app.tool.base import BaseTool, ToolResult


_BROWSER_DESCRIPTION = """\
Execute browser automation actions within the sandbox.
The supported actions depend on the selected sandbox provider.
"""


class SandboxBrowserTool(BaseTool):
    """Provider-agnostic browser automation tool."""

    name: str = "sandbox_browser"
    description: str = _BROWSER_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Browser action to perform",
            },
            "url": {"type": "string"},
            "index": {"type": "integer"},
            "text": {"type": "string"},
            "amount": {"type": "integer"},
            "page_id": {"type": "integer"},
            "keys": {"type": "string"},
            "seconds": {"type": "integer"},
            "x": {"type": "integer"},
            "y": {"type": "integer"},
            "element_source": {"type": "string"},
            "element_target": {"type": "string"},
        },
        "required": ["action"],
    }

    browser_service: BrowserService = Field(exclude=True)

    def __init__(self, browser_service: BrowserService, **data):
        super().__init__(browser_service=browser_service, **data)

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
        try:
            payload: Dict[str, Optional[Any]] = {
                "url": url,
                "index": index,
                "text": text,
                "amount": amount,
                "page_id": page_id,
                "keys": keys,
                "seconds": seconds,
                "x": x,
                "y": y,
                "element_source": element_source,
                "element_target": element_target,
            }
            payload = {k: v for k, v in payload.items() if v is not None}
            result = await self.browser_service.perform_action(action, payload)
            if result.get("success"):
                return self.success_response(result)
            return self.fail_response(result.get("message", "Browser action failed"))
        except NotImplementedError as exc:
            return self.fail_response(str(exc))
        except Exception as exc:
            return self.fail_response(f"Browser action failed: {exc}")

    async def get_current_state(self) -> ToolResult:
        try:
            state = await self.browser_service.current_state()
            return self.success_response(state)
        except NotImplementedError:
            return self.fail_response("Browser state retrieval not supported")
        except Exception as exc:
            return self.fail_response(f"Failed to get browser state: {exc}")
