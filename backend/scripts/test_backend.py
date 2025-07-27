#!/usr/bin/env python3
"""
OpenManus Backend Function Test Script
"""

import asyncio
import os
import sys

# Add project root directory to Python path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from tests.test_api import main as test_main

if __name__ == "__main__":
    asyncio.run(test_main())
