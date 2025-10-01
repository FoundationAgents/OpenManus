#!/usr/bin/env python
"""Test script for Chainlit integration with OpenManus."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.frontend.chainlit_app import ChainlitOpenManus
from app.logger import logger


async def test_agent_initialization():
    """Test agent initialization and cleanup."""
    print("🧪 Testing agent initialization...")

    chainlit_manus = ChainlitOpenManus()

    try:
        # Test initialization
        agent = await chainlit_manus.initialize_agent()
        assert agent is not None, "Agent should be initialized"
        print("✅ Agent initialized successfully")

        # Test basic functionality
        assert hasattr(agent, "available_tools"), "Agent should have tools"
        assert hasattr(agent, "memory"), "Agent should have memory"
        print(f"✅ Agent has {len(agent.available_tools.tools)} tools available")

        # Test simple query
        response = await agent.run("Hello, what can you do?")
        assert response, "Agent should respond to queries"
        print("✅ Agent responds to queries")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

    finally:
        # Test cleanup
        await chainlit_manus.cleanup_agent()
        print("✅ Agent cleaned up successfully")

    return True


async def test_configuration_setup():
    """Test configuration setup."""
    print("🧪 Testing configuration setup...")

    try:
        from app.frontend.chainlit_config import CHAINLIT_CONFIG, setup_chainlit_config

        # Test config generation
        setup_chainlit_config(PROJECT_ROOT / "test_config")

        config_file = PROJECT_ROOT / "test_config" / ".chainlit" / "config.toml"
        assert config_file.exists(), "Config file should be created"
        print("✅ Configuration file created")

        # Test config content
        content = config_file.read_text()
        assert "OpenManus" in content, "Config should contain project name"
        assert "Multi-Agent" in content, "Config should contain description"
        print("✅ Configuration content is correct")

        # Cleanup test config
        import shutil

        shutil.rmtree(PROJECT_ROOT / "test_config")
        print("✅ Test configuration cleaned up")

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

    return True


def test_dependencies():
    """Test if all required dependencies are available."""
    print("🧪 Testing dependencies...")

    required_modules = ["chainlit", "uvicorn", "fastapi", "websockets", "aiofiles"]

    missing = []

    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} is available")
        except ImportError:
            print(f"❌ {module} is missing")
            missing.append(module)

    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False

    return True


async def run_tests():
    """Run all integration tests."""
    print("🚀 Starting OpenManus Chainlit Integration Tests\n")

    tests = [
        ("Dependencies", test_dependencies),
        ("Configuration Setup", test_configuration_setup),
        ("Agent Integration", test_agent_initialization),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print("=" * 50)

        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()

            results.append((test_name, result))

        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print(f"\n\n{'='*50}")
    print("TEST SUMMARY")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Chainlit integration is ready to use.")
        print("\nTo start the frontend, run:")
        print("  python run_chainlit.py")
        return True
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
