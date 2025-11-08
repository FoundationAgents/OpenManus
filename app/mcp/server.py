"""
Legacy MCP Server - now redirects to modular server.
This file is maintained for backward compatibility.
"""

import argparse
import asyncio
import sys

from app.logger import logger
from app.mcp.modular_server import ModularMCPServer


class MCPServer:
    """Legacy MCP Server class - redirects to modular implementation."""
    
    def __init__(self, name: str = "ixlinx-agent"):
        logger.warning("MCPServer is deprecated, use ModularMCPServer instead")
        self.modular_server = ModularMCPServer()
        self.name = name

    def run(self, transport: str = "stdio") -> None:
        """Run the MCP server using modular implementation."""
        logger.info(f"Starting legacy MCPServer ({transport} mode) - redirecting to modular server")
        
        # Run the tools service by default for backward compatibility
        asyncio.run(self.modular_server.run_service("tools"))


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="iXlinx Agent Legacy MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Communication method: stdio or sse (default: stdio)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    # Show deprecation warning
    logger.warning(
        "This legacy MCP server is deprecated. "
        "Use 'python -m app.mcp.modular_server' instead."
    )
    
    # Create and run server (redirecting to modular)
    server = MCPServer()
    server.run(transport=args.transport)
