#!/usr/bin/env python
"""Launch script for Chainlit frontend with OpenManus integration."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.frontend.chainlit_config import set_chainlit_env_vars, setup_chainlit_config
from app.logger import logger


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Launch OpenManus with Chainlit frontend",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default="localhost", help="Host address to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port number to bind to")
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode with detailed logging"
    )
    parser.add_argument(
        "--auto-reload", action="store_true", help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (no browser auto-open)",
    )
    parser.add_argument(
        "--config-only",
        action="store_true",
        help="Only setup configuration files and exit",
    )
    return parser.parse_args()


def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = ["chainlit", "uvicorn", "fastapi", "websockets", "aiofiles"]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        logger.error(f"Missing required packages: {', '.join(missing_packages)}")
        logger.error(
            "Please install them with: pip install chainlit uvicorn fastapi websockets aiofiles"
        )
        return False

    return True


def setup_environment(args):
    """Setup environment for Chainlit."""
    # Setup Chainlit configuration
    logger.info("Setting up Chainlit configuration...")
    setup_chainlit_config(PROJECT_ROOT)

    # Set environment variables
    set_chainlit_env_vars(host=args.host, port=args.port, debug=args.debug)

    # Additional environment variables
    if args.headless:
        os.environ["CHAINLIT_HEADLESS"] = "1"

    if args.auto_reload:
        os.environ["CHAINLIT_WATCH"] = "1"

    logger.info(f"Environment configured for {args.host}:{args.port}")


def main():
    """Main entry point."""
    args = parse_args()

    print("\n" + "=" * 60)
    print("🤖 OpenManus Chainlit Frontend")
    print("=" * 60)

    # Setup environment
    setup_environment(args)

    if args.config_only:
        logger.info("Configuration setup complete. Exiting.")
        return

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    logger.info(f"Starting OpenManus Chainlit frontend on {args.host}:{args.port}")

    if args.debug:
        logger.info("Debug mode enabled")
    if args.auto_reload:
        logger.info("Auto-reload enabled")
    if args.headless:
        logger.info("Headless mode enabled")

    try:
        # Import Chainlit after environment setup
        import chainlit as cl

        # Import our app handlers
        from app.frontend import chainlit_app  # This imports all handlers

        logger.info("Chainlit handlers loaded successfully")

        # Launch Chainlit
        print(f"\n🚀 Launching Chainlit frontend...")
        print(f"📱 Web interface: http://{args.host}:{args.port}")
        print(f"🛑 Press Ctrl+C to stop\n")

        # Run Chainlit using the CLI approach
        import subprocess

        cmd = [
            sys.executable,
            "-m",
            "chainlit",
            "run",
            "app/frontend/chainlit_app.py",
            "--host",
            args.host,
            "--port",
            str(args.port),
        ]

        if args.headless:
            cmd.append("--headless")

        if args.auto_reload:
            cmd.append("--watch")

        # Run the command
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        sys.exit(result.returncode)

    except KeyboardInterrupt:
        logger.info("\n🛑 Shutdown requested by user")
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure Chainlit is installed: pip install chainlit")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error launching Chainlit frontend: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
