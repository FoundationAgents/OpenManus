#!/usr/bin/env python3
"""
OpenManus System Integration Entry Point
Starts the complete integrated system with all subsystems
"""

import sys
import os

# Add to project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.system_startup import main

if __name__ == "__main__":
    main()
