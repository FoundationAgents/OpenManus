"""
Example client for using the Manus agent through MCP.

This example demonstrates how to use the high-level Manus agent through the MCP client,
both with and without streaming responses.
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

from mcp.client import MCPClient
from mcp.client import SSETransport


async def run_manus_agent_simple(prompt: str) -> None:
    """Run the Manus agent with a simple (non-streaming) request."""
    print(f"\n=== Running Manus Agent (Simple Mode) ===")
    print(f"Prompt: {prompt}")

    # Create client with stdio transport (for local testing)
    client = MCPClient()
    await client.connect()

    try:
        # Call the high-level Manus agent
        result = await client.manus_agent(prompt=prompt, streaming=False)

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


async def run_manus_agent_streaming(prompt: str, server_url: Optional[str] = None) -> None:
    """Run the Manus agent with streaming responses over SSE."""
    print(f"\n=== Running Manus Agent (Streaming Mode) ===")
    print(f"Prompt: {prompt}")

    # Create client with SSE transport for streaming
    if server_url:
        # Connect to a remote server
        client = MCPClient(transport=SSETransport(server_url))
    else:
        # Connect to localhost with default port
        client = MCPClient(transport=SSETransport("http://localhost:8000"))

    await client.connect()

    try:
        # Call the agent with streaming enabled
        async for event in client.manus_agent(prompt=prompt, streaming=True):
            try:
                # Parse and display each event
                event_data = json.loads(event)
                status = event_data.get("status", "unknown")

                if status == "started":
                    print(f"\n🚀 Agent started processing prompt: {event_data.get('prompt')}")

                elif status == "thinking":
                    step = event_data.get("step", 0)
                    should_act = event_data.get("should_act", False)
                    print(f"\n🤔 Step {step}: Agent thinking...")
                    print(f"   Will act: {'Yes' if should_act else 'No'}")

                elif status == "acting":
                    step = event_data.get("step", 0)
                    result = event_data.get("result", "")
                    print(f"\n🧠 Step {step}: Agent acting...")
                    print(f"   Result: {result[:100]}{'...' if len(result) > 100 else ''}")

                elif status == "complete":
                    print(f"\n✅ Agent completed in {event_data.get('total_steps', 0)} steps")
                    messages = event_data.get("messages", [])
                    if messages:
                        print(f"   Final response: {messages[-1].get('content', '')[:150]}...")

                elif status == "error":
                    print(f"\n❌ Error: {event_data.get('error', 'Unknown error')}")

                else:
                    print(f"\nReceived event: {json.dumps(event_data, indent=2)}")

            except json.JSONDecodeError:
                print(f"Received non-JSON event: {event}")

    finally:
        await client.close()


async def main() -> None:
    """Run the example."""
    # Get prompt from command line or use default
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Tell me a joke about AI agents"

    # Choose which example to run
    mode = "streaming"  # or "simple"

    if mode == "simple":
        await run_manus_agent_simple(prompt)
    else:
        # For streaming mode, you need to run the MCP server with SSE transport:
        # python run_mcp_server.py --transport sse --host 127.0.0.1 --port 8000
        await run_manus_agent_streaming(prompt)


if __name__ == "__main__":
    asyncio.run(main())
