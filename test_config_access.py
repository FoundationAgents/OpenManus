#!/usr/bin/env python
"""Simple test to check config access"""

from app.config import config

print("Testing config access...")
print(f"Config type: {type(config)}")
print(f"MCP config: {config.mcp_config}")
print(f"MCP config type: {type(config.mcp_config)}")
print("Done!")