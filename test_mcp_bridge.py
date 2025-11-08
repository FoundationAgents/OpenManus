#!/usr/bin/env python
"""
Test script for MCP Bridge functionality.
Tests both native tool calling and MCP stdio fallback modes.
"""

import asyncio
import json
import sys

from app.config import config
from app.logger import logger
from app.mcp.bridge import MCPBridge


async def test_native_mode():
    """Test MCP Bridge in native mode."""
    print("\n=== Testing Native Mode ===")
    
    # Create a model config that supports tools
    model_config = {
        "model": "gpt-4",
        "api_type": "openai",
        "supports_tools": True,
        "base_url": "https://api.openai.com/v1"
    }
    
    bridge = MCPBridge()
    
    try:
        # Initialize with native mode
        await bridge.initialize(model_config)
        
        print(f"Fallback active: {bridge.is_fallback_active()}")
        print(f"Available tools: {bridge.get_tool_names()}")
        
        # Test tool execution
        if "bash" in bridge.get_tool_names():
            result = await bridge.execute_tool("bash", command="echo 'Hello from native mode!'")
            print(f"Tool result: {result}")
        
        # Get status
        status = bridge.get_status()
        print(f"Bridge status: {json.dumps(status, indent=2)}")
        
    except Exception as e:
        print(f"Error in native mode: {e}")
    finally:
        await bridge.cleanup()


async def test_fallback_mode():
    """Test MCP Bridge in fallback mode."""
    print("\n=== Testing Fallback Mode ===")
    
    # Create a model config that doesn't support tools
    model_config = {
        "model": "llama2",
        "api_type": "ollama",
        "supports_tools": False,
        "base_url": "http://localhost:11434"
    }
    
    bridge = MCPBridge()
    
    try:
        # Initialize with fallback mode
        await bridge.initialize(model_config)
        
        print(f"Fallback active: {bridge.is_fallback_active()}")
        print(f"Available tools: {bridge.get_tool_names()}")
        
        # List all tools
        tools = await bridge.list_tools()
        print(f"Tool schemas: {json.dumps(tools, indent=2)}")
        
        # Test tool execution if available
        tool_names = bridge.get_tool_names()
        if tool_names:
            # Try to execute the first available tool
            tool_name = tool_names[0]
            if tool_name == "bash" or "bash" in tool_name:
                result = await bridge.execute_tool(tool_name, command="echo 'Hello from fallback mode!'")
                print(f"Tool result: {result}")
        
        # Get status
        status = bridge.get_status()
        print(f"Bridge status: {json.dumps(status, indent=2)}")
        
    except Exception as e:
        print(f"Error in fallback mode: {e}")
    finally:
        await bridge.cleanup()


async def test_discovery():
    """Test MCP server discovery."""
    print("\n=== Testing Server Discovery ===")
    
    from app.mcp.modular_server import ModularMCPServer
    
    try:
        server = ModularMCPServer()
        await server.initialize_from_config()
        
        discovery_info = server.get_discovery_info()
        print(f"Discovery info: {json.dumps(discovery_info, indent=2)}")
        
    except Exception as e:
        print(f"Error in discovery: {e}")


async def test_config_loading():
    """Test configuration loading."""
    print("\n=== Testing Configuration Loading ===")
    
    try:
        mcp_config = config.mcp_config
        
        print(f"Server reference: {mcp_config.server_reference}")
        print(f"Default transport: {mcp_config.default_transport}")
        print(f"Enable fallback: {mcp_config.enable_fallback}")
        print(f"Internal servers: {list(mcp_config.internal_servers.keys())}")
        print(f"External servers: {list(mcp_config.external_servers.keys())}")
        
        # Test loading bridge config directly
        bridge_config = type(mcp_config).load_bridge_config()
        print(f"Bridge config keys: {list(bridge_config.keys())}")
        
    except Exception as e:
        print(f"Error loading config: {e}")


async def main():
    """Main test runner."""
    print("MCP Bridge Test Suite")
    print("====================")
    
    # Parse command line arguments
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if test_type in ["all", "config"]:
        await test_config_loading()
    
    if test_type in ["all", "native"]:
        await test_native_mode()
    
    if test_type in ["all", "fallback"]:
        await test_fallback_mode()
    
    if test_type in ["all", "discovery"]:
        await test_discovery()
    
    print("\n=== Test Suite Complete ===")


if __name__ == "__main__":
    asyncio.run(main())