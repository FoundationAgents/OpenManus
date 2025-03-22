import logging
import sys


logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stderr)])

import argparse
import asyncio
import atexit
import json
import os
from inspect import Parameter, Signature
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from fastapi import APIRouter, BackgroundTasks, FastAPI
from mcp.server.fastmcp import FastMCP
from sse_starlette.sse import EventSourceResponse

from app.logger import logger
from app.tool.base import BaseTool
from app.tool.bash import Bash
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.manus_agent_tool import ManusAgentTool
from app.tool.str_replace_editor import StrReplaceEditor
from app.tool.terminate import Terminate


class MCPServer:
    """MCP Server implementation with tool registration and management."""

    def __init__(self, name: str = "openmanus"):
        self.server = FastMCP(name)
        self.tools: Dict[str, BaseTool] = {}

        # Initialize standard tools
        self.tools["bash"] = Bash()
        self.tools["browser_use"] = BrowserUseTool()  # Use correct name to match class
        self.tools["str_replace_editor"] = StrReplaceEditor()  # Use correct name to match class
        self.tools["terminate"] = Terminate()

        # Add the high-level Manus agent tool
        self.tools["manus_agent"] = ManusAgentTool()

    def register_tool(self, tool: BaseTool, method_name: Optional[str] = None) -> None:
        """Register a tool with parameter validation and documentation."""
        tool_name = method_name or tool.name
        tool_param = tool.to_param()
        tool_function = tool_param["function"]

        # Define the async function to be registered
        async def tool_method(**kwargs):
            logger.info(f"Executing {tool_name}: {kwargs}")

            # Special handling for Manus agent with streaming support
            if tool_name == "manus_agent" and kwargs.get("streaming", False):
                logger.info(f"Using streaming mode for {tool_name}")
                
                # Detect if we're using SSE transport
                import os
                using_sse = os.environ.get("MCP_SERVER_TRANSPORT") == "sse"
                logger.info(f"Using SSE transport: {using_sse}")
                
                if using_sse:
                    # With SSE, we need to ensure the generator is consumed properly
                    # The key issue was that the generator was not being properly consumed
                    # and executed for the Manus agent
                    
                    # Manually trigger the execution of the manus agent in a way that will
                    # properly convert its output to a stream of events
                    logger.info("Creating wrapper for SSE streaming response")
                    
                    # Create a proxy generator that ensures the Manus agent is executed
                    import sys
                    
                    # Use async task to avoid potential deadlocks in generator execution
                    async def start_generator_task(tool_name, exec_kwargs, tools):
                        try:
                            logger.info(f"MCP task: Starting execution task for {tool_name}")
                            sys.stdout.flush()
                            sys.stderr.flush()
                            
                            # Get the Manus tool instance
                            manus_tool = tools[tool_name]
                            logger.info("MCP task: Executing tool with streaming=True")
                            sys.stdout.flush()
                            sys.stderr.flush()
                            
                            # Create and start the generator - forced execution
                            generator = await manus_tool.execute(streaming=True, **exec_kwargs)
                            logger.info("MCP task: Generator created successfully")
                            sys.stdout.flush()
                            sys.stderr.flush()
                            
                            return generator
                        except Exception as e:
                            import traceback
                            logger.error(f"MCP task: Error in generator task: {str(e)}\n{traceback.format_exc()}")
                            sys.stdout.flush()
                            sys.stderr.flush()
                            return None
                    
                    # Start a task to create and execute the generator                    
                    generator_task = None
                    
                    async def stream_response():
                        nonlocal generator_task
                        try:
                            # Force stdout/stderr flush throughout to ensure logs are visible
                            sys.stdout.flush()
                            sys.stderr.flush()
                            
                            # Send an initial event to confirm streaming has started
                            logger.info("MCP server: Starting streaming response")
                            sys.stdout.flush()
                            yield json.dumps({"status": "streaming_started", "message": "Stream started by MCP server"})
                            
                            # Get stripped kwargs (without streaming flag which we already processed)
                            exec_kwargs = {k: v for k, v in kwargs.items() if k != "streaming"}
                            logger.info(f"MCP server: Prepared exec kwargs: {exec_kwargs}")
                            sys.stdout.flush()
                            
                            # Start the generator task in a separate context to avoid deadlocks
                            logger.info("MCP server: Creating generator task")
                            sys.stdout.flush()
                            
                            # Create a new event loop to ensure isolation
                            generator_task = asyncio.create_task(
                                start_generator_task("manus_agent", exec_kwargs, self.tools)
                            )
                            
                            # Wait for the generator with timeout
                            try:
                                logger.info("MCP server: Waiting for generator task to complete")
                                sys.stdout.flush()
                                generator = await asyncio.wait_for(generator_task, timeout=10.0)
                                logger.info("MCP server: Generator task completed")
                                sys.stdout.flush()
                            except asyncio.TimeoutError:
                                logger.error("MCP server: Generator task timed out after 10 seconds")
                                sys.stdout.flush()
                                yield json.dumps({"status": "error", "error": "Generator creation timed out"})
                                return
                            except Exception as task_e:
                                import traceback
                                logger.error(f"MCP server: Error waiting for generator task: {str(task_e)}\n{traceback.format_exc()}")
                                sys.stdout.flush()
                                yield json.dumps({"status": "error", "error": f"Generator task error: {str(task_e)}"})
                                return
                            
                            # Check if generator is valid
                            if generator is None:
                                logger.error("MCP server: Generator task returned None")
                                sys.stdout.flush()
                                yield json.dumps({"status": "error", "error": "Failed to create generator"})
                                return
                            
                            # Consume the generator and yield each chunk
                            logger.info("MCP server: Starting to consume generator")
                            sys.stdout.flush()
                            chunk_count = 0
                            
                            # Wrap generator consumption in a separate task with timeout
                            async def process_chunk():
                                nonlocal chunk_count
                                try:
                                    async for chunk in generator:
                                        chunk_count += 1
                                        logger.info(f"MCP server: Received chunk {chunk_count}")
                                        sys.stdout.flush()
                                        yield chunk
                                        await asyncio.sleep(0.01)  # Small delay
                                except Exception as e:
                                    import traceback
                                    logger.error(f"MCP server: Error processing chunk: {str(e)}\n{traceback.format_exc()}")
                                    sys.stdout.flush()
                                    yield json.dumps({"status": "error", "error": f"Chunk processing error: {str(e)}"})
                            
                            # Use process_chunk as an async generator
                            async for chunk in process_chunk():
                                yield chunk
                                
                            logger.info(f"MCP server: Generator processing completed with {chunk_count} chunks")
                            sys.stdout.flush()
                            
                            # Send a final event to confirm completion
                            yield json.dumps({"status": "stream_complete", "message": "Stream completed by MCP server"})
                            logger.info("MCP server: Streaming completed")
                            sys.stdout.flush()
                            
                        except Exception as e:
                            import traceback
                            logger.error(f"MCP server: Error in stream_response: {str(e)}\n{traceback.format_exc()}")
                            sys.stdout.flush()
                            yield json.dumps({"status": "error", "error": f"Streaming error: {str(e)}"})

                    # Return a new generator that will be consumed by FastMCP's SSE transport
                    logger.info("Returning SSE stream response generator")
                    return stream_response()
                    
                else:
                    # For non-SSE transports, we need to collect all results
                    logger.info("Using non-SSE mode, collecting all results")
                    
                    # Get stripped kwargs (without streaming flag which we already processed)
                    exec_kwargs = {k: v for k, v in kwargs.items() if k != "streaming"}
                    
                    # Get the Manus tool instance
                    manus_tool = self.tools["manus_agent"]
                    
                    # Execute with streaming and collect results
                    results = []
                    try:
                        # Ensure that we get a proper generator
                        generator = await manus_tool.execute(streaming=True, **exec_kwargs)
                        
                        # Collect all results
                        logger.info("Collecting all results from generator")
                        async for chunk in generator:
                            logger.info(f"Collected chunk: {chunk[:50]}..." if len(chunk) > 50 else f"Collected chunk: {chunk}")
                            results.append(chunk)
                            
                        # Return all collected results as JSON array
                        result_json = json.dumps(results)
                        logger.info(f"Returning collected results: {result_json[:100]}..." if len(result_json) > 100 else f"Returning collected results: {result_json}")
                        return result_json
                    except Exception as e:
                        logger.error(f"Error collecting results: {e}")
                        return json.dumps({"status": "error", "error": str(e)})

            # Standard execution for all other tools
            result = await tool.execute(**kwargs)

            logger.info(f"Result of {tool_name}: {result}")

            # Handle different types of results
            if hasattr(result, "model_dump"):
                return json.dumps(result.model_dump())
            elif isinstance(result, dict):
                return json.dumps(result)
            return result

        # Set method metadata
        tool_method.__name__ = tool_name
        tool_method.__doc__ = self._build_docstring(tool_function)
        tool_method.__signature__ = self._build_signature(tool_function)

        # Store parameter schema (important for tools that access it programmatically)
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])
        tool_method._parameter_schema = {
            param_name: {
                "description": param_details.get("description", ""),
                "type": param_details.get("type", "any"),
                "required": param_name in required_params,
            }
            for param_name, param_details in param_props.items()
        }

        # Register with server
        self.server.tool()(tool_method)
        logger.info(f"Registered tool: {tool_name}")

    def _build_docstring(self, tool_function: dict) -> str:
        """Build a formatted docstring from tool function metadata."""
        description = tool_function.get("description", "")
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])

        # Build docstring (match original format)
        docstring = description
        if param_props:
            docstring += "\n\nParameters:\n"
            for param_name, param_details in param_props.items():
                required_str = (
                    "(required)" if param_name in required_params else "(optional)"
                )
                param_type = param_details.get("type", "any")
                param_desc = param_details.get("description", "")
                docstring += (
                    f"    {param_name} ({param_type}) {required_str}: {param_desc}\n"
                )

        return docstring

    def _build_signature(self, tool_function: dict) -> Signature:
        """Build a function signature from tool function metadata."""
        param_props = tool_function.get("parameters", {}).get("properties", {})
        required_params = tool_function.get("parameters", {}).get("required", [])

        parameters = []

        # Follow original type mapping
        for param_name, param_details in param_props.items():
            param_type = param_details.get("type", "")
            default = Parameter.empty if param_name in required_params else None

            # Map JSON Schema types to Python types (same as original)
            annotation = Any
            if param_type == "string":
                annotation = str
            elif param_type == "integer":
                annotation = int
            elif param_type == "number":
                annotation = float
            elif param_type == "boolean":
                annotation = bool
            elif param_type == "object":
                annotation = dict
            elif param_type == "array":
                annotation = list

            # Create parameter with same structure as original
            param = Parameter(
                name=param_name,
                kind=Parameter.KEYWORD_ONLY,
                default=default,
                annotation=annotation,
            )
            parameters.append(param)

        return Signature(parameters=parameters)

    async def cleanup(self) -> None:
        """Clean up server resources."""
        logger.info("Cleaning up resources")
        # Follow original cleanup logic - only clean browser tool
        if "browser" in self.tools and hasattr(self.tools["browser"], "cleanup"):
            await self.tools["browser"].cleanup()

    def register_all_tools(self) -> None:
        """Register all tools with the server."""
        for tool in self.tools.values():
            self.register_tool(tool)

    # Removed direct streaming endpoint implementation as it's no longer needed

    def run(self, transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000) -> None:
        """Run the MCP server.

        Args:
            transport: Transport protocol to use ("stdio" or "sse")
            host: Host to bind the HTTP/SSE server to (only used with sse transport)
            port: Port to bind the HTTP/SSE server to (only used with sse transport)
        """
        # Register all tools
        self.register_all_tools()

        # Register cleanup function (match original behavior)
        atexit.register(lambda: asyncio.run(self.cleanup()))

        # Set transport type in environment for tool methods to check
        os.environ["MCP_SERVER_TRANSPORT"] = transport
        
        if transport == "sse":
            # With SSE transport, we're using HTTP server with Server-Sent Events
            logger.info(f"Starting OpenManus HTTP server with SSE transport on {host}:{port}")
            # Set bind host and port for SSE transport
            os.environ["MCP_SERVER_HOST"] = host
            os.environ["MCP_SERVER_PORT"] = str(port)
            
            # Use sse transport which will start an HTTP server
            self.server.run(transport=transport)
        else:
            # Standard stdio transport
            logger.info(f"Starting OpenManus server ({transport} mode)")
            self.server.run(transport=transport)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="OpenManus MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Communication method: stdio or sse (default: stdio)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the HTTP/SSE server to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the HTTP/SSE server to (default: 8000)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Create and run server with all provided arguments
    server = MCPServer()
    server.run(transport=args.transport, host=args.host, port=args.port)
