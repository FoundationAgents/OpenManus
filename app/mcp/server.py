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

                    # Use a radically different approach with a thread and queue to force execution
                    import sys
                    import threading
                    import queue
                    import time

                    # Create a queue for communication between the thread and the generator
                    result_queue = queue.Queue()
                    execution_complete = threading.Event()

                    # Using a thread to completely bypass any potential deadlocks or asyncio issues
                    def run_manus_agent_in_thread(tool_name, exec_kwargs, tools):
                        try:
                            print(f"THREAD: Starting execution thread for {tool_name}")
                            sys.stdout.flush()

                            # Get the Manus tool instance
                            manus_tool = tools[tool_name]
                            print("THREAD: Got Manus tool instance")

                            # Put initial status in queue
                            result_queue.put(json.dumps({
                                "status": "thread_started",
                                "message": "Thread started for Manus agent execution"
                            }))

                            # Run the Manus agent directly in the thread instead of using streaming
                            # This is a blocking call, but it's in a separate thread so it won't block the server
                            print(f"THREAD: About to execute Manus agent with: {exec_kwargs}")
                            sys.stdout.flush()

                            # Import here to avoid circular dependencies
                            from app.agent.manus import Manus, AgentState, Message

                            # Create and run the agent directly
                            try:
                                agent = Manus()
                                if exec_kwargs.get("max_steps") is not None:
                                    agent.max_steps = exec_kwargs["max_steps"]

                                prompt = exec_kwargs["prompt"]
                                print(f"THREAD: Created Manus agent with prompt: {prompt[:50]}...")
                                sys.stdout.flush()

                                # Initialize the agent
                                agent.messages = [Message.user_message(prompt)]
                                agent.current_step = 0
                                agent.state = AgentState.RUNNING

                                # Report initial status
                                result_queue.put(json.dumps({
                                    "status": "started",
                                    "step": 0,
                                    "message": f"Starting to process: '{prompt[:50]}{'...' if len(prompt) > 50 else ''}'"
                                }))

                                # Run steps until completion or max steps reached
                                actions_summary = []
                                while agent.state == AgentState.RUNNING and agent.current_step < agent.max_steps:
                                    agent.current_step += 1
                                    print(f"THREAD: Running step {agent.current_step}")
                                    sys.stdout.flush()

                                    # Run think step synchronously
                                    try:
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                        should_act = loop.run_until_complete(agent.think())

                                        # Get thinking content
                                        last_messages = [msg for msg in agent.memory.messages[-2:]
                                                       if hasattr(msg, "role") and hasattr(msg, "content")]
                                        thinking_content = last_messages[-1].content if last_messages else "No content available"
                                        thinking_summary = thinking_content[:150] + "..." if len(thinking_content) > 150 else thinking_content

                                        # Put thinking result in queue
                                        result_queue.put(json.dumps({
                                            "status": "thinking",
                                            "step": agent.current_step,
                                            "content": thinking_summary
                                        }))

                                        # If should act, perform the action
                                        if should_act:
                                            print(f"THREAD: Agent will act on step {agent.current_step}")
                                            sys.stdout.flush()
                                            result = loop.run_until_complete(agent.act())
                                            result_str = str(result)

                                            # Create a summary
                                            summary = result_str[:150] + "..." if len(result_str) > 150 else result_str
                                            actions_summary.append(f"Step {agent.current_step}: {summary}")

                                            # Put action result in queue
                                            result_queue.put(json.dumps({
                                                "status": "acting",
                                                "step": agent.current_step,
                                                "action": summary
                                            }))

                                        loop.close()
                                    except Exception as e:
                                        print(f"THREAD: Error in agent execution: {str(e)}")
                                        sys.stdout.flush()
                                        import traceback
                                        result_queue.put(json.dumps({
                                            "status": "error",
                                            "step": agent.current_step,
                                            "error": f"Error: {str(e)}",
                                            "traceback": traceback.format_exc()
                                        }))
                                        agent.state = AgentState.FINISHED

                                    # Small delay to avoid overwhelming the queue
                                    time.sleep(0.1)

                                    # Break if agent is finished
                                    if agent.state == AgentState.FINISHED:
                                        print("THREAD: Agent finished")
                                        sys.stdout.flush()
                                        break

                                # Get final result
                                last_messages = [msg for msg in agent.memory.messages[-3:]
                                               if hasattr(msg, "role") and hasattr(msg, "content")]
                                final_content = last_messages[-1].content if last_messages else "No final content available"
                                short_content = final_content[:300] + "..." if len(final_content) > 300 else final_content

                                # Put final result in queue
                                result_queue.put(json.dumps({
                                    "status": "complete",
                                    "content": short_content,
                                    "steps_summary": actions_summary[-3:] if len(actions_summary) > 3 else actions_summary,
                                    "total_steps": agent.current_step
                                }))
                                print(f"THREAD: Execution completed with {agent.current_step} steps")
                                sys.stdout.flush()

                            except Exception as agent_e:
                                print(f"THREAD: Error creating or running agent: {str(agent_e)}")
                                sys.stdout.flush()
                                import traceback
                                result_queue.put(json.dumps({
                                    "status": "error",
                                    "error": f"Agent error: {str(agent_e)}",
                                    "traceback": traceback.format_exc()
                                }))
                        except Exception as thread_e:
                            print(f"THREAD: Unhandled error in thread: {str(thread_e)}")
                            sys.stdout.flush()
                            import traceback
                            result_queue.put(json.dumps({
                                "status": "error",
                                "error": f"Thread error: {str(thread_e)}",
                                "traceback": traceback.format_exc()
                            }))
                        finally:
                            # Mark execution as complete
                            execution_complete.set()
                            print("THREAD: Execution marked as complete")
                            sys.stdout.flush()

                    # Start the thread
                    exec_kwargs = {k: v for k, v in kwargs.items() if k != "streaming"}
                    thread = threading.Thread(
                        target=run_manus_agent_in_thread,
                        args=("manus_agent", exec_kwargs, self.tools),
                        daemon=True
                    )
                    thread.start()
                    logger.info(f"Started Manus agent execution in thread {thread.ident}")

                    # Create a simple generator that consumes from the queue
                    async def stream_response():
                        try:
                            # Initial message
                            logger.info("MCP server: Starting streaming response from thread queue")
                            yield json.dumps({"status": "streaming_started", "message": "Stream started by MCP server"})

                            # Process items from the queue until thread signals completion
                            timeout_counter = 0
                            max_timeout = 300  # 30 seconds max wait (100ms * 300)

                            while not execution_complete.is_set() or not result_queue.empty():
                                try:
                                    # Try to get an item from the queue with a small timeout
                                    item = result_queue.get(block=True, timeout=0.1)
                                    logger.info(f"Got item from queue: {item[:50]}..." if len(item) > 50 else f"Got item from queue: {item}")
                                    yield item
                                    timeout_counter = 0  # Reset timeout counter on successful get
                                except queue.Empty:
                                    # Queue is empty but thread might still be running
                                    await asyncio.sleep(0.1)  # Small sleep to avoid CPU spinning
                                    timeout_counter += 1
                                    if timeout_counter >= max_timeout and not execution_complete.is_set():
                                        logger.error("Queue processing timed out after 30 seconds without new items")
                                        yield json.dumps({"status": "error", "error": "Execution timed out"})
                                        break
                                    continue

                            # Final completion message
                            yield json.dumps({"status": "stream_complete", "message": "Stream completed by MCP server"})
                            logger.info("MCP server: Queue processing completed")

                        except Exception as e:
                            import traceback
                            logger.error(f"MCP server: Error in stream_response: {str(e)}\n{traceback.format_exc()}")
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
