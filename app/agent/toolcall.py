import asyncio
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

from pydantic import BaseModel, model_validator

from app.agent.base import BaseAgent, BaseAgentEvents
from app.agent.react import ReActAgent
from app.exceptions import TokenLimitExceeded
from app.logger import logger
from app.sandbox.core.manager import SandboxManager
from app.schema import TOOL_CHOICE_TYPE, AgentState, Message, ToolCall, ToolChoice
from app.tool import CreateChatCompletion, Terminate, ToolCollection
from app.tool.base import BaseTool
from app.tool.mcp import MCPClients
from app.tool.mcp_sandbox import MCPSandboxClients

# Avoid circular import if BrowserAgent needs BrowserContextHelper
if TYPE_CHECKING:
    from app.agent.base import BaseAgent  # Or wherever memory is defined


TOOL_CALL_REQUIRED = "Tool calls required but none provided"


class ToolCallAgentEvents(BaseAgentEvents):
    TOOL_START = "agent:tool:start"
    TOOL_COMPLETE = "agent:tool:complete"
    TOOL_ERROR = "agent:tool:error"
    TOOL_SELECTED = "agent:tool:selected"
    TOOL_EXECUTE_START = "agent:tool:execute:start"
    TOOL_EXECUTE_COMPLETE = "agent:tool:execute:complete"


class MCPToolCallExtension:
    """A context manager for handling multiple MCP client connections.

    This class is responsible for:
    1. Maintaining multiple MCP client connections
    2. Managing client lifecycles
    3. Providing CRUD operations for clients
    """

    def __init__(self):
        # Dictionary to store multiple client connections
        # key: client_id, value: MCPClients instance
        self.clients: Dict[str, Union[MCPClients, MCPSandboxClients]] = {}

    async def add_sse_client(self, client_id: str, server_url: str) -> MCPClients:
        """Add a new SSE-based MCP client connection.

        Args:
            client_id: Unique identifier for the client
            server_url: URL of the MCP server

        Returns:
            MCPClients: The newly created client instance

        Raises:
            ValueError: If client_id already exists
        """
        if client_id in self.clients:
            raise ValueError(f"Client ID '{client_id}' already exists")

        client = MCPClients(client_id=client_id)
        await client.connect_sse(server_url=server_url)
        self.clients[client_id] = client
        return client

    async def add_sse_sandbox_client(
        self, client_id: str, server_url: str
    ) -> MCPSandboxClients:
        """Add a new SSE-based MCP client connection running in a sandbox.

        Args:
            client_id: Unique identifier for the client
            server_url: URL of the MCP server

        Returns:
            MCPSandboxClients: The newly created sandboxed client instance

        Raises:
            ValueError: If client_id already exists
        """
        if client_id in self.clients:
            raise ValueError(f"Client ID '{client_id}' already exists")

        client = MCPSandboxClients(client_id=client_id)
        await client.connect_sse(server_url=server_url)
        self.clients[client_id] = client
        return client

    async def add_stdio_client(
        self, client_id: str, command: str, args: Optional[List[str]] = None
    ) -> MCPClients:
        """Add a new STDIO-based MCP client connection.

        Args:
            client_id: Unique identifier for the client
            command: Command to execute
            args: List of command arguments

        Returns:
            MCPClients: The newly created client instance

        Raises:
            ValueError: If client_id already exists
        """
        if client_id in self.clients:
            raise ValueError(f"Client ID '{client_id}' already exists")

        client = MCPClients(client_id=client_id)
        await client.connect_stdio(command=command, args=args or [])
        self.clients[client_id] = client
        return client

    async def add_stdio_sandbox_client(
        self, client_id: str, command: str, args: Optional[List[str]] = None
    ) -> MCPSandboxClients:
        """Add a new STDIO-based MCP client connection running in a sandbox.

        Args:
            client_id: Unique identifier for the client
            command: Command to execute
            args: List of command arguments

        Returns:
            MCPSandboxClients: The newly created sandboxed client instance

        Raises:
            ValueError: If client_id already exists
        """
        if client_id in self.clients:
            raise ValueError(f"Client ID '{client_id}' already exists")

        client = MCPSandboxClients(client_id=client_id)
        await client.connect_stdio(command=command, args=args or [])
        self.clients[client_id] = client
        return client

    def get_client(
        self, client_id: str
    ) -> Optional[Union[MCPClients, MCPSandboxClients]]:
        """Retrieve a specific MCP client.

        Args:
            client_id: Unique identifier for the client

        Returns:
            Optional[Union[MCPClients, MCPSandboxClients]]: The client instance if found, None otherwise
        """
        return self.clients.get(client_id)

    async def remove_client(self, client_id: str) -> bool:
        """Remove and disconnect a specific MCP client connection.

        Args:
            client_id: Unique identifier for the client

        Returns:
            bool: True if client was found and removed, False otherwise
        """
        if client := self.clients.pop(client_id, None):
            await client.disconnect()
            return True
        return False

    async def disconnect_all(self) -> None:
        """Disconnect all MCP client connections."""
        for client_id in list(self.clients.keys()):
            await self.remove_client(client_id)

    def list_clients(self) -> List[str]:
        """Get a list of all client IDs.

        Returns:
            List[str]: List of all connected client IDs
        """
        return list(self.clients.keys())

    def get_client_count(self) -> int:
        """Get the current number of connected clients.

        Returns:
            int: Number of clients
        """
        return len(self.clients)

    async def __aenter__(self) -> "MCPToolCallExtension":
        """Async context manager entry point."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit point, ensures all connections are properly closed."""
        await self.disconnect_all()


class ToolCallContextHelper:
    available_tools: ToolCollection = ToolCollection(
        CreateChatCompletion(), Terminate()
    )

    mcp: MCPToolCallExtension = None

    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO  # type: ignore
    special_tool_names: List[str] = [Terminate().name]

    tool_calls: List[ToolCall] = []

    max_observe: int = 10000

    def __init__(self, agent: "BaseAgent"):
        self.agent = agent
        self.mcp = MCPToolCallExtension()

    async def add_tool(self, tool: BaseTool) -> None:
        """Add a new tool to the available tools collection."""
        self.available_tools.add_tool(tool)

    async def add_mcp(self, tool: dict) -> None:
        """Add a new MCP client to the available tools collection."""
        if isinstance(tool, dict) and "client_id" in tool and "server_url" in tool:
            await self.mcp.add_sse_client(tool["client_id"], tool["server_url"])
            client = self.mcp.get_client(tool["client_id"])
            if client:
                for mcp_tool in client.tool_map.values():
                    self.available_tools.add_tool(mcp_tool)
        elif isinstance(tool, dict) and "client_id" in tool and "command" in tool:
            await self.mcp.add_stdio_sandbox_client(
                tool["client_id"], tool["command"], tool.get("args", [])
            )
            client = self.mcp.get_client(tool["client_id"])
            if client:
                for mcp_tool in client.tool_map.values():
                    self.available_tools.add_tool(mcp_tool)

    async def ask_tool(self) -> bool:
        """Process current state and decide next actions using tools"""
        if self.agent.next_step_prompt:
            user_msg = Message.user_message(self.agent.next_step_prompt)
            self.agent.messages += [user_msg]

        try:
            # Get response with tool options
            response = await self.agent.llm.ask_tool(
                messages=self.agent.messages,
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choices,
            )
        except ValueError:
            raise
        except Exception as e:
            if hasattr(e, "__cause__") and isinstance(e.__cause__, TokenLimitExceeded):
                token_limit_error = e.__cause__
                logger.error(
                    f"🚨 Token limit error (from RetryError): {token_limit_error}"
                )
                self.agent.memory.add_message(
                    Message.assistant_message(
                        f"Maximum token limit reached, cannot continue execution: {str(token_limit_error)}"
                    )
                )
                self.agent.state = AgentState.FINISHED
                return False
            raise

        self.tool_calls = tool_calls = (
            response.tool_calls if response and response.tool_calls else []
        )
        content = response.content if response and response.content else ""

        # Log response info
        logger.info(f"✨ {self.agent.name}'s thoughts: {content}")
        logger.info(
            f"🛠️ {self.agent.name} selected {len(tool_calls) if tool_calls else 0} tools to use"
        )
        self.agent.emit(
            ToolCallAgentEvents.TOOL_SELECTED,
            {
                "thoughts": content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": call.type,
                        "index": call.index,
                        "function": {
                            "name": call.function.name,
                            "arguments": json.loads(call.function.arguments),
                        },
                    }
                    for call in tool_calls
                ],
            },
        )
        if tool_calls:
            tool_info = {
                "tools": [call.function.name for call in tool_calls],
                "arguments": tool_calls[0].function.arguments,
            }
            logger.info(f"🧰 Tools being prepared: {tool_info['tools']}")
            logger.info(f"🔧 Tool arguments: {tool_info['arguments']}")

        try:
            if response is None:
                raise RuntimeError("No response received from the LLM")

            # Handle different tool_choices modes
            if self.tool_choices == ToolChoice.NONE:
                if tool_calls:
                    logger.warning(
                        f"🤔 Hmm, {self.agent.name} tried to use tools when they weren't available!"
                    )
                if content:
                    self.agent.memory.add_message(Message.assistant_message(content))
                    return True
                return False

            # Create and add assistant message
            assistant_msg = (
                Message.from_tool_calls(content=content, tool_calls=self.tool_calls)
                if self.tool_calls
                else Message.assistant_message(content)
            )
            self.agent.memory.add_message(assistant_msg)

            if self.tool_choices == ToolChoice.REQUIRED and not self.tool_calls:
                return True  # Will be handled in act()

            # For 'auto' mode, continue with content if no commands but content exists
            if self.tool_choices == ToolChoice.AUTO and not self.tool_calls:
                return bool(content)

            return bool(self.tool_calls)
        except Exception as e:
            logger.error(
                f"🚨 Oops! The {self.agent.name}'s thinking process hit a snag: {e}"
            )
            self.agent.memory.add_message(
                Message.assistant_message(
                    f"Error encountered while processing: {str(e)}"
                )
            )
            return False

    async def execute_tool(self) -> str:
        """Execute tool calls and handle their results"""
        self.agent.emit(
            ToolCallAgentEvents.TOOL_START,
            {"tool_calls": [call.model_dump() for call in self.tool_calls]},
        )
        if not self.tool_calls:
            if self.tool_choices == ToolChoice.REQUIRED:
                raise ValueError(TOOL_CALL_REQUIRED)

            # Return last message content if no tool calls
            return (
                self.agent.messages[-1].content or "No content or commands to execute"
            )

        results = []

        for command in self.tool_calls:
            # Reset base64_image for each tool call
            self._current_base64_image = None

            result = await self.execute_tool_command(command)

            if self.max_observe:
                result = result[: self.max_observe]

            logger.info(
                f"🎯 Tool '{command.function.name}' completed its mission! Result: {result}"
            )

            # Add tool response to memory
            tool_msg = Message.tool_message(
                content=result,
                tool_call_id=command.id,
                name=command.function.name,
                base64_image=self._current_base64_image,
            )
            self.agent.memory.add_message(tool_msg)
            results.append(result)
        self.agent.emit(ToolCallAgentEvents.TOOL_COMPLETE, {"results": results})
        return results

    async def execute_tool_command(self, command: ToolCall) -> str:
        """Execute a single tool call with robust error handling"""
        if not command or not command.function or not command.function.name:
            return "Error: Invalid command format"

        name = command.function.name
        if name not in self.available_tools.tool_map:
            return f"Error: Unknown tool '{name}'"

        try:
            # Parse arguments
            args = json.loads(command.function.arguments or "{}")

            # Execute the tool
            logger.info(f"🔧 Activating tool: '{name}'...")
            self.agent.emit(
                ToolCallAgentEvents.TOOL_EXECUTE_START, {"name": name, "args": args}
            )
            result = await self.available_tools.execute(name=name, tool_input=args)
            self.agent.emit(
                ToolCallAgentEvents.TOOL_EXECUTE_COMPLETE,
                {
                    "name": name,
                    "result": (
                        result.model_dump()
                        if isinstance(result, BaseModel)
                        else str(result)
                    ),
                },
            )
            # Handle special tools
            await self.handle_special_tool(name=name, result=result)

            # Check if result is a ToolResult with base64_image
            if hasattr(result, "base64_image") and result.base64_image:
                # Store the base64_image for later use in tool_message
                self._current_base64_image = result.base64_image

                # Format result for display
                observation = (
                    f"Observed output of cmd `{name}` executed:\n{str(result)}"
                    if result
                    else f"Cmd `{name}` completed with no output"
                )
                return observation

            # Format result for display (standard case)
            observation = (
                f"Observed output of cmd `{name}` executed:\n{str(result)}"
                if result
                else f"Cmd `{name}` completed with no output"
            )

            return observation
        except json.JSONDecodeError:
            error_msg = f"Error parsing arguments for {name}: Invalid JSON format"
            logger.error(
                f"📝 Oops! The arguments for '{name}' don't make sense - invalid JSON, arguments:{command.function.arguments}"
            )
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"⚠️ Tool '{name}' encountered a problem: {str(e)}"
            logger.exception(error_msg)
            return f"Error: {error_msg}"

    async def handle_special_tool(self, name: str, result: Any, **kwargs):
        """Handle special tool execution and state changes"""
        if not self._is_special_tool(name):
            return

        if self._should_finish_execution(name=name, result=result, **kwargs):
            # Set agent state to finished
            logger.info(f"🏁 Special tool '{name}' has completed the task!")
            self.agent.state = AgentState.FINISHED

    @staticmethod
    def _should_finish_execution(**kwargs) -> bool:
        """Determine if tool execution should finish the agent"""
        return True

    def _is_special_tool(self, name: str) -> bool:
        """Check if tool name is in special tools list"""
        return name.lower() in [n.lower() for n in self.special_tool_names]

    async def cleanup_tools(self):
        """Clean up resources used by the agent's tools."""
        logger.info(f"🧹 Cleaning up resources for agent '{self.agent.name}'...")
        for tool_name, tool_instance in self.available_tools.tool_map.items():
            if hasattr(tool_instance, "cleanup") and asyncio.iscoroutinefunction(
                tool_instance.cleanup
            ):
                try:
                    logger.debug(f"🧼 Cleaning up tool: {tool_name}")
                    await tool_instance.cleanup()
                except Exception as e:
                    logger.error(
                        f"🚨 Error cleaning up tool '{tool_name}': {e}", exc_info=True
                    )
        logger.info(f"✨ Cleanup complete for agent '{self.agent.name}'.")


class ToolCallAgent(ReActAgent):
    """Base agent class for handling tool/function calls with enhanced abstraction"""

    name: str = "toolcall"
    description: str = "an agent that can execute tool calls."

    tool_call_context_helper: Optional[ToolCallContextHelper] = None

    @model_validator(mode="after")
    def initialize_helper(self) -> "ToolCallAgent":
        self.tool_call_context_helper = ToolCallContextHelper(self)
        return self

    async def think(self) -> bool:
        """Process current state and decide next actions using tools"""
        return await self.tool_call_context_helper.ask_tool()

    async def act(self) -> str:
        """Execute tool calls and handle their results"""
        results = await self.tool_call_context_helper.execute_tool()
        return "\n\n".join(results)

    async def execute_tool(self, command: ToolCall) -> str:
        """Execute a single tool call with robust error handling"""
        return await self.tool_call_context_helper.execute_tool_command(command)

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """Handle special tool execution and state changes"""
        return await self.tool_call_context_helper.handle_special_tool(
            name=name, result=result, **kwargs
        )

    @staticmethod
    def _should_finish_execution(**kwargs) -> bool:
        """Determine if tool execution should finish the agent"""
        return ToolCallContextHelper._should_finish_execution(**kwargs)

    def _is_special_tool(self, name: str) -> bool:
        """Check if tool name is in special tools list"""
        return self.tool_call_context_helper._is_special_tool(name)

    async def cleanup(self):
        """Clean up resources used by the agent's tools."""
        return await self.tool_call_context_helper.cleanup_tools()

    async def run(self, request: Optional[str] = None) -> str:
        """Run the agent with cleanup when done."""
        try:
            return await super().run(request)
        finally:
            await self.cleanup()
