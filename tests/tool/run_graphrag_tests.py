#!/usr/bin/env python3
"""
Test runner for GraphRAG query tool tests.

This script provides convenient ways to run GraphRAG tests with different configurations.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_tests(test_type="unit", verbose=False, coverage=False):
    """Run GraphRAG tests with specified configuration."""

    # Base pytest command
    cmd = ["python3", "-m", "pytest"]

    # Add verbosity
    if verbose:
        cmd.append("-v")

    # Add coverage if requested
    if coverage:
        cmd.extend(["--cov=app.tool.graphrag_query", "--cov-report=html", "--cov-report=term"])

    # Determine which tests to run
    if test_type == "unit":
        cmd.append("tests/tool/test_graphrag_query.py::TestGraphRAGQuery")
        print("🧪 Running unit tests for GraphRAG query tool...")
    elif test_type == "integration":
        cmd.extend(["-m", "integration", "tests/tool/test_graphrag_query.py"])
        print("🔗 Running integration tests for GraphRAG query tool...")
    elif test_type == "all":
        cmd.append("tests/tool/test_graphrag_query.py")
        print("🚀 Running all tests for GraphRAG query tool...")
    elif test_type == "quick":
        cmd.extend(["-m", "not slow and not integration", "tests/tool/test_graphrag_query.py"])
        print("⚡ Running quick tests for GraphRAG query tool...")
    else:
        print(f"❌ Unknown test type: {test_type}")
        return 1

    # Run the tests from project root directory
    try:
        # Get project root (two levels up from tests/tool/)
        project_root = Path(__file__).parent.parent.parent
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def check_graphrag_setup():
    """Check if GraphRAG is properly set up."""
    print("🔍 Checking GraphRAG setup...")

    try:
        # Check if graphrag module is available
        result = subprocess.run(["python3", "-m", "graphrag", "--help"], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ GraphRAG module is available")

            # Check if yh_rag directory exists (from project root)
            project_root = Path(__file__).parent.parent.parent
            yh_rag_path = project_root / "yh_rag"
            if yh_rag_path.exists():
                print("✅ yh_rag directory found")

                # Check for settings.yaml
                settings_file = yh_rag_path / "settings.yaml"
                if settings_file.exists():
                    print("✅ settings.yaml found")
                else:
                    print("⚠️  settings.yaml not found in yh_rag directory")

                return True
            else:
                print("⚠️  yh_rag directory not found")
                print("   Integration tests may be skipped")
                return False
        else:
            print("❌ GraphRAG module not available")
            print("   Install with: pip install graphrag")
            return False

    except Exception as e:
        print(f"❌ Error checking GraphRAG setup: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run GraphRAG query tool tests")
    parser.add_argument(
        "test_type",
        choices=["unit", "integration", "all", "quick", "check"],
        default="unit",
        nargs="?",
        help="Type of tests to run (default: unit)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Run tests with verbose output")
    parser.add_argument("-c", "--coverage", action="store_true", help="Run tests with coverage reporting")

    args = parser.parse_args()

    print("🧪 GraphRAG Query Tool Test Runner")
    print("=" * 40)

    if args.test_type == "check":
        setup_ok = check_graphrag_setup()
        return 0 if setup_ok else 1

    # Check setup before running tests
    if args.test_type in ["integration", "all"]:
        setup_ok = check_graphrag_setup()
        if not setup_ok:
            print("\n⚠️  GraphRAG setup issues detected.")
            print("   Integration tests may fail or be skipped.")
            response = input("   Continue anyway? (y/N): ")
            if response.lower() != "y":
                return 1

    # Run the tests
    return run_tests(args.test_type, args.verbose, args.coverage)


if __name__ == "__main__":
    sys.exit(main())
