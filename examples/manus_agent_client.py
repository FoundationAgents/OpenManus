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


async def stream_from_direct_endpoint(prompt: str, server_url: Optional[str] = None) -> AsyncGenerator[str, None]:
    """Stream directly from the dedicated streaming endpoint."""
    base_url = server_url or "http://localhost:8000"
    url = f"{base_url}/direct-stream/manus?prompt={prompt}"
    
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream('POST', url, timeout=300.0) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield json.dumps({"status": "error", "error": f"Server returned {response.status_code}: {error_text.decode('utf-8')}"})
                    return
                    
                # SSE events format: each line starts with "data: " followed by the event data
                # and ends with two newlines
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    while "\n\n" in buffer:
                        message, buffer = buffer.split("\n\n", 1)
                        for line in message.split("\n"):
                            if line.startswith("data: "):
                                data = line[6:]
                                yield data
        except Exception as e:
            yield json.dumps({"status": "error", "error": f"Connection error: {str(e)}"})
            return

async def run_manus_agent_streaming(prompt: str, server_url: Optional[str] = None) -> None:
    """Run the Manus agent with streaming responses using direct endpoint."""
    print(f"\n=== Running Manus Agent (Streaming Mode) ===")
    print(f"Prompt: {prompt}")

    try:
        # Use the direct streaming endpoint
        async for event in stream_from_direct_endpoint(prompt, server_url):
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

    except Exception as e:
        print(f"Error in streaming: {e}")

async def main() -> None:
    """Run the example."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Manus Agent MCP Client Example")
    parser.add_argument(
        "--prompt", "-p",
        type=str,
        default="Tell me about the history of artificial intelligence",
        help="Prompt to send to the Manus agent"
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["simple", "streaming", "direct"],
        default="direct",
        help="Mode to run the client in (simple=no streaming, streaming=standard api, direct=dedicated endpoint)"
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
    elif args.mode == "streaming":
        print("Running in standard streaming mode")
        print("WARNING: Standard streaming mode may not work correctly")
        await run_manus_agent_streaming(args.prompt, server_url)
    else:
        print("Running with direct streaming endpoint (recommended mode)")
        print("NOTE: Make sure the server is running with SSE transport:")
        print(f"      python run_mcp_server.py --transport sse --host {args.host} --port {args.port}")
        await run_manus_agent_streaming(args.prompt, server_url)


if __name__ == "__main__":
    asyncio.run(main())
