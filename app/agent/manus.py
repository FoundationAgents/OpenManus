from typing import Dict, List, Optional

from pydantic import Field, model_validator

from app.agent.browser import BrowserContextHelper
from app.agent.toolcall import ToolCallAgent
from app.config import config
from app.logger import logger
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import Message
from app.skill_manager import skill_manager
from app.tool import Terminate, ToolCollection
from app.tool.ask_human import AskHuman
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.mcp import MCPClients, MCPClientTool
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor


class Manus(ToolCallAgent):
    """A versatile general-purpose agent with support for both local and MCP tools."""

    name: str = "Manus"
    description: str = "A versatile agent that can solve various tasks using multiple tools including MCP-based tools"

    system_prompt: str = SYSTEM_PROMPT.format(directory=config.workspace_root)
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 20

    # MCP clients for remote tool access
    mcp_clients: MCPClients = Field(default_factory=MCPClients)

    # Add general-purpose tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(),
            BrowserUseTool(),
            StrReplaceEditor(),
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

    # Active skills for this agent
    active_skills: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def initialize_helper(self) -> "Manus":
        """Initialize basic components synchronously."""
        self.browser_context_helper = BrowserContextHelper(self)
        return self

    @classmethod
    async def create(cls, **kwargs) -> "Manus":
        """Factory method to create and properly initialize a Manus instance."""
        instance = cls(**kwargs)
        await instance.initialize_mcp_servers()
        instance._initialized = True
        return instance

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
            self._initialized = False
        # Clear active skills
        self.active_skills.clear()

    async def activate_skills(self, user_request: str) -> None:
        """Automatically activate relevant skills based on user request."""
        if not config.skills_config.enabled or not config.skills_config.auto_activate:
            return

        relevant_skills = skill_manager.get_relevant_skills(
            user_request,
            threshold=config.skills_config.threshold,
        )

        for skill in relevant_skills:
            if skill.name not in self.active_skills:
                self.active_skills[skill.name] = skill.get_full_prompt()
                logger.info(f"🎯 Activated skill: {skill.name}")

    def get_skill_system_prompt(self) -> Optional[str]:
        """Get combined system prompt from all active skills."""
        if not self.active_skills:
            return None

        skill_prompts = []
        for skill_name, skill_content in self.active_skills.items():
            skill_prompts.append(
                f"\n=== Skill: {skill_name} ===\n{skill_content}\n=== End Skill ===\n"
            )

        combined = (
            "\n\n"
            + "=" * 50
            + "\n"
            + "Active Skills:\n"
            + "=" * 50
            + "\n"
            + "\n".join(skill_prompts)
        )
        return combined

    async def activate_skill_by_name(self, skill_name: str) -> bool:
        """Manually activate a specific skill by name."""
        skill = skill_manager.get_skill(skill_name)
        if not skill:
            logger.warning(f"Skill not found: {skill_name}")
            return False

        if skill.name in self.active_skills:
            logger.info(f"Skill already active: {skill_name}")
            return True

        self.active_skills[skill.name] = skill.get_full_prompt()
        logger.info(f"🎯 Manually activated skill: {skill_name}")
        return True

    def deactivate_skill(self, skill_name: str) -> bool:
        """Deactivate a specific skill."""
        if skill_name not in self.active_skills:
            logger.warning(f"Skill not active: {skill_name}")
            return False

        del self.active_skills[skill_name]
        logger.info(f"🚫 Deactivated skill: {skill_name}")
        return True

    def list_active_skills(self) -> List[str]:
        """List all currently active skills."""
        return list(self.active_skills.keys())

    async def think(self) -> bool:
        """Process current state and decide next actions with appropriate context."""
        if not self._initialized:
            await self.initialize_mcp_servers()
            self._initialized = True

        # Activate relevant skills on first think
        if not self.active_skills and self.memory.messages:
            # Get user's first request
            for msg in self.memory.messages[:3]:
                if msg.role == "user" and msg.content:
                    await self.activate_skills(msg.content)
                    break

        original_prompt = self.next_step_prompt
        recent_messages = self.memory.messages[-3:] if self.memory.messages else []
        browser_in_use = any(
            tc.function.name == BrowserUseTool().name
            for msg in recent_messages
            if msg.tool_calls
            for tc in msg.tool_calls
        )

        if browser_in_use:
            self.next_step_prompt = (
                await self.browser_context_helper.format_next_step_prompt()
            )

        # Add skill prompts to context
        skill_system_prompt = self.get_skill_system_prompt()
        if skill_system_prompt and self.system_prompt:
            # Temporarily append skill prompts to system prompt
            self.system_prompt = self.system_prompt + skill_system_prompt

        result = await super().think()

        # Restore original prompt
        self.next_step_prompt = original_prompt

        # Remove skill prompts from system prompt to avoid accumulating
        if skill_system_prompt:
            # Remove skill section that was added
            base_prompt = self.system_prompt
            if "Active Skills:" in base_prompt:
                base_prompt = base_prompt[: base_prompt.index("Active Skills:")]

        return result
