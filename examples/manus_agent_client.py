"""
Example client for using the Manus agent through MCP.

This example demonstrates how to use the high-level Manus agent through the MCP client,
both with and without streaming responses.
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

from mcp.client.session import Session as MCPSession
from mcp.client.stdio import StdioTransport
from sse_starlette.sse import EventSourceResponse  # For SSE type hints


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


async def run_manus_agent_streaming(prompt: str, server_url: Optional[str] = None) -> None:
    """Run the Manus agent with streaming responses over SSE."""
    print(f"\n=== Running Manus Agent (Streaming Mode) ===")
    print(f"Prompt: {prompt}")

    # Import the HTTP client for SSE
    import httpx
    import asyncio
    from urllib.parse import urljoin

    # Define the server URL
    base_url = server_url or "http://localhost:8000"
    api_url = urljoin(base_url, "/call/manus_agent")
    
    print(f"Connecting to {api_url}")
    
    # Make an HTTP request with streaming response
    async with httpx.AsyncClient() as client:
        try:
            # Call the agent with streaming enabled
            async with client.stream(
                "POST", 
                api_url,
                json={"prompt": prompt, "streaming": True},
                headers={"Accept": "text/event-stream"},
                timeout=120.0
            ) as response:
                if response.status_code != 200:
                    print(f"Error: Server returned status code {response.status_code}")
                    try:
                        error_text = await response.aread()
                        print(f"Error response: {error_text}")
                    except:
                        pass
                    return
                
                # Process SSE events
                buffer = ""
                async for chunk in response.aiter_bytes():
                    buffer += chunk.decode("utf-8")
                    
                    # Process complete SSE events
                    while "\n\n" in buffer:
                        event, buffer = buffer.split("\n\n", 1)
                        lines = event.split("\n")
                        data = None
                        
                        for line in lines:
                            if line.startswith("data: "):
                                data = line[6:]
                                break
                        
                        if data:
                            try:
                                # Parse and display each event
                                event_data = json.loads(data)
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

                            except json.JSONDecodeError as e:
                                print(f"Received invalid JSON: {data}\nError: {e}")

        except Exception as e:
            print(f"Error connecting to server: {e}")


async def main() -> None:
    """Run the example."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Manus Agent MCP Client Example")
    parser.add_argument(
        "prompt", 
        nargs="*", 
        default=["Tell me a joke about AI agents"],
        help="Prompt to send to the Manus agent"
    )
    parser.add_argument(
        "--mode", 
        choices=["simple", "streaming"],
        default="streaming",
        help="Mode to run the client in (default: streaming)"
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
    prompt = " ".join(args.prompt)
    server_url = f"http://{args.host}:{args.port}"
    
    print(f"Using prompt: {prompt}")
    
    if args.mode == "simple":
        print("Running in simple mode (non-streaming)")
        await run_manus_agent_simple(prompt)
    else:
        print(f"Running in streaming mode, connecting to {server_url}")
        print("NOTE: Make sure the server is running with SSE transport:")
        print(f"      python run_mcp_server.py --transport sse --host {args.host} --port {args.port}")
        await run_manus_agent_streaming(prompt, server_url)


if __name__ == "__main__":
    asyncio.run(main())
