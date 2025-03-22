"""
Example client for using the Manus agent through MCP.

This example demonstrates how to use the high-level Manus agent through the MCP client,
both with and without streaming responses.
"""

import argparse
import asyncio
import json
import sys
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from mcp.client.session import Session as MCPSession
from mcp.client.stdio import StdioTransport


async def run_manus_agent_simple(prompt: str) -> None:
    """Run the Manus agent with a simple (non-streaming) request."""
    print(f"\n=== Running Manus Agent (Simple Mode) ===")
    print(f"Prompt: {prompt}")

    # Create client with stdio transport (for local testing)
    client = MCPSession(transport=StdioTransport())
    await client.connect()

    try:
        # Call the high-level Manus agent
        result = await client.call("manus_agent", prompt=prompt, streaming=False)

        # Parse and display the result
        try:
            result_json = json.loads(result)
            print("\nResult:")
            print(json.dumps(result_json, indent=2))
        except:
            # If not JSON, display as string
            print(f"\nResult: {result}")

    finally:
        await client.close()


# Direct streaming endpoint no longer needed, using standard MCP streaming

class MCPClient:
    """Simple client for the MCP server that supports streaming responses."""

    def __init__(self, transport: str = "stdio", server_url: Optional[str] = None):
        self.transport = transport
        self.server_url = server_url
        self.session = None

    async def connect(self):
        """Connect to the MCP server."""
        if self.transport == "stdio":
            self.session = MCPSession(transport=StdioTransport())
        elif self.transport == "sse":
            if not self.server_url:
                raise ValueError("server_url is required for SSE transport")
            # Import here to avoid introducing dependency if not needed
            from mcp.client.sse import SSETransport
            self.session = MCPSession(transport=SSETransport(server_url=self.server_url))
        else:
            raise ValueError(f"Unsupported transport: {self.transport}")

        await self.session.connect()

    async def call(self, method: str, **kwargs):
        """Call a method on the MCP server."""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        return await self.session.call(method, **kwargs)

    async def stream(self, method: str, **kwargs):
        """Stream a method call to the MCP server."""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        return await self.session.stream(method, **kwargs)

    async def close(self):
        """Close the connection to the MCP server."""
        if self.session:
            await self.session.close()
            self.session = None

async def run_manus_agent_streaming(prompt: str, server_url: Optional[str] = None) -> None:
    """Run the Manus agent with streaming responses."""
    print(f"\n=== Running Manus Agent (Streaming Mode) ===")
    print(f"Prompt: {prompt}")
    
    # Create client with SSE transport
    client = MCPClient(transport="sse", server_url=server_url)
    await client.connect()
    
    try:
        # Use streaming API to get a generator of events
        print("Requesting streaming response from Manus agent...")
        generator = await client.stream("manus_agent", prompt=prompt, streaming=True)
        
        print("Streaming response started:")
        print("-" * 50)
        
        # Process the streaming events
        counter = 0
        async for event in generator:
            counter += 1
            try:
                # Parse and display each event
                event_data = json.loads(event)
                status = event_data.get("status", "unknown")
                
                if status == "streaming_started":
                    print(f"🚀 Stream started: {event_data.get('message', '')}")
                    
                elif status == "stream_complete":
                    print(f"✅ Stream completed: {event_data.get('message', '')}")
                    
                elif status == "thinking":
                    step = event_data.get("step", 0)
                    content = event_data.get("content", "No content")
                    print(f"🤔 Thinking (Step {step}): {content}")
                    
                elif status == "acting":
                    step = event_data.get("step", 0)
                    action = event_data.get("action", "No action")
                    print(f"🧠 Acting (Step {step}): {action}")
                    
                elif status == "complete":
                    print(f"✅ Agent completed successfully")
                    content = event_data.get("content", "No content")
                    print(f"Final response: {content[:150]}{'...' if len(content) > 150 else ''}")
                    
                elif status == "error":
                    print(f"❌ Error: {event_data.get('error', 'Unknown error')}")
                    
                else:
                    # Just print the raw event for unknown statuses
                    print(f"Event {counter}: {event}")
                    
            except json.JSONDecodeError:
                # If not JSON, print as raw string
                print(f"Raw event {counter}: {event}")
                
        print("-" * 50)
        print(f"Received {counter} events from Manus agent")
        
    except Exception as e:
        print(f"Error in streaming: {e}")
        
    finally:
        await client.close()

async def main() -> None:
    """Run the example."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Manus Agent MCP Client Example")
    parser.add_argument(
        "prompt", 
        nargs="+",
        help="Prompt for the Manus agent"
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["simple", "streaming"],
        default="streaming",
        help="Mode to run the client in (simple=non-streaming, streaming=with streaming)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host of the MCP server (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port of the MCP server (default: 8000)"
    )

    args = parser.parse_args()
    server_url = f"http://{args.host}:{args.port}"

    print(f"Using prompt: {args.prompt}")
    print(f"Server URL: {server_url}")

    if args.mode == "simple":
        print("Running in simple mode (non-streaming)")
        await run_manus_agent_simple(args.prompt)
    else:
        print("Running in streaming mode")
        print("NOTE: Make sure the server is running with SSE transport:")
        print(f"      python run_mcp_server.py --transport sse --host {args.host} --port {args.port}")
        await run_manus_agent_streaming(args.prompt, server_url)


if __name__ == "__main__":
    asyncio.run(main())
