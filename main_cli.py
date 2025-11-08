#!/usr/bin/env python3
"""
OpenManus CLI - Secondary Entry Point

CLI mode for automation and scripting. GUI is the primary interface.
"""

import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.logger import logger
from app.config import config


class OpenManusCLI:
    """
    Command-line interface for OpenManus.
    
    Secondary entry point for automation and scripting.
    For interactive use, prefer the GUI (main_gui.py).
    """
    
    def __init__(self):
        """Initialize the CLI."""
        self.parser = self._create_parser()
        logger.info("OpenManus CLI initialized")
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            description="OpenManus - AI Agent Framework (CLI Mode)",
            epilog="For interactive use, run: python main_gui.py"
        )
        
        parser.add_argument(
            "--version",
            action="version",
            version="OpenManus 1.0.0"
        )
        
        parser.add_argument(
            "-v", "--verbose",
            action="store_true",
            help="Enable verbose logging"
        )
        
        parser.add_argument(
            "--workspace",
            type=Path,
            help="Workspace directory path"
        )
        
        # Subcommands
        subparsers = parser.add_subparsers(dest="command", help="Available commands")
        
        # Agent command
        agent_parser = subparsers.add_parser("agent", help="Run an agent")
        agent_parser.add_argument("agent_name", help="Name of the agent to run")
        agent_parser.add_argument("--task", required=True, help="Task description")
        agent_parser.add_argument("--output", type=Path, help="Output file")
        
        # Tool command
        tool_parser = subparsers.add_parser("tool", help="Execute a tool")
        tool_parser.add_argument("tool_name", help="Name of the tool")
        tool_parser.add_argument("args", nargs="*", help="Tool arguments")
        
        # Server command
        server_parser = subparsers.add_parser("server", help="Start MCP server")
        server_parser.add_argument("--port", type=int, default=3000, help="Port to listen on")
        server_parser.add_argument("--host", default="localhost", help="Host to bind to")
        
        # Config command
        config_parser = subparsers.add_parser("config", help="Manage configuration")
        config_parser.add_argument("action", choices=["show", "set", "reset"], help="Config action")
        config_parser.add_argument("--key", help="Config key")
        config_parser.add_argument("--value", help="Config value")
        
        return parser
    
    def run(self, args=None):
        """
        Run the CLI application.
        
        Args:
            args: Command line arguments (None = use sys.argv)
            
        Returns:
            Exit code
        """
        try:
            # Parse arguments
            parsed_args = self.parser.parse_args(args)
            
            # Configure logging
            if parsed_args.verbose:
                logging.basicConfig(level=logging.DEBUG)
            else:
                logging.basicConfig(level=logging.INFO)
            
            logger.info("=" * 60)
            logger.info("OpenManus CLI Mode")
            logger.info("=" * 60)
            
            # Set workspace
            if parsed_args.workspace:
                config.local_service.workspace_directory = str(parsed_args.workspace)
                logger.info(f"Workspace: {parsed_args.workspace}")
            
            # Execute command
            if not parsed_args.command:
                self.parser.print_help()
                print("\nNote: For interactive use, run: python main_gui.py")
                return 0
            
            if parsed_args.command == "agent":
                return self._run_agent(parsed_args)
            
            elif parsed_args.command == "tool":
                return self._run_tool(parsed_args)
            
            elif parsed_args.command == "server":
                return self._run_server(parsed_args)
            
            elif parsed_args.command == "config":
                return self._manage_config(parsed_args)
            
            else:
                logger.error(f"Unknown command: {parsed_args.command}")
                return 1
            
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            return 130
        
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return 1
    
    def _run_agent(self, args) -> int:
        """Run an agent."""
        logger.info(f"Running agent: {args.agent_name}")
        logger.info(f"Task: {args.task}")
        
        # TODO: Implement agent execution
        logger.warning("Agent execution not yet implemented in CLI mode")
        logger.info("Use the GUI (main_gui.py) for full agent orchestration")
        
        return 0
    
    def _run_tool(self, args) -> int:
        """Execute a tool."""
        logger.info(f"Executing tool: {args.tool_name}")
        logger.info(f"Arguments: {args.args}")
        
        # TODO: Implement tool execution
        logger.warning("Tool execution not yet implemented in CLI mode")
        logger.info("Use the GUI (main_gui.py) for full tool support")
        
        return 0
    
    def _run_server(self, args) -> int:
        """Start MCP server."""
        logger.info(f"Starting MCP server on {args.host}:{args.port}")
        
        try:
            # Import and start MCP server
            from app.mcp.server import start_mcp_server
            
            # Run server (blocking)
            start_mcp_server(host=args.host, port=args.port)
            
        except ImportError:
            logger.error("MCP server not available")
            return 1
        
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
            return 1
        
        return 0
    
    def _manage_config(self, args) -> int:
        """Manage configuration."""
        if args.action == "show":
            # Show configuration
            print("Current Configuration:")
            print(f"  Theme: {config.ui.theme}")
            print(f"  Workspace: {config.local_service.workspace_directory}")
            print(f"  LLM Model: {config.llm.model}")
            return 0
        
        elif args.action == "set":
            if not args.key or not args.value:
                logger.error("--key and --value required for 'set' action")
                return 1
            
            # TODO: Implement config setting
            logger.warning("Config setting not yet implemented")
            return 1
        
        elif args.action == "reset":
            logger.info("Resetting configuration to defaults")
            # TODO: Implement config reset
            return 0
        
        return 0


def main():
    """Main entry point."""
    cli = OpenManusCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
