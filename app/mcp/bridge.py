import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union

from app.config import config
from app.logger import logger
from app.tool.base import BaseTool, ToolResult
from app.tool.mcp import MCPClients


class ModelCapabilityDetector:
    """Detects model capabilities for tool calling support."""

    @staticmethod
    def supports_tools(model_config: Dict[str, Any]) -> bool:
        """Check if the model supports native tool calling."""
        # Check explicit supports_tools flag
        if "supports_tools" in model_config:
            return bool(model_config["supports_tools"])

        # Check API type - some types don't support tools
        api_type = model_config.get("api_type", "").lower()
        unsupported_types = ["ollama", "custom", "text-only"]
        if api_type in unsupported_types:
            return False

        # Check provider-specific logic
        base_url = model_config.get("base_url", "").lower()
        if "ollama" in base_url or "llama" in base_url:
            return False

        # Default to assuming tool support
        return True

    @staticmethod
    def should_use_fallback(model_config: Dict[str, Any]) -> bool:
        """Determine if fallback should be used based on model capabilities."""
        # Check if fallback is enabled in config
        mcp_config = getattr(config, 'mcp_config', None)
        if not mcp_config:
            return False

        enable_fallback = getattr(mcp_config, 'enable_fallback', True)
        if not enable_fallback:
            return False

        # Check model capabilities
        return not ModelCapabilityDetector.supports_tools(model_config)


class MCPBridge:
    """Bridge for tool execution with automatic fallback to MCP stdio clients."""

    def __init__(self):
        self.mcp_clients = MCPClients()
        self.capability_detector = ModelCapabilityDetector()
        self.fallback_active = False
        self.native_tools: Dict[str, BaseTool] = {}
        self.mcp_tools: Dict[str, Any] = {}
        self.connection_pools: Dict[str, List] = {}

    async def initialize(self, model_config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the bridge based on model capabilities."""
        if not model_config:
            # Use default model config
            llm_configs = config.llm
            model_config = llm_configs.get("default", {})
            if isinstance(model_config, dict):
                model_config = model_config.dict() if hasattr(model_config, 'dict') else model_config

        # Determine if we need fallback
        should_fallback = self.capability_detector.should_use_fallback(model_config)
        
        if should_fallback:
            await self._initialize_fallback()
        else:
            await self._initialize_native()

    async def _initialize_native(self) -> None:
        """Initialize for native tool calling."""
        logger.info("Initializing MCP Bridge for native tool calling")
        self.fallback_active = False
        
        # Load native tools from configuration
        await self._load_native_tools()

    async def _initialize_fallback(self) -> None:
        """Initialize for MCP stdio fallback."""
        logger.info("Initializing MCP Bridge for stdio fallback")
        self.fallback_active = True
        
        # Start internal MCP servers
        await self._start_internal_servers()
        
        # Connect to internal servers via stdio
        await self._connect_internal_servers()

    async def _load_native_tools(self) -> None:
        """Load native tools for direct execution."""
        from app.tool.bash import Bash
        from app.tool.browser_use_tool import BrowserUseTool
        from app.tool.str_replace_editor import StrReplaceEditor
        from app.tool.terminate import Terminate

        self.native_tools = {
            "bash": Bash(),
            "browser": BrowserUseTool(),
            "editor": StrReplaceEditor(),
            "terminate": Terminate(),
        }

    async def _start_internal_servers(self) -> None:
        """Start internal MCP servers for fallback mode."""
        mcp_config = getattr(config, 'mcp_config', None)
        if not mcp_config:
            return

        internal_servers = getattr(mcp_config, 'internal_servers', {})
        
        for server_name, server_config in internal_servers.items():
            if server_config.get("enabled", True) and server_config.get("autoStart", True):
                await self._start_server_process(server_name, server_config)

    async def _start_server_process(self, server_name: str, server_config: Dict) -> None:
        """Start a server process for the given configuration."""
        import subprocess
        
        command = server_config.get("command")
        args = server_config.get("args", [])
        
        if not command:
            logger.warning(f"No command specified for server {server_name}")
            return

        try:
            # Start the server process
            process = subprocess.Popen(
                [command] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
            )
            
            # Store process reference for cleanup
            if not hasattr(self, '_server_processes'):
                self._server_processes = {}
            self._server_processes[server_name] = process
            
            logger.info(f"Started MCP server process: {server_name}")
            
            # Give the server a moment to start up
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Failed to start server {server_name}: {e}")

    async def _connect_internal_servers(self) -> None:
        """Connect to internal MCP servers."""
        mcp_config = getattr(config, 'mcp_config', None)
        if not mcp_config:
            return

        internal_servers = getattr(mcp_config, 'internal_servers', {})
        
        for server_name, server_config in internal_servers.items():
            if server_config.get("enabled", True):
                await self._connect_to_server(server_name, server_config)

    async def _connect_to_server(self, server_name: str, server_config: Dict) -> None:
        """Connect to a specific MCP server."""
        connection_type = server_config.get("type", "stdio")
        
        if connection_type == "stdio":
            command = server_config.get("command")
            args = server_config.get("args", [])
            
            if command:
                try:
                    await self.mcp_clients.connect_stdio(
                        command=command,
                        args=args,
                        server_id=server_name
                    )
                    logger.info(f"Connected to MCP server: {server_name}")
                except Exception as e:
                    logger.error(f"Failed to connect to server {server_name}: {e}")
        
        elif connection_type == "sse":
            url = server_config.get("url")
            if url:
                try:
                    await self.mcp_clients.connect_sse(
                        server_url=url,
                        server_id=server_name
                    )
                    logger.info(f"Connected to MCP server via SSE: {server_name}")
                except Exception as e:
                    logger.error(f"Failed to connect to server {server_name}: {e}")

    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool using the appropriate method."""
        if self.fallback_active:
            return await self._execute_mcp_tool(tool_name, **kwargs)
        else:
            return await self._execute_native_tool(tool_name, **kwargs)

    async def _execute_native_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool natively."""
        tool = self.native_tools.get(tool_name)
        if not tool:
            return ToolResult(error=f"Unknown tool: {tool_name}")

        try:
            logger.info(f"Executing native tool: {tool_name}")
            result = await tool.execute(**kwargs)
            logger.info(f"Result of native tool {tool_name}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error executing native tool {tool_name}: {e}")
            return ToolResult(error=f"Error executing tool {tool_name}: {str(e)}")

    async def _execute_mcp_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool via MCP fallback."""
        # Find the tool in MCP clients
        mcp_tool = None
        
        # Try direct match first
        if tool_name in self.mcp_clients.tool_map:
            mcp_tool = self.mcp_clients.tool_map[tool_name]
        else:
            # Try to find with namespace prefix
            for tool_key, tool in self.mcp_clients.tool_map.items():
                if tool_key.endswith(f"_{tool_name}") or tool_name in tool_key:
                    mcp_tool = tool
                    break

        if not mcp_tool:
            return ToolResult(error=f"Tool not found in MCP: {tool_name}")

        try:
            logger.info(f"Executing MCP tool: {tool_name}")
            result = await mcp_tool.execute(**kwargs)
            logger.info(f"Result of MCP tool {tool_name}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error executing MCP tool {tool_name}: {e}")
            return ToolResult(error=f"Error executing MCP tool {tool_name}: {str(e)}")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        if self.fallback_active:
            # List MCP tools
            response = await self.mcp_clients.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                }
                for tool in response.tools
            ]
        else:
            # List native tools
            return [
                {
                    "name": name,
                    "description": tool.description,
                    "parameters": tool.to_param()["function"].get("parameters", {}),
                }
                for name, tool in self.native_tools.items()
            ]

    def get_tool_names(self) -> List[str]:
        """Get list of available tool names."""
        if self.fallback_active:
            return list(self.mcp_clients.tool_map.keys())
        else:
            return list(self.native_tools.keys())

    def is_fallback_active(self) -> bool:
        """Check if fallback mode is active."""
        return self.fallback_active

    async def cleanup(self) -> None:
        """Clean up bridge resources."""
        logger.info("Cleaning up MCP Bridge")
        
        # Disconnect MCP clients
        if self.mcp_clients.sessions:
            await self.mcp_clients.disconnect()
        
        # Terminate server processes
        if hasattr(self, '_server_processes'):
            for server_name, process in self._server_processes.items():
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    logger.info(f"Terminated server process: {server_name}")
                except Exception as e:
                    logger.error(f"Error terminating server {server_name}: {e}")
                    try:
                        process.kill()
                        process.wait(timeout=2)
                    except:
                        pass

    def get_status(self) -> Dict[str, Any]:
        """Get bridge status information."""
        return {
            "fallback_active": self.fallback_active,
            "native_tools_count": len(self.native_tools),
            "mcp_tools_count": len(self.mcp_clients.tool_map),
            "mcp_connections": len(self.mcp_clients.sessions),
            "tool_names": self.get_tool_names(),
        }