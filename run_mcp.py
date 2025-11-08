#!/usr/bin/env python
import argparse
import asyncio
import sys

from app.agent.mcp import MCPAgent
from app.config import config
from app.logger import logger
from app.mcp.bridge import MCPBridge


class MCPRunner:
    """Runner class for MCP Agent with proper path handling and configuration."""

    def __init__(self):
        self.root_path = config.root_path
        self.server_reference = config.mcp_config.server_reference
        self.agent = MCPAgent()
        self.bridge = MCPBridge()

    async def initialize(
        self,
        connection_type: str,
        server_url: str | None = None,
        use_bridge: bool = False,
    ) -> None:
        """Initialize the MCP agent with the appropriate connection."""
        logger.info(f"Initializing MCPAgent with {connection_type} connection...")

        if use_bridge:
            # Initialize the MCP bridge first
            await self.bridge.initialize()
            logger.info(f"MCP Bridge initialized (fallback: {self.bridge.is_fallback_active()})")
            
            # Configure agent based on bridge mode
            if self.bridge.is_fallback_active():
                # In fallback mode, connect to internal MCP server
                await self.agent.initialize(
                    connection_type="stdio",
                    command=sys.executable,
                    args=["-m", self.server_reference, "--service", "tools"],
                )
            else:
                # In native mode, proceed normally
                if connection_type == "stdio":
                    await self.agent.initialize(
                        connection_type="stdio",
                        command=sys.executable,
                        args=["-m", self.server_reference],
                    )
                else:  # sse
                    await self.agent.initialize(connection_type="sse", server_url=server_url)
        else:
            # Legacy mode - direct connection
            if connection_type == "stdio":
                await self.agent.initialize(
                    connection_type="stdio",
                    command=sys.executable,
                    args=["-m", self.server_reference],
                )
            else:  # sse
                await self.agent.initialize(connection_type="sse", server_url=server_url)

        logger.info(f"Connected to MCP server via {connection_type}")

    async def run_interactive(self) -> None:
        """Run the agent in interactive mode."""
        print("\nMCP Agent Interactive Mode (type 'exit' to quit)\n")
        while True:
            user_input = input("\nEnter your request: ")
            if user_input.lower() in ["exit", "quit", "q"]:
                break
            response = await self.agent.run(user_input)
            print(f"\nAgent: {response}")

    async def run_single_prompt(self, prompt: str) -> None:
        """Run the agent with a single prompt."""
        await self.agent.run(prompt)

    async def run_default(self) -> None:
        """Run the agent in default mode."""
        prompt = input("Enter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        logger.warning("Processing your request...")
        await self.agent.run(prompt)
        logger.info("Request processing completed.")

    async def cleanup(self) -> None:
        """Clean up agent resources."""
        await self.agent.cleanup()
        await self.bridge.cleanup()
        logger.info("Session ended")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the MCP Agent")
    parser.add_argument(
        "--connection",
        "-c",
        choices=["stdio", "sse"],
        default="stdio",
        help="Connection type: stdio or sse",
    )
    parser.add_argument(
        "--server-url",
        default="http://127.0.0.1:8000/sse",
        help="URL for SSE connection",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )
    parser.add_argument("--prompt", "-p", help="Single prompt to execute and exit")
    parser.add_argument(
        "--bridge", "-b", action="store_true", 
        help="Use MCP bridge with automatic fallback"
    )
    parser.add_argument(
        "--start-server", action="store_true",
        help="Start internal MCP server before connecting"
    )
    return parser.parse_args()


async def run_mcp() -> None:
    """Main entry point for the MCP runner."""
    args = parse_args()
    runner = MCPRunner()

    try:
        # Start server if requested
        if args.start_server:
            logger.info("Starting internal MCP server...")
            # This would start the server in the background
            # For now, we'll rely on the bridge to handle it
        
        await runner.initialize(
            args.connection, 
            args.server_url,
            use_bridge=args.bridge
        )

        if args.prompt:
            await runner.run_single_prompt(args.prompt)
        elif args.interactive:
            await runner.run_interactive()
        else:
            await runner.run_default()

    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Error running MCPAgent: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(run_mcp())
