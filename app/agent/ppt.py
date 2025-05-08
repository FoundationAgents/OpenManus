import json
from typing import Any, Dict, List

from pydantic import Field
from app.tool import Terminate, Validator, ToolCollection, LatexGenerator
from app.agent.toolcall import ToolCallAgent
from app.logger import logger
from app.schema import AgentState, Message, ToolCall
from app.tool import (
    ToolCollection,
)
import uuid
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function

class FixedToolCallAgent(ToolCallAgent):
    """
    Agent that executes a fixed sequence of tools, potentially terminating
    early if the validator tool indicates completion.
    """

    name: str = "fixed_toolcall"
    description: str = (
        "an agent that executes a fixed sequence of tools in predefined order, "
        "potentially terminating early based on validator feedback."
    )

    available_tools: ToolCollection = ToolCollection(
        LatexGenerator(), Validator()
    )


    max_steps: int = 7
    curr_step: int = 0


    async def think(self) -> bool:
        """Process current state and decide next actions using tools"""
        # pick which of your tools to call
        tool_idx = self.curr_step % len(self.available_tools.tools)
        tool_meta = self.available_tools.tools[tool_idx]


        payload = {
            "request": self.memory.messages[0].content,
            "history": str(self.memory.messages),
        }
        arg_str = json.dumps(payload)

        # build the Function descriptor
        func_call = Function(
            name=tool_meta.name,
            arguments=arg_str,
        )

        # generate a proper call ID
        call_id = f"call_{uuid.uuid4().hex}"

        # wrap it up in a ChatCompletionMessageToolCall
        tool_call = ChatCompletionMessageToolCall(
            id=call_id,
            function=func_call,
            type= "function"
        )

        # assign to self.tool_calls just like the SDK would
        self.tool_calls = tool_calls = [tool_call]
        logger.info(
            f"🛠️ {self.name} selected {len(tool_calls) if tool_calls else 0} tools to use"
        )
        self.curr_step += 1

        return True
