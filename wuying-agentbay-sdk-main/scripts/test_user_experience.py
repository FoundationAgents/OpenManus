#!/usr/bin/env python3
"""
User Experience Test Script
Simulate documentation usage paths for different types of users
"""

import os
import sys
from pathlib import Path


def test_newbie_user_path():
    """Test newbie user path"""
    print("🆕 Test newbie user path...")

    required_files = [
        "README.md",  # Main entry
        "docs/README.md",  # Documentation entry
        "docs/quickstart/README.md",  # Newbie navigation
        "docs/quickstart/installation.md",  # Installation guide
        "docs/quickstart/basic-concepts.md",  # Basic concepts
        "docs/quickstart/first-session.md",  # First session
        "docs/quickstart/faq.md",  # FAQ
    ]

    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)

    if missing_files:
        print(f"  ❌ Missing files: {missing_files}")
        return False
    else:
        print("  ✅ Newbie user path complete")
        return True


def test_experienced_user_path():
    """Test experienced user path"""
    print("🚀 Test experienced user path...")

    required_files = [
        "README.md",  # Main entry
        "docs/guides/README.md",  # Feature navigation
        "docs/guides/session-management.md",  # Session management
        "docs/guides/file-operations.md",  # File operations
        "docs/guides/automation.md",  # Automation features
        "docs/guides/data-persistence.md",  # Data persistence
        "docs/guides/advanced-features.md",  # Advanced features
        "docs/api-reference.md",  # API quick reference
    ]

    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)

    if missing_files:
        print(f"  ❌ Missing files: {missing_files}")
        return False
    else:
        print("  ✅ Experienced user path complete")
        return True


def test_package_user_path():
    """Test package installation user path"""
    print("📦 Test package installation user path...")

    languages = ["python", "typescript", "golang"]
    all_good = True

    for lang in languages:
        print(f"  Testing {lang.upper()} user path...")

        required_files = [
            f"{lang}/README.md",  # Language-specific README
            f"{lang}/docs/api/README.md",  # API documentation
        ]

        # Check example code
        examples_dir = f"{lang}/docs/examples"
        if os.path.exists(examples_dir):
            example_count = len(
                [
                    f
                    for f in os.listdir(examples_dir)
                    if os.path.isdir(os.path.join(examples_dir, f))
                ]
            )
            if example_count > 0:
                print(f"    ✅ Found {example_count}  examples")
            else:
                print(f"    ⚠️  Example directory is empty")
        else:
            print(f"    ❌ Missing example directory: {examples_dir}")
            all_good = False

        missing_files = []
        for file_path in required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)

        if missing_files:
            print(f"    ❌ Missing files: {missing_files}")
            all_good = False
        else:
            print(f"    ✅ {lang.upper()}  path complete")

    return all_good


def test_content_quality():
    """Test content quality"""
    print("📝 Test content quality...")

    # Check content length of core documents
    core_docs = {
        "docs/quickstart/first-session.md": 1000,  # At least 1000 characters
        "docs/guides/session-management.md": 2000,  # At least 2000 characters
        "docs/guides/automation.md": 1500,  # At least 1500 characters
        "docs/guides/data-persistence.md": 2000,  # At least 2000 characters
        "docs/guides/advanced-features.md": 2000,  # At least 2000 characters
    }

    all_good = True
    for doc_path, min_length in core_docs.items():
        if os.path.exists(doc_path):
            with open(doc_path, "r", encoding="utf-8") as f:
                content = f.read()
                if len(content) >= min_length:
                    print(
                        f"  ✅ {doc_path}  content is substantial ({len(content)}  characters)"
                    )
                else:
                    print(
                        f"  ⚠️  {doc_path}  content is limited ({len(content)}  characters, recommend at least  {min_length})"
                    )
        else:
            print(f"  ❌ Document does not exist: {doc_path}")
            all_good = False

    return all_good


def test_navigation_consistency():
    """Test navigation consistency"""
    print("🧭 Test navigation consistency...")

    # Check if main README files have user flow
    readme_files = [
        "README.md",
        "python/README.md",
        "typescript/README.md",
        "golang/README.md",
    ]

    all_good = True
    for readme in readme_files:
        if os.path.exists(readme):
            with open(readme, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if contains user flow keywords
            user_flow_keywords = [
                "newbie users",
                "experienced users",
                "choose your learning path",
            ]
            has_user_flow = any(keyword in content for keyword in user_flow_keywords)

            if has_user_flow:
                print(f"  ✅ {readme}  contains user flow")
            else:
                print(f"  ⚠️  {readme}  lacks user flow")
                all_good = False
        else:
            print(f"  ❌ README does not exist: {readme}")
            all_good = False

    return all_good


def main():
    """Main function"""
    print("🧪 Starting user experience test...")
    print(f"Project root directory: {os.getcwd()}")
    print()

    # Execute various tests
    tests = [
        ("Newbie user path", test_newbie_user_path),
        ("Experienced user path", test_experienced_user_path),
        ("Package installation user path", test_package_user_path),
        ("Content quality", test_content_quality),
        ("Navigation consistency", test_navigation_consistency),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        result = test_func()
        results.append((test_name, result))
        print()

    # Summary results
    print("=" * 50)
    print("📊 Test results summary:")
    print()

    passed = 0
    for test_name, result in results:
        status = "✅ Pass" if result else "❌ Fail"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1

    print()
    print(
        f"Overall pass rate: {passed}/{len(results)} ({passed/len(results)*100:.1f}%)"
    )

    if passed == len(results):
        print("\n🎉 All tests passed! Documentation user experience is good.")
        return 0
    else:
        print(f"\n⚠️  {len(results)-passed} tests failed, need improvement.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
