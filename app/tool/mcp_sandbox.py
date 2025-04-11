import asyncio
import time
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional, Tuple

import docker
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from app.container.manager import ContainerManager
from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.tool_collection import ToolCollection

container_manager_singleton = ContainerManager()


class MCPSandboxClientTool(BaseTool):
    """Represents a tool proxy that can be called on the MCP server from the client side, running in a sandbox."""

    session: Optional[ClientSession] = None
    client_id: str = ""

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool by making a remote call to the MCP server."""
        if not self.session:
            return ToolResult(error="Not connected to MCP server")

        try:
            # Remove client_id prefix from tool name before calling server
            server_tool_name = (
                self.name[len(self.client_id) + 1 :] if self.client_id else self.name
            )
            result = await self.session.call_tool(server_tool_name, kwargs)
            content_str = ", ".join(
                item.text for item in result.content if isinstance(item, TextContent)
            )
            return ToolResult(output=content_str or "No output returned.")
        except Exception as e:
            return ToolResult(error=f"Error executing tool: {str(e)}")


class MCPSandboxClients(ToolCollection):
    """
    A collection of tools that connects to an MCP server within a container and manages available tools.
    """

    session: Optional[ClientSession] = None
    exit_stack: AsyncExitStack = None
    description: str = "MCP client tools running in container for server interaction"
    client_id: str = ""

    # Container management
    container_name: Optional[str] = None

    def __init__(self, client_id: str):
        super().__init__()  # Initialize with empty tools list
        self.name = f"mcp-{client_id}"  # Keep name for backward compatibility
        self.client_id = client_id
        self.exit_stack = AsyncExitStack()

    def _get_command_type(self, command: str) -> str:
        """Determine the type of command (uvx/npx/docker)."""
        if command.startswith("uvx"):
            return "uvx"
        elif command.startswith("npx"):
            return "npx"
        elif command.startswith("docker"):
            return "docker"
        else:
            raise ValueError(f"Unsupported command type: {command}")

    def _convert_to_docker_command(
        self, parameters: StdioServerParameters
    ) -> StdioServerParameters:
        """Convert any command to unified docker command format and return StdioServerParameters.

        Args:
            command: The original command to execute
            args: List of command arguments

        Returns:
            StdioServerParameters: Parameters for stdio transport
        """
        command_type = self._get_command_type(parameters.command)

        # Build a unified docker command
        docker_command = "docker"
        docker_args = ["run", "--rm", "-i"]

        # Add network configuration
        docker_args.extend(["--network", "openmanus-container-network"])

        # Basic environment variables
        env_vars = {
            "PYTHONUNBUFFERED": "1",  # Ensure Python output is not buffered
            "TERM": "dumb",  # Use dumb terminal type
            "PS1": "$ ",  # Set a simple prompt
            "PROMPT_COMMAND": "",  # Disable prompt command
        }

        # Set different images and volumes based on command type
        # uvx
        if command_type == "uvx":
            docker_args.extend(
                [
                    "openmanus-sandbox-uvenv:latest",
                    "bash",
                    "-c",
                ]
            )
            # Directly use pip to install and run packages
            start_cmd = f"uvenv run {' '.join(parameters.args)}"
            docker_args.append(start_cmd)
        # npx
        elif command_type == "npx":
            docker_args.extend(
                [
                    "-v",
                    "/tmp/npm_cache:/tmp/npm_cache:rw",
                    "node:18-slim",
                    "bash",
                    "-c",
                ]
            )
            # Keep the original command and arguments unchanged
            start_cmd = f"{parameters.command} {' '.join(parameters.args)}"
            docker_args.append(start_cmd)
        elif command_type == "docker":
            # If it's a docker command, use the original parameters directly
            return StdioServerParameters(
                command=parameters.command, args=parameters.args, env=env_vars
            )

        return StdioServerParameters(
            command=docker_command, args=docker_args, env=env_vars
        )

    async def connect_stdio(self, command: str, args: List[str]) -> None:
        """Connect to an MCP server using stdio transport within a container."""
        if not command:
            raise ValueError("Server command is required.")
        if self.session:
            await self.disconnect()

        # Convert to unified docker command parameters
        server_params = self._convert_to_docker_command(
            StdioServerParameters(command=command, args=args)
        )
        full_command = f"{server_params.command} {' '.join(server_params.args)}"
        logger.info(f"Starting MCP server with docker command args : {full_command}")

        # Use stdio_client provided by mcp library
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        logger.info("Client session created")

        # Directly call the initialization method
        await self._initialize_and_list_tools()

    async def connect_sse(self, server_url: str) -> None:
        """Connect to an MCP server using SSE transport."""
        if not server_url:
            raise ValueError("Server URL is required.")
        if self.session:
            await self.disconnect()

        try:
            # Use AsyncExitStack to manage async context
            streams = await self.exit_stack.enter_async_context(
                sse_client(url=server_url)
            )
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(*streams)
            )
            logger.info("Client session created")

            # Initialize session
            logger.info("Initializing MCP session...")
            try:
                await self.session.initialize()
                logger.info("MCP session initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize MCP session: {e}")
                await self.disconnect()
                raise RuntimeError(f"Failed to initialize MCP session: {e}")

            # Fetch available tools from MCP server
            try:
                await self._initialize_and_list_tools()
            except Exception as e:
                logger.error(f"Failed to list tools: {e}")
                await self.disconnect()
                raise RuntimeError(f"Failed to list tools: {e}")

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            await self.disconnect()
            raise RuntimeError(f"Failed to connect to MCP server: {e}")

    async def _initialize_and_list_tools(self) -> None:
        """Initialize session and populate tool map."""
        if not self.session:
            raise RuntimeError("Session not initialized.")

        logger.info("Initializing MCP session...")
        try:
            await self.session.initialize()
            logger.info("MCP session initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MCP session: {e}")
            await self.disconnect()
            raise RuntimeError(f"Failed to initialize MCP session: {e}")

        logger.info("Fetching available tools from MCP server...")
        try:
            response = await self.session.list_tools()
            logger.info(f"Received tool list response: {response}")

            # Clear existing tools
            self.tools = tuple()
            self.tool_map = {}

            # Add client_id prefix to tool name
            for tool in response.tools:
                prefixed_name = f"{self.client_id}-{tool.name}"
                server_tool = MCPSandboxClientTool(
                    name=prefixed_name,
                    description=tool.description,
                    parameters=tool.inputSchema,
                    session=self.session,
                    client_id=self.client_id,
                )
                self.tool_map[prefixed_name] = server_tool
                logger.info(f"Added tool: {prefixed_name}")

            self.tools = tuple(self.tool_map.values())
            logger.info(
                f"Connected to server with tools (via container): {[tool.name for tool in response.tools]}"
            )
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            await self.disconnect()
            raise RuntimeError(f"Failed to list tools: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the MCP server and clean up resources."""
        if self.session and self.exit_stack:
            await self.exit_stack.aclose()
            self.session = None
            self.tools = tuple()
            self.tool_map = {}

            # Clean up container if needed
            if self.container_name:
                await container_manager_singleton.stop_container(self.container_name)
                self.container_name = None

            logger.info(
                f"Disconnected from MCP server and cleaned up container for client {self.client_id}"
            )
