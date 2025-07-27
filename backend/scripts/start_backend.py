#!/usr/bin/env python3
"""
OpenManus Backend Startup Script
"""

import argparse
import os
import sys
from pathlib import Path

import uvicorn

# Add project root directory to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.core.config import config


def main():
    parser = argparse.ArgumentParser(description="Start OpenManus Backend service")
    parser.add_argument(
        "--host", type=str, default=config.host, help="Service listening address"
    )
    parser.add_argument("--port", type=int, default=config.port, help="Service port")
    parser.add_argument(
        "--reload", action="store_true", help="Enable hot reload (development mode)"
    )

    args = parser.parse_args()

    print(f"Starting OpenManus Backend service...")
    print(f"Address: http://{args.host}:{args.port}")
    print(f"API Documentation: http://{args.host}:{args.port}/docs")
    print(f"Hot Reload: {'Enabled' if args.reload else 'Disabled'}")
    print(f"Log Level: {args.log_level}")
    print("-" * 50)

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
