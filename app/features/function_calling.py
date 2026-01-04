"""Minimax M2 Function Calling & Interleaved Thinking

Implements Tool Use and Interleaved Thinking for advanced agentic capabilities.
"""

import asyncio
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import aiohttp


class ContentBlockType(Enum):
    """Content block types in responses."""

    THINKING = "thinking"
    TEXT = "text"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


@dataclass
class ToolParameter:
    """Tool parameter definition."""

    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[List[str]] = None

    def to_dict(self):
        """Convert to dictionary."""
        result = {
            "type": self.type,
            "description": self.description,
        }
        if self.enum:
            result["enum"] = self.enum
        return result


@dataclass
class ToolDefinition:
    """Tool definition for function calling."""

    name: str
    description: str
    parameters: Dict[str, ToolParameter]

    def to_dict(self):
        """Convert to Minimax API format."""
        properties = {}
        required = []

        for param_name, param in self.parameters.items():
            properties[param_name] = param.to_dict()
            if param.required:
                required.append(param_name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


@dataclass
class ThinkingBlock:
    """Thinking block from model response."""

    type: str = "thinking"
    thinking: str = ""

    def to_dict(self):
        """Convert to dictionary."""
        return {"type": self.type, "thinking": self.thinking}


@dataclass
class TextBlock:
    """Text block from model response."""

    type: str = "text"
    text: str = ""

    def to_dict(self):
        """Convert to dictionary."""
        return {"type": self.type, "text": self.text}


@dataclass
class ToolUseBlock:
    """Tool use block from model response."""

    type: str = "tool_use"
    id: str = ""
    name: str = ""
    input: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "type": self.type,
            "id": self.id,
            "name": self.name,
            "input": self.input,
        }


@dataclass
class ToolResultBlock:
    """Tool result block for conversation history."""

    type: str = "tool_result"
    tool_use_id: str = ""
    content: str = ""

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "type": self.type,
            "tool_use_id": self.tool_use_id,
            "content": self.content,
        }


@dataclass
class Message:
    """Message in conversation history."""

    role: str  # user, assistant, system
    content: Any  # str or list of content blocks

    def to_dict(self):
        """Convert to dictionary."""
        if isinstance(self.content, str):
            return {"role": self.role, "content": self.content}
        elif isinstance(self.content, list):
            return {
                "role": self.role,
                "content": [
                    block.to_dict() if hasattr(block, "to_dict") else block
                    for block in self.content
                ],
            }
        return {"role": self.role, "content": self.content}


class FunctionCallRegistry:
    """Registry for callable functions."""

    def __init__(self):
        """Initialize registry."""
        self.functions: Dict[str, Callable] = {}
        self.tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, ToolParameter],
        func: Callable,
    ):
        """Register a function.

        Args:
            name: Function name.
            description: Function description.
            parameters: Parameter definitions.
            func: Callable function.
        """
        self.functions[name] = func
        self.tools[name] = ToolDefinition(name, description, parameters)

    def get_tool_definitions(self) -> List[Dict]:
        """Get tool definitions for API.

        Returns:
            List of tool definitions.
        """
        return [tool.to_dict() for tool in self.tools.values()]

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a registered function.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Function arguments.

        Returns:
            Function result as string.
        """
        if tool_name not in self.functions:
            return f"Error: Tool '{tool_name}' not found"

        try:
            func = self.functions[tool_name]
            if asyncio.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
            return str(result)
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"


class MinimaxFunctionCaller:
    """Minimax M2 function calling client with interleaved thinking."""

    def __init__(
        self,
        api_key: str,
        model: str = "MiniMax-M2",
        base_url: str = "https://api.minimax.io",
    ):
        """Initialize function caller.

        Args:
            api_key: Minimax API key.
            model: Model name.
            base_url: API base URL.
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.registry = FunctionCallRegistry()
        self.conversation_history: List[Message] = []

    def register_function(
        self,
        name: str,
        description: str,
        parameters: Dict[str, ToolParameter],
        func: Callable,
    ):
        """Register a function for tool calling.

        Args:
            name: Function name.
            description: Function description.
            parameters: Parameter definitions.
            func: Callable function.
        """
        self.registry.register(name, description, parameters, func)

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers.

        Returns:
            Headers dictionary.
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _call_api(
        self, messages: List[Message], tools: Optional[List[Dict]] = None
    ) -> Dict:
        """Call Minimax API.

        Args:
            messages: Conversation messages.
            tools: Tool definitions.

        Returns:
            API response.
        """
        payload = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages],
            "max_tokens": 4096,
        }

        if tools:
            payload["tools"] = tools

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API error: {error_text}")
                    return await response.json()
            except Exception as e:
                raise Exception(f"Minimax API error: {str(e)}")

    def _parse_response(self, response: Dict) -> Tuple[List, bool]:
        """Parse API response into content blocks.

        Args:
            response: API response.

        Returns:
            Tuple of (content_blocks, has_tool_calls).
        """
        content_blocks = []
        has_tool_calls = False

        choice = response["choices"][0]
        message = choice["message"]

        # Handle content field (can be string or list)
        if isinstance(message.get("content"), str):
            content = message["content"]
            # Parse thinking tags if present
            if "<think>" in content:
                think_start = content.find("<think>")
                think_end = content.find("</think>")
                if think_start != -1 and think_end != -1:
                    thinking_text = content[think_start + 7 : think_end]
                    content_blocks.append(ThinkingBlock(thinking=thinking_text))
                    remaining = content[:think_start] + content[think_end + 8 :]
                    if remaining.strip():
                        content_blocks.append(TextBlock(text=remaining.strip()))
            else:
                content_blocks.append(TextBlock(text=content))

        # Handle tool_calls
        if "tool_calls" in message:
            has_tool_calls = True
            for tool_call in message["tool_calls"]:
                block = ToolUseBlock(
                    id=tool_call.get("id", ""),
                    name=tool_call["function"]["name"],
                    input=json.loads(tool_call["function"]["arguments"]),
                )
                content_blocks.append(block)

        return content_blocks, has_tool_calls

    async def call_with_tools(self, user_message: str, max_iterations: int = 10) -> str:
        """Call Minimax with tool use and interleaved thinking.

        Args:
            user_message: User input message.
            max_iterations: Maximum iterations for tool calling loop.

        Returns:
            Final response text.
        """
        # Add user message to history
        self.conversation_history.append(Message("user", user_message))

        for iteration in range(max_iterations):
            # Call API with tools
            tools = self.registry.get_tool_definitions()
            response = await self._call_api(self.conversation_history, tools)

            # Parse response
            content_blocks, has_tool_calls = self._parse_response(response)

            # Print thinking if present
            for block in content_blocks:
                if isinstance(block, ThinkingBlock):
                    print(f"\n💭 Thinking:\n{block.thinking}")

            # Add assistant response to history
            self.conversation_history.append(Message("assistant", content_blocks))

            # If no tool calls, return final text
            if not has_tool_calls:
                for block in content_blocks:
                    if isinstance(block, TextBlock):
                        return block.text
                return "No response generated"

            # Execute tool calls
            tool_results = []
            for block in content_blocks:
                if isinstance(block, ToolUseBlock):
                    print(f"\n🔧 Executing tool: {block.name}")
                    print(f"   Input: {json.dumps(block.input, ensure_ascii=False)}")

                    result = await self.registry.execute(block.name, block.input)
                    print(f"   Result: {result}")

                    tool_results.append(
                        ToolResultBlock(tool_use_id=block.id, content=result)
                    )

            # Add tool results to history
            if tool_results:
                self.conversation_history.append(Message("user", tool_results))

        return "Max iterations reached"

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
