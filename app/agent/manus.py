import os
from datetime import datetime
from typing import Optional

from pydantic import Field, model_validator

from app.agent.browser import BrowserContextHelper
from app.agent.react import ReActAgent
from app.agent.toolcall import ToolCallContextHelper
from app.config import config
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import Message
from app.tool import Terminate, ToolCollection
from app.tool.base import BaseTool
from app.tool.bash import Bash
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.create_chat_completion import CreateChatCompletion
from app.tool.deep_research import DeepResearch
from app.tool.planning import PlanningTool
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.web_search import WebSearch

SYSTEM_TOOLS: list[BaseTool] = [
    Bash(),
    WebSearch(),
    DeepResearch(),
    BrowserUseTool(),
    StrReplaceEditor(),
    PlanningTool(),
    CreateChatCompletion(),
    PythonExecute(),
]

SYSTEM_TOOLS_MAP = {tool.name: tool.__class__ for tool in SYSTEM_TOOLS}


SYSTEM_MCP_TOOLS_MAP = {
    "mcp-everything": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-everything"],
        "description": "https://github.com/modelcontextprotocol/servers/tree/main/src/everything",
    },
    "excel": {
        "command": "npx",
        "args": ["-y", "@negokaz/excel-mcp-server"],
        "env": {"EXCEL_MCP_PAGING_CELLS_LIMIT": "4000"},
    },
}


class Manus(ReActAgent):
    """A versatile general-purpose agent."""

    name: str = "Manus"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    system_prompt: str = SYSTEM_PROMPT.format(
        directory="/workspace",
        task_id="Not Specified",
        task_dir="Not Specified",
        real_task_dir=config.workspace_root,
        language="English",
        current_date=datetime.now().strftime("%Y-%m-%d"),
    )
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_steps: int = 20

    tool_call_context_helper: Optional[ToolCallContextHelper] = None
    browser_context_helper: Optional[BrowserContextHelper] = None

    task_dir: str = ""
    language: Optional[str] = Field(None, description="Language for the agent")

    async def initialize(
        self,
        task_id: str,
        language: Optional[str] = None,
        tools: Optional[list[str]] = None,
    ):
        self.task_id = task_id
        self.language = language
        self.task_dir = f"/workspace/{task_id}"

        if not os.path.exists(self.task_dir):
            os.makedirs(self.task_dir)

        self.system_prompt = SYSTEM_PROMPT.format(
            directory="/workspace",
            task_id=self.task_id,
            task_dir=self.task_dir,
            real_task_dir=os.path.join(
                config.workspace_root, self.task_dir.replace("/workspace/", "")
            ),
            language=self.language or "English",
            current_date=datetime.now().strftime("%Y-%m-%d"),
        )
        self.next_step_prompt = NEXT_STEP_PROMPT.format(
            language=self.language or "English",
        )

        self.memory.add_message(Message.system_message(self.system_prompt))

        self.browser_context_helper = BrowserContextHelper(self)
        self.tool_call_context_helper = ToolCallContextHelper(self)
        # Add general-purpose tools to the tool collection
        self.tool_call_context_helper.available_tools = ToolCollection(
            Terminate(),
        )
        if tools:
            for tool_name in tools:
                if tool_name in SYSTEM_TOOLS_MAP:
                    inst = SYSTEM_TOOLS_MAP[tool_name]()
                    await self.tool_call_context_helper.add_tool(inst)
                    if hasattr(inst, "llm"):
                        inst.llm = self.llm
                elif tool_name in SYSTEM_MCP_TOOLS_MAP:
                    t = SYSTEM_MCP_TOOLS_MAP[tool_name]
                    await self.tool_call_context_helper.add_mcp(
                        {
                            "client_id": tool_name,
                            "command": t["command"],
                            "args": t["args"],
                            "env": t["env"],
                        }
                    )
        return self

    @model_validator(mode="after")
    def initialize_helper(self) -> "Manus":
        return self

    async def think(self) -> bool:
        """Process current state and decide next actions with appropriate context."""
        original_prompt = self.next_step_prompt
        browser_in_use = self._check_browser_in_use_recently()

        if browser_in_use:
            self.next_step_prompt = (
                await self.browser_context_helper.format_next_step_prompt()
            )

        result = await self.tool_call_context_helper.ask_tool()

        # Restore original prompt
        self.next_step_prompt = original_prompt

        return result

    async def act(self) -> str:
        """Execute decided actions"""
        results = await self.tool_call_context_helper.execute_tool()
        return "\n\n".join(results)

    def _check_browser_in_use_recently(self) -> bool:
        """Check if the browser is in use by looking at the last 3 messages."""
        recent_messages = self.memory.messages[-3:] if self.memory.messages else []
        browser_in_use = any(
            tc.function.name == BrowserUseTool().name
            for msg in recent_messages
            if msg.tool_calls
            for tc in msg.tool_calls
        )
        return browser_in_use

    async def cleanup(self):
        """Clean up Manus agent resources."""
        if self.browser_context_helper:
            await self.browser_context_helper.cleanup_browser()
        if self.tool_call_context_helper:
            await self.tool_call_context_helper.cleanup_tools()
