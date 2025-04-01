import os
from typing import Optional

from pydantic import Field

from app.agent.browser import BrowserAgent
from app.config import config
from app.prompt.browser import NEXT_STEP_PROMPT as BROWSER_NEXT_STEP_PROMPT
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import Message
from app.tool import Terminate, ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.planning import PlanningTool
from app.tool.python_execute import PythonExecute
from app.tool.str_replace_editor import StrReplaceEditor


class Manus(BrowserAgent):
    """
    A versatile general-purpose agent that uses planning to solve various tasks.

    This agent extends BrowserAgent with a comprehensive set of tools and capabilities,
    including Python execution, web browsing, file operations, and information retrieval
    to handle a wide range of user requests.
    """

    name: str = "Manus"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    system_prompt: str = SYSTEM_PROMPT.format(
        directory=config.workspace_root,
        task_id="Not Specified",
        task_dir="Not Specified",
        language="English",
    )
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 20

    # Add general-purpose tools to the tool collection
    available_tools: ToolCollection = Field(default_factory=lambda: ToolCollection())

    task_id: Optional[str] = Field(None, description="Task ID for the agent")
    language: Optional[str] = Field(None, description="Language for the agent")

    def initialize(self, task_id: str, language: Optional[str] = None):
        self.task_id = task_id
        self.language = language
        task_dir = f"{config.workspace_root}/{task_id}"

        self.available_tools.add_tools(
            PlanningTool(),
            PythonExecute(),
            StrReplaceEditor(),
            Terminate(),
            BrowserUseTool(llm=self.llm),
        )

        if not os.path.exists(task_dir):
            os.makedirs(task_dir)

        self.system_prompt = SYSTEM_PROMPT.format(
            task_id=self.task_id,
            directory=config.workspace_root,
            task_dir=task_dir,
            language=self.language or "English",
        )

        self.memory.add_message(Message.system_message(self.system_prompt))
        return self

    async def think(self) -> bool:
        """Process current state and decide next actions with appropriate context."""
        # Store original prompt
        original_prompt = self.next_step_prompt

        # Only check recent messages (last 3) for browser activity
        recent_messages = self.memory.messages[-3:] if self.memory.messages else []
        browser_in_use = any(
            "browser_use" in msg.content.lower()
            for msg in recent_messages
            if hasattr(msg, "content") and isinstance(msg.content, str)
        )

        if browser_in_use:
            # Override with browser-specific prompt temporarily to get browser context
            self.next_step_prompt = BROWSER_NEXT_STEP_PROMPT

        # Call parent's think method
        result = await super().think()

        # Restore original prompt
        self.next_step_prompt = original_prompt

        return result
