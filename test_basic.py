#!/usr/bin/env python3
"""
Simple test script to verify the OpenManus framework functionality.
This tests basic imports and core functionality without optional dependencies.
"""

import sys
import os
from pathlib import Path

def test_basic_imports():
    """Test basic framework imports."""
    print("Testing basic imports...")
    
    try:
        from app.config import config
        print("✓ Config import successful")
    except Exception as e:
        print(f"✗ Config import failed: {e}")
        return False
    
    try:
        from app.logger import logger
        print("✓ Logger import successful")
    except Exception as e:
        print(f"✗ Logger import failed: {e}")
        return False
    
    try:
        from app.schema import Message
        print("✓ Schema import successful")
    except Exception as e:
        print(f"✗ Schema import failed: {e}")
        return False
    
    return True

def test_config_loading():
    """Test configuration loading."""
    print("\nTesting configuration loading...")
    
    try:
        # Test workspace root
        workspace_root = config.workspace_root
        print(f"✓ Workspace root: {workspace_root}")
        
        # Test local service config
        local_service = config.local_service
        print(f"✓ Local service workspace: {local_service.workspace_directory}")
        
        # Test UI config
        ui_config = config.ui
        print(f"✓ UI config - GUI enabled: {ui_config.enable_gui}, WebUI enabled: {ui_config.enable_webui}")
        
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_workspace():
    """Test workspace functionality."""
    print("\nTesting workspace...")
    
    try:
        workspace = config.workspace_root
        workspace.mkdir(parents=True, exist_ok=True)
        
        # Test file operations
        test_file = workspace / "test.txt"
        test_file.write_text("Hello, OpenManus!")
        
        content = test_file.read_text()
        if content == "Hello, OpenManus!":
            print("✓ File operations successful")
            test_file.unlink()  # Cleanup
            return True
        else:
            print("✗ File content mismatch")
            return False
            
    except Exception as e:
        print(f"✗ Workspace test failed: {e}")
        return False

def test_optional_imports():
    """Test optional imports and provide helpful messages."""
    print("\nTesting optional imports...")
    
    # Test PyQt6
    try:
        import PyQt6
        print("✓ PyQt6 available - GUI mode supported")
    except ImportError:
        print("✗ PyQt6 not available - GUI mode disabled")
        print("  To enable GUI mode: pip install PyQt6")
    
    # Test FastAPI
    try:
        import fastapi
        print("✓ FastAPI available - Web UI mode supported")
    except ImportError:
        print("✗ FastAPI not available - Web UI mode disabled")
        print("  To enable Web UI mode: pip install fastapi uvicorn")
    
    # Test psutil
    try:
        import psutil
        print("✓ psutil available - system monitoring enabled")
    except ImportError:
        print("✗ psutil not available - system monitoring disabled")
        print("  To enable system monitoring: pip install psutil")

def main():
    """Run all tests."""
    print("OpenManus Framework Test Suite")
    print("=" * 40)
    
    # Run tests
    tests_passed = 0
    total_tests = 4
    
    if test_basic_imports():
        tests_passed += 1
    
    if test_config_loading():
        tests_passed += 1
    
    if test_workspace():
        tests_passed += 1
    
    test_optional_imports()  # This is informational
    total_tests += 1
    
    # Summary
    print("\n" + "=" * 40)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✓ All core tests passed! OpenManus framework is working correctly.")
        print("\nTo use the framework:")
        print("  python main.py --help")
        print("\nModes available:")
        print("  - CLI: python main.py")
        print("  - GUI: python main.py --gui (requires PyQt6)")
        print("  - Web UI: python main.py --webui (requires FastAPI)")
        print("  - Agent Flow: python main.py --mode agent_flow")
        print("  - ADE Mode: python main.py --mode ade")
        return 0
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())