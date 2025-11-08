import argparse
import asyncio
import atexit
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from app.config import config
from app.logger import logger
from app.mcp.service_base import SERVICE_REGISTRY, get_service, list_services


class ModularMCPServer:
    """Modular MCP server supporting multiple service registrations."""

    def __init__(self, service_name: Optional[str] = None, transport: str = "stdio"):
        self.service_name = service_name
        self.transport = transport
        self.services: Dict[str, any] = {}
        self.server_info = {
            "name": "ixlinx-agent",
            "version": "1.0.0",
            "transport": transport,
            "services": {},
        }

    async def initialize_service(self, service_name: str) -> bool:
        """Initialize a specific service."""
        service_class = get_service(service_name)
        if not service_class:
            logger.error(f"Unknown service: {service_name}")
            return False

        try:
            service = service_class()
            service.register_tools()
            self.services[service_name] = service
            
            # Store service info
            self.server_info["services"][service_name] = service.get_server_info()
            logger.info(f"Initialized service: {service_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize service {service_name}: {e}")
            return False

    async def initialize_from_config(self) -> None:
        """Initialize services from configuration."""
        mcp_config = config.mcp_config
        
        # Load internal servers configuration
        internal_servers = getattr(mcp_config, 'internal_servers', {})
        if internal_servers:
            for service_name, service_config in internal_servers.items():
                if service_config.get("enabled", True):
                    await self.initialize_service(service_name)

    async def start_discovery_server(self) -> None:
        """Start a discovery endpoint for available tools."""
        # This would be implemented for SSE transport
        if self.transport == "sse":
            logger.info("Discovery server available at /tools endpoint")

    def get_service_server(self, service_name: str) -> Optional[any]:
        """Get the MCP server instance for a specific service."""
        service = self.services.get(service_name)
        if service:
            return service.server
        return None

    async def run_service(self, service_name: str) -> None:
        """Run a specific service."""
        if service_name not in self.services:
            if not await self.initialize_service(service_name):
                raise ValueError(f"Could not initialize service: {service_name}")

        service = self.services[service_name]
        
        # Register cleanup
        atexit.register(lambda: asyncio.run(service.cleanup()))
        
        logger.info(f"Starting {service_name} service ({self.transport} mode)")
        service.server.run(transport=self.transport)

    async def run_all_services(self) -> None:
        """Run all initialized services."""
        if not self.services:
            await self.initialize_from_config()

        if not self.services:
            logger.warning("No services initialized")
            return

        # For now, run the first service (could be extended for multi-service mode)
        service_name = next(iter(self.services))
        await self.run_service(service_name)

    def get_discovery_info(self) -> Dict:
        """Get discovery information about all services."""
        return {
            "server": self.server_info,
            "available_services": list_services(),
            "initialized_services": list(self.services.keys()),
            "tools": self._get_all_tools(),
        }

    def _get_all_tools(self) -> Dict[str, List[Dict]]:
        """Get all available tools from all services."""
        all_tools = {}
        for service_name, service in self.services.items():
            tools = []
            for tool_name, tool in service.get_tools().items():
                tool_param = tool.to_param()
                tools.append({
                    "name": f"{service.namespace}.{tool_name}",
                    "description": tool_param["function"].get("description", ""),
                    "parameters": tool_param["function"].get("parameters", {}),
                })
            all_tools[service_name] = tools
        return all_tools

    async def cleanup(self) -> None:
        """Clean up all services."""
        logger.info("Cleaning up all services")
        for service in self.services.values():
            try:
                await service.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up service: {e}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="OpenManus Modular MCP Server")
    parser.add_argument(
        "--service",
        "-s",
        help="Specific service to run (tools, knowledge, memory)",
        choices=list_services(),
    )
    parser.add_argument(
        "--transport",
        "-t",
        choices=["stdio", "sse"],
        default="stdio",
        help="Communication method: stdio or sse (default: stdio)",
    )
    parser.add_argument(
        "--list-services",
        action="store_true",
        help="List all available services and exit",
    )
    parser.add_argument(
        "--discovery",
        action="store_true", 
        help="Run in discovery mode and show available tools",
    )
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()

    if args.list_services:
        print("Available services:")
        for service_name in list_services():
            service_class = get_service(service_name)
            if service_class:
                service_info = service_class().__dict__.get('namespace', 'unknown')
                print(f"  {service_name} (namespace: {service_info})")
        return

    server = ModularMCPServer(service_name=args.service, transport=args.transport)

    if args.discovery:
        await server.initialize_from_config()
        discovery_info = server.get_discovery_info()
        print(json.dumps(discovery_info, indent=2))
        return

    try:
        if args.service:
            await server.run_service(args.service)
        else:
            await server.run_all_services()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())