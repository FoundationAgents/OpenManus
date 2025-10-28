from typing import Dict, List, Optional

from pydantic import Field, model_validator

from app.agent.browser import BrowserContextHelper
from app.agent.toolcall import ToolCallAgent
from app.config import config
from app.sandbox.providers import create_sandbox_provider, SandboxProvider
from app.logger import logger
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tool import Terminate, ToolCollection
from app.tool.ask_human import AskHuman
from app.tool.mcp import MCPClients, MCPClientTool
from app.tool.sandbox.sb_browser_tool import SandboxBrowserTool
from app.tool.sandbox.sb_computer_tool import SandboxComputerTool
from app.tool.sandbox.sb_mobile_tool import SandboxMobileTool
from app.tool.sandbox.sb_files_tool import SandboxFilesTool
from app.tool.sandbox.sb_shell_tool import SandboxShellTool
from app.tool.sandbox.sb_vision_tool import SandboxVisionTool


class SandboxManus(ToolCallAgent):
    """A versatile general-purpose agent with support for both local and MCP tools."""

    name: str = "SandboxManus"
    description: str = "A versatile agent that can solve various tasks using multiple sandbox-tools including MCP-based tools"

    system_prompt: str = SYSTEM_PROMPT.format(directory=config.workspace_root)
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 20

    # MCP clients for remote tool access
    mcp_clients: MCPClients = Field(default_factory=MCPClients)

    # Add general-purpose tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            # PythonExecute(),
            # BrowserUseTool(),
            # StrReplaceEditor(),
            AskHuman(),
            Terminate(),
        )
    )

    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])
    browser_context_helper: Optional[BrowserContextHelper] = None

    # Track connected MCP servers
    connected_servers: Dict[str, str] = Field(
        default_factory=dict
    )  # server_id -> url/command
    _initialized: bool = False
    sandbox_link: Optional[dict[str, dict[str, str]]] = Field(default_factory=dict)
    sandbox_provider: Optional[SandboxProvider] = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def initialize_helper(self) -> "SandboxManus":
        """Initialize basic components synchronously."""
        self.browser_context_helper = BrowserContextHelper(self)
        return self

    @classmethod
    async def create(cls, **kwargs) -> "SandboxManus":
        """Factory method to create and properly initialize a Manus instance."""
        instance = cls(**kwargs)
        await instance.initialize_mcp_servers()
        await instance.initialize_sandbox_tools()
        instance._initialized = True
        return instance

    async def initialize_sandbox_tools(self) -> None:
        try:
            provider = create_sandbox_provider()
            await provider.initialize()
            self.sandbox_provider = provider

            metadata = provider.metadata()
            link_key = (
                metadata.extra.get("sandbox_id")
                if metadata.extra.get("sandbox_id")
                else metadata.provider
            )
            if metadata.links:
                self.sandbox_link[link_key] = metadata.links
                for name, url in metadata.links.items():
                    logger.info(f"Sandbox {name} link: {url}")

            tools = [
                SandboxShellTool(provider.shell_service()),
                SandboxFilesTool(provider.file_service()),
            ]

            browser_service = provider.browser_service()
            if browser_service:
                tools.append(SandboxBrowserTool(browser_service))

            computer_service = provider.computer_service()
            if computer_service:
                tools.append(SandboxComputerTool(computer_service))

            mobile_service = provider.mobile_service()
            if mobile_service:
                tools.append(SandboxMobileTool(mobile_service))

            vision_service = provider.vision_service()
            if vision_service:
                tools.append(SandboxVisionTool(vision_service))

            self.available_tools.add_tools(*tools)

        except Exception as e:
            logger.error(f"Error initializing sandbox tools: {e}")
            raise

    async def initialize_mcp_servers(self) -> None:
        """Initialize connections to configured MCP servers."""
        for server_id, server_config in config.mcp_config.servers.items():
            try:
                if server_config.type == "sse":
                    if server_config.url:
                        await self.connect_mcp_server(server_config.url, server_id)
                        logger.info(
                            f"Connected to MCP server {server_id} at {server_config.url}"
                        )
                elif server_config.type == "stdio":
                    if server_config.command:
                        await self.connect_mcp_server(
                            server_config.command,
                            server_id,
                            use_stdio=True,
                            stdio_args=server_config.args,
                        )
                        logger.info(
                            f"Connected to MCP server {server_id} using command {server_config.command}"
                        )
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {server_id}: {e}")

    async def connect_mcp_server(
        self,
        server_url: str,
        server_id: str = "",
        use_stdio: bool = False,
        stdio_args: List[str] = None,
    ) -> None:
        """Connect to an MCP server and add its tools."""
        if use_stdio:
            await self.mcp_clients.connect_stdio(
                server_url, stdio_args or [], server_id
            )
            self.connected_servers[server_id or server_url] = server_url
        else:
            await self.mcp_clients.connect_sse(server_url, server_id)
            self.connected_servers[server_id or server_url] = server_url

        # Update available tools with only the new tools from this server
        new_tools = [
            tool for tool in self.mcp_clients.tools if tool.server_id == server_id
        ]
        self.available_tools.add_tools(*new_tools)

    async def disconnect_mcp_server(self, server_id: str = "") -> None:
        """Disconnect from an MCP server and remove its tools."""
        await self.mcp_clients.disconnect(server_id)
        if server_id:
            self.connected_servers.pop(server_id, None)
        else:
            self.connected_servers.clear()

        # Rebuild available tools without the disconnected server's tools
        base_tools = [
            tool
            for tool in self.available_tools.tools
            if not isinstance(tool, MCPClientTool)
        ]
        self.available_tools = ToolCollection(*base_tools)
        self.available_tools.add_tools(*self.mcp_clients.tools)

    async def cleanup(self):
        """Clean up Manus agent resources."""
        if self.browser_context_helper:
            await self.browser_context_helper.cleanup_browser()
        # Disconnect from all MCP servers only if we were initialized
        if self._initialized:
            await self.disconnect_mcp_server()
            if self.sandbox_provider:
                try:
                    await self.sandbox_provider.cleanup()
                except Exception:
                    logger.warning("Failed to cleanup sandbox provider", exc_info=True)
                self.sandbox_provider = None
            self._initialized = False

    async def think(self) -> bool:
        """Process current state and decide next actions with appropriate context."""
        if not self._initialized:
            await self.initialize_mcp_servers()
            self._initialized = True

        original_prompt = self.next_step_prompt
        recent_messages = self.memory.messages[-3:] if self.memory.messages else []
        browser_tool_name = "sandbox_browser"
        browser_in_use = any(
            tc.function.name == browser_tool_name
            for msg in recent_messages
            if msg.tool_calls
            for tc in msg.tool_calls
        )

        if browser_in_use:
            self.next_step_prompt = (
                await self.browser_context_helper.format_next_step_prompt()
            )

        result = await super().think()

        # Restore original prompt
        self.next_step_prompt = original_prompt

        return result
