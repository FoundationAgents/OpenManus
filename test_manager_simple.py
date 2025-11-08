#!/usr/bin/env python
"""Test manager without exception handling"""

import asyncio
from app.config import config
from app.mcp.modular_server import ModularMCPServer

async def test_list():
    print("Testing list services...")
    mcp_config = config.mcp_config
    internal_servers = getattr(mcp_config, 'internal_servers', {})
    print(f"Internal servers: {internal_servers}")
    print("Done!")

if __name__ == "__main__":
    asyncio.run(test_list())