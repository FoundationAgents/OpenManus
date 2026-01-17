#!/usr/bin/env python3
"""Test script for OpenManus sandbox backends."""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from app.sandbox.adapters.base import SandboxStatus
    from app.sandbox.adapters.factory import SandboxFactory
    from app.sandbox.adapters.unified_client import UnifiedSandboxClient
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the OpenManus root directory")
    sys.exit(1)


class SandboxTester:
    """Test runner for sandbox backends."""

    def __init__(self):
        self.results = {}
        self.total_tests = 0
        self.passed_tests = 0

    async def test_backend(self, backend_name: str, config: dict = None) -> bool:
        """Test a specific backend."""
        print(f"\n🧪 Testing {backend_name} backend...")
        print("-" * 40)

        try:
            # Test 1: Client Creation
            print("1️⃣  Creating client...", end=" ")
            client = UnifiedSandboxClient(backend_name, config)
            print("✅")

            # Test 2: Sandbox Creation
            print("2️⃣  Creating sandbox...", end=" ")
            start_time = time.time()

            async with client.sandbox_context() as sandbox_id:
                creation_time = time.time() - start_time
                print(f"✅ ({creation_time:.2f}s)")
                print(f"    Sandbox ID: {sandbox_id}")

                # Test 3: Sandbox Info
                print("3️⃣  Getting sandbox info...", end=" ")
                info = await client.get_sandbox_info(sandbox_id)
                print("✅")
                print(f"    Status: {info.status.value}")
                print(f"    Image: {info.image}")
                if info.urls:
                    for name, url in info.urls.items():
                        print(f"    {name.upper()}: {url}")

                # Test 4: Command Execution
                print("4️⃣  Executing commands...", end=" ")

                # Simple echo test
                result = await client.execute(sandbox_id, "echo 'Hello from sandbox!'")
                if "Hello from sandbox!" in result.stdout:
                    print("✅")
                    print(f"    Output: {result.stdout.strip()}")
                    print(f"    Execution time: {result.execution_time:.2f}s")
                else:
                    print("❌")
                    print(f"    Expected output not found")
                    print(f"    Stdout: {result.stdout}")
                    print(f"    Stderr: {result.stderr}")
                    return False

                # Test 5: Python execution
                print("5️⃣  Testing Python...", end=" ")
                python_result = await client.execute(
                    sandbox_id,
                    "python3 -c 'import sys; print(f\"Python {sys.version_info.major}.{sys.version_info.minor}\")'",
                )
                if "Python" in python_result.stdout:
                    print("✅")
                    print(f"    {python_result.stdout.strip()}")
                else:
                    print("⚠️  (Python may not be available)")

                # Test 6: File Operations
                print("6️⃣  Testing file operations...", end=" ")

                # Write file
                test_content = f"Hello from {backend_name} at {time.time()}"
                await client.write_file(sandbox_id, "/tmp/test.txt", test_content)

                # Read file
                read_content = await client.read_file(sandbox_id, "/tmp/test.txt")

                if read_content.strip() == test_content:
                    print("✅")
                    print(f"    File content matches: {len(test_content)} chars")
                else:
                    print("❌")
                    print(f"    Content mismatch")
                    print(f"    Written: {test_content}")
                    print(f"    Read: {read_content}")
                    return False

                # Test 7: Directory Listing
                print("7️⃣  Testing directory listing...", end=" ")
                files = await client.list_files(sandbox_id, "/tmp")
                if "test.txt" in files:
                    print("✅")
                    print(f"    Found {len(files)} files in /tmp")
                else:
                    print("❌")
                    print(f"    test.txt not found in listing: {files}")
                    return False

                # Test 8: Complex command
                print("8️⃣  Testing complex command...", end=" ")
                complex_result = await client.execute(
                    sandbox_id, "ls -la /tmp | grep test.txt | wc -l"
                )
                if complex_result.stdout.strip() == "1":
                    print("✅")
                else:
                    print("⚠️  (Complex piping may not work)")

            print(f"\n✅ {backend_name} backend test PASSED!")
            return True

        except Exception as e:
            print(f"\n❌ {backend_name} backend test FAILED: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def test_docker(self) -> bool:
        """Test Docker backend."""
        return await self.test_backend("docker")

    async def test_gitpod(self) -> bool:
        """Test GitPod backend."""
        config = {}

        # Check for GitPod configuration
        gitpod_url = os.getenv("GITPOD_URL", "http://localhost")
        gitpod_token = os.getenv("GITPOD_TOKEN")

        if not gitpod_token:
            print("⏭️  Skipping GitPod test (no GITPOD_TOKEN environment variable)")
            print("   Set GITPOD_TOKEN to test GitPod backend")
            return None

        config = {"gitpod_url": gitpod_url, "gitpod_token": gitpod_token}

        return await self.test_backend("gitpod", config)

    async def test_e2b(self) -> bool:
        """Test E2B backend."""
        e2b_api_key = os.getenv("E2B_API_KEY")

        if not e2b_api_key:
            print("⏭️  Skipping E2B test (no E2B_API_KEY environment variable)")
            print("   Set E2B_API_KEY to test E2B backend")
            return None

        config = {"api_key": e2b_api_key, "template": os.getenv("E2B_TEMPLATE", "base")}

        return await self.test_backend("e2b", config)

    async def test_factory(self):
        """Test the factory functionality."""
        print("\n🏭 Testing SandboxFactory...")
        print("-" * 30)

        # Test 1: Available adapters
        print("1️⃣  Getting available adapters...", end=" ")
        adapters = SandboxFactory.get_available_adapters()
        print("✅")
        print(f"    Available: {', '.join(adapters)}")

        # Test 2: Auto-detect backend
        print("2️⃣  Auto-detecting backend...", end=" ")
        backend = SandboxFactory.auto_detect_backend()
        print("✅")
        print(f"    Detected: {backend}")

        # Test 3: Create best available
        print("3️⃣  Creating best available adapter...", end=" ")
        try:
            adapter = SandboxFactory.create_best_available()
            print("✅")
            print(f"    Created: {type(adapter).__name__}")
        except Exception as e:
            print("❌")
            print(f"    Error: {e}")
            return False

        return True

    async def run_all_tests(self):
        """Run all available tests."""
        print("🚀 OpenManus Sandbox Backend Test Suite")
        print("=" * 45)

        start_time = time.time()

        # Test factory first
        factory_result = await self.test_factory()
        if factory_result:
            self.passed_tests += 1
        self.total_tests += 1

        # Test backends
        backends_to_test = [
            ("Docker", self.test_docker),
            ("GitPod", self.test_gitpod),
            ("E2B", self.test_e2b),
        ]

        for backend_name, test_func in backends_to_test:
            result = await test_func()
            if result is not None:  # None means skipped
                self.results[backend_name.lower()] = result
                if result:
                    self.passed_tests += 1
                self.total_tests += 1

        total_time = time.time() - start_time

        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)

        print(f"\n🏭 Factory Tests:")
        print(f"  ✅ Factory functionality: {'PASSED' if factory_result else 'FAILED'}")

        print(f"\n🧪 Backend Tests:")
        for backend, success in self.results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"  {backend.title()}: {status}")

        skipped = 3 - len(self.results)  # 3 total backends
        if skipped > 0:
            print(f"\n⏭️  Skipped: {skipped} backend(s) (missing configuration)")

        print(f"\n🎯 Results: {self.passed_tests}/{self.total_tests} tests passed")
        print(f"⏱️  Total time: {total_time:.2f} seconds")

        if self.passed_tests == self.total_tests:
            print("\n🎉 All tests passed! OpenManus sandbox backends are ready to use.")
            return True
        elif self.passed_tests > 0:
            print(
                f"\n⚠️  {self.total_tests - self.passed_tests} test(s) failed, but some backends are working."
            )
            return True
        else:
            print("\n❌ All tests failed. Check your configuration and dependencies.")
            return False


async def main():
    """Main test runner."""
    tester = SandboxTester()

    # Check if running with specific backend
    if len(sys.argv) > 1:
        backend = sys.argv[1].lower()

        if backend == "docker":
            success = await tester.test_docker()
        elif backend == "gitpod":
            success = await tester.test_gitpod()
        elif backend == "e2b":
            success = await tester.test_e2b()
        elif backend == "factory":
            success = await tester.test_factory()
        else:
            print(f"❌ Unknown backend: {backend}")
            print("Available backends: docker, gitpod, e2b, factory")
            sys.exit(1)

        sys.exit(0 if success else 1)

    # Run all tests
    success = await tester.run_all_tests()

    # Show configuration help if some tests failed
    if not success:
        print("\n💡 Configuration Help:")
        print("  Docker: Should work out of the box")
        print("  GitPod: Set GITPOD_URL and GITPOD_TOKEN")
        print("  E2B: Set E2B_API_KEY")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
