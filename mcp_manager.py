#!/usr/bin/env python
"""
MCP Server Manager - Start/stop internal MCP servers.
Provides CLI for managing internal MCP services.
"""

import argparse
import asyncio
import json
import signal
import sys
from typing import Dict, List

from app.config import config
from app.logger import logger
from app.mcp.modular_server import ModularMCPServer


class MCPServerManager:
    """Manager for MCP servers lifecycle."""

    def __init__(self):
        self.servers: Dict[str, ModularMCPServer] = {}
        self.running = False

    async def start_server(self, service_name: str, transport: str = "stdio") -> None:
        """Start a specific service."""
        logger.info(f"Starting MCP service: {service_name}")
        
        server = ModularMCPServer()
        await server.initialize_service(service_name)
        
        self.servers[service_name] = server
        
        try:
            await server.run_service(service_name)
        except KeyboardInterrupt:
            logger.info(f"Service {service_name} stopped by user")
        except Exception as e:
            logger.error(f"Service {service_name} error: {e}")
        finally:
            if service_name in self.servers:
                del self.servers[service_name]

    async def start_all_enabled(self, transport: str = "stdio") -> None:
        """Start all enabled services."""
        logger.info("Starting all enabled MCP services")
        
        mcp_config = config.mcp_config
        internal_servers = getattr(mcp_config, 'internal_servers', {})
        
        tasks = []
        for service_name, service_config in internal_servers.items():
            if service_config.get("enabled", True) and service_config.get("autoStart", True):
                task = asyncio.create_task(
                    self.start_server(service_name, transport)
                )
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            logger.warning("No enabled services found to start")

    async def stop_server(self, service_name: str) -> None:
        """Stop a specific service."""
        if service_name in self.servers:
            server = self.servers[service_name]
            await server.cleanup()
            del self.servers[service_name]
            logger.info(f"Stopped service: {service_name}")
        else:
            logger.warning(f"Service {service_name} not running")

    async def stop_all(self) -> None:
        """Stop all running services."""
        logger.info("Stopping all MCP services")
        
        for service_name in list(self.servers.keys()):
            await self.stop_server(service_name)

    async def list_services(self) -> None:
        """List all configured services."""
        print("Configured MCP Services:")
        print("=" * 50)
        
        # List available services
        from app.mcp.service_base import list_services
        available = list_services()
        print(f"Available services: {', '.join(available)}")
        print()
        
        # Show configured services
        mcp_config = config.mcp_config
        internal_servers = getattr(mcp_config, 'internal_servers', {})
        external_servers = getattr(mcp_config, 'external_servers', {})
        
        if internal_servers:
            print("Internal Services:")
            for name, server_config in internal_servers.items():
                enabled = server_config.get("enabled", True)
                auto_start = server_config.get("autoStart", True)
                transport = server_config.get("type", "stdio")
                status = "✓" if enabled else "✗"
                print(f"  {name} [{status}] - {transport} (auto-start: {auto_start})")
        
        if external_servers:
            print("\nExternal Services:")
            for name, server_config in external_servers.items():
                enabled = server_config.get("enabled", False)
                transport = server_config.get("type", "sse")
                status = "✓" if enabled else "✗"
                url = server_config.get("url", "N/A")
                print(f"  {name} [{status}] - {transport} @ {url}")

    async def show_status(self) -> None:
        """Show status of running services."""
        print("Running MCP Services:")
        print("=" * 30)
        
        if not self.servers:
            print("No services currently running")
            return
        
        for service_name, server in self.servers.items():
            discovery_info = server.get_discovery_info()
            tools_count = len(discovery_info.get("tools", {}))
            print(f"  {service_name}: {tools_count} tools")

    async def discover_tools(self, service_name: str = None) -> None:
        """Discover tools from services."""
        if service_name:
            # Discover from specific service
            server = ModularMCPServer()
            await server.initialize_service(service_name)
            discovery_info = server.get_discovery_info()
            print(f"Tools for {service_name}:")
            print(json.dumps(discovery_info["tools"], indent=2))
            await server.cleanup()
        else:
            # Discover from all services
            mcp_config = config.mcp_config
            internal_servers = getattr(mcp_config, 'internal_servers', {})
            
            for name in internal_servers.keys():
                await self.discover_tools(name)
                print()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="MCP Server Manager")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start services")
    start_parser.add_argument(
        "service", nargs="?", help="Service name (or 'all' for enabled services)"
    )
    start_parser.add_argument(
        "--transport", "-t", choices=["stdio", "sse"], default="stdio",
        help="Transport type"
    )
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop services")
    stop_parser.add_argument(
        "service", nargs="?", help="Service name (or 'all' for all services)"
    )
    
    # List command
    subparsers.add_parser("list", help="List configured services")
    
    # Status command
    subparsers.add_parser("status", help="Show running services status")
    
    # Discover command
    discover_parser = subparsers.add_parser("discover", help="Discover tools")
    discover_parser.add_argument(
        "service", nargs="?", help="Service name (omit for all services)"
    )
    
    return parser.parse_args()


async def main():
    """Main entry point."""
    try:
        args = parse_args()
    except SystemExit:
        # Handle argparse exit gracefully
        return
    
    manager = MCPServerManager()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(manager.stop_all())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.command == "start":
            if not args.service or args.service == "all":
                await manager.start_all_enabled(args.transport)
            else:
                await manager.start_server(args.service, args.transport)
        
        elif args.command == "stop":
            if not args.service or args.service == "all":
                await manager.stop_all()
            else:
                await manager.stop_server(args.service)
        
        elif args.command == "list":
            await manager.list_services()
        
        elif args.command == "status":
            await manager.show_status()
        
        elif args.command == "discover":
            await manager.discover_tools(args.service)
        
        else:
            print("Unknown command. Use --help for available commands.")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        await manager.stop_all()
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())