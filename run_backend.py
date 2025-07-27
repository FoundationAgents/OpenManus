#!/usr/bin/env python3
"""
OpenManus Backend Startup Script
"""

import argparse
import os
import sys

import uvicorn

# Add project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app.main import app


def main():
    parser = argparse.ArgumentParser(description="Start OpenManus Backend service")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Service listening address (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Service port (default: 8000)"
    )
    parser.add_argument(
        "--reload", action="store_true", help="Enable hot reload (development mode)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Log level (default: info)",
    )

    args = parser.parse_args()

    print(f"Starting OpenManus Backend service...")
    print(f"Address: http://{args.host}:{args.port}")
    print(f"API Documentation: http://{args.host}:{args.port}/docs")
    print(f"Hot Reload: {'Enabled' if args.reload else 'Disabled'}")
    print(f"Log Level: {args.log_level}")
    print("-" * 50)

    uvicorn.run(
        "backend.app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
