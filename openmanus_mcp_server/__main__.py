"""Allow running the MCP server as a module: python -m openmanus_mcp_server"""
import asyncio

from openmanus_mcp_server.server import main  # noqa: E402


if __name__ == "__main__":
    asyncio.run(main())
