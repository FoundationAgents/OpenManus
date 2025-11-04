#!/usr/bin/env python
import argparse
import asyncio
import os
import sys
from pathlib import Path

from app.agent.mcp import MCPAgent
from app.config import config
from app.logger import logger


def load_prompt_from_file(file_path: str) -> str:
    """Load prompt content from a file."""
    try:
        # Convert to absolute path if it's relative
        if not os.path.isabs(file_path):
            # Make path relative to the current working directory
            file_path = os.path.join(os.getcwd(), file_path)

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path, encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            raise ValueError(f"File is empty: {file_path}")

        logger.info(f"Successfully loaded prompt from file: {file_path}")
        return content

    except Exception as e:
        logger.error(f"Failed to load prompt from file '{file_path}': {e}")
        raise


class MCPRunner:
    """Runner class for MCP Agent with proper path handling and configuration."""

    def __init__(self):
        self.root_path = config.root_path
        self.server_reference = config.mcp_config.server_reference
        self.agent = MCPAgent()

    async def initialize(
        self,
        connection_type: str,
        server_url: str | None = None,
    ) -> None:
        """Initialize the MCP agent with the appropriate connection."""
        logger.info(f"Initializing MCPAgent with {connection_type} connection...")

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
            user_input = input("\nEnter your request (or file:path/to/file): ")
            if user_input.lower() in ["exit", "quit", "q"]:
                break

            # Check if input starts with 'file:' prefix
            if user_input.startswith("file:"):
                try:
                    file_path = user_input[5:]  # Remove 'file:' prefix
                    prompt = load_prompt_from_file(file_path)
                    response = await self.agent.run(prompt)
                except Exception as e:
                    print(f"\nError loading file: {e}")
                    continue
            else:
                response = await self.agent.run(user_input)
            print(f"\nAgent: {response}")

    async def run_single_prompt(self, prompt: str) -> None:
        """Run the agent with a single prompt."""
        # Check if prompt starts with 'file:' prefix
        if prompt.startswith("file:"):
            file_path = prompt[5:]  # Remove 'file:' prefix
            actual_prompt = load_prompt_from_file(file_path)
        else:
            actual_prompt = prompt

        await self.agent.run(actual_prompt)

    async def run_default(self) -> None:
        """Run the agent in default mode."""
        prompt_input = input("Enter your prompt (or file:path/to/file): ")
        if not prompt_input.strip():
            logger.warning("Empty prompt provided.")
            return

        # Check if prompt starts with 'file:' prefix
        if prompt_input.startswith("file:"):
            file_path = prompt_input[5:]  # Remove 'file:' prefix
            prompt = load_prompt_from_file(file_path)
        else:
            prompt = prompt_input

        logger.warning("Processing your request...")
        await self.agent.run(prompt)
        logger.info("Request processing completed.")

    async def cleanup(self) -> None:
        """Clean up agent resources."""
        await self.agent.cleanup()
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
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument(
        "--prompt", "-p", help="Single prompt to execute and exit. Use 'file:path/to/file' to load prompt from a file."
    )
    return parser.parse_args()


async def run_mcp() -> None:
    """Main entry point for the MCP runner."""
    args = parse_args()
    runner = MCPRunner()

    try:
        await runner.initialize(args.connection, args.server_url)

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
