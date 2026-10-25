import json
from typing import TYPE_CHECKING, Optional

from app.agent.mcp import MCPAgent
from app.logger import logger
from app.prompt.browser import NEXT_STEP_PROMPT
from app.schema import Message
from app.tool.terminate import Terminate


# Avoid circular import if BrowserAgent needs BrowserContextHelper
if TYPE_CHECKING:
    from app.agent.base import BaseAgent  # Or wherever memory is defined


_SANDBOX_BROWSER_TOOL_NAME = "sandbox_browser"


class BrowserContextHelper:
    def __init__(self, agent: "BaseAgent"):
        self.agent = agent
        self._current_base64_image: Optional[str] = None

    async def get_browser_state(self) -> Optional[dict]:
        browser_tool = self.agent.available_tools.get_tool(_SANDBOX_BROWSER_TOOL_NAME)
        if not browser_tool or not hasattr(browser_tool, "get_current_state"):
            logger.warning("SandboxBrowserTool not found or has no current state")
            return None
        try:
            result = await browser_tool.get_current_state()
            if result.error:
                logger.debug(f"Browser state error: {result.error}")
                return None
            if hasattr(result, "base64_image") and result.base64_image:
                self._current_base64_image = result.base64_image
            else:
                self._current_base64_image = None
            return json.loads(result.output)
        except Exception as e:
            logger.debug(f"Failed to get browser state: {str(e)}")
            return None

    async def format_next_step_prompt(self) -> str:
        """Gets browser state and formats the browser prompt."""
        browser_state = await self.get_browser_state()
        url_info, tabs_info, content_above_info, content_below_info = "", "", "", ""
        results_info = ""  # Or get from agent if needed elsewhere

        if browser_state and not browser_state.get("error"):
            url_info = f"\n   URL: {browser_state.get('url', 'N/A')}\n   Title: {browser_state.get('title', 'N/A')}"
            tabs = browser_state.get("tabs", [])
            if tabs:
                tabs_info = f"\n   {len(tabs)} tab(s) available"
            pixels_above = browser_state.get("pixels_above", 0)
            pixels_below = browser_state.get("pixels_below", 0)
            if pixels_above > 0:
                content_above_info = f" ({pixels_above} pixels)"
            if pixels_below > 0:
                content_below_info = f" ({pixels_below} pixels)"

            if self._current_base64_image:
                image_message = Message.user_message(
                    content="Current browser screenshot:",
                    base64_image=self._current_base64_image,
                )
                self.agent.memory.add_message(image_message)
                self._current_base64_image = None  # Consume the image after adding

        return NEXT_STEP_PROMPT.format(
            url_placeholder=url_info,
            tabs_placeholder=tabs_info,
            content_above_placeholder=content_above_info,
            content_below_placeholder=content_below_info,
            results_placeholder=results_info,
        )

    async def cleanup_browser(self):
        browser_tool = self.agent.available_tools.get_tool(_SANDBOX_BROWSER_TOOL_NAME)
        if browser_tool and hasattr(browser_tool, "cleanup"):
            await browser_tool.cleanup()


class BrowserAgent(MCPAgent):
    """Browser-only agent backed by the Browser Use CLI 3.0 MCP server."""

    name: str = "browser"
    description: str = "A browser agent that can control a browser to accomplish tasks"
    system_prompt: str = """\
Use Browser Use CLI 3.0 through `browser_exec`. Pass the Python body from CLI
examples as the `code` argument. Use `browser_screenshot` when visual context
is needed. The browser-harness session persists across calls. Use `terminate`
when the task is complete.
"""

    async def initialize(self) -> None:
        await super().initialize(
            connection_type="stdio",
            command="uvx",
            args=["browser-use", "--cli-mcp"],
            server_id="browser_use",
            tool_name_prefix=False,
        )
        self.available_tools.add_tool(Terminate())

    @classmethod
    async def create(cls, **kwargs) -> "BrowserAgent":
        instance = cls(**kwargs)
        await instance.initialize()
        return instance

    async def run(self, request: Optional[str] = None) -> str:
        if not self.mcp_clients.sessions:
            await self.initialize()
        return await super().run(request)
