#!/usr/bin/env python3
"""
Documentation Link Validation Script
Check if all internal links in markdown files are valid
"""

import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, urljoin


def find_markdown_files(base_path):
    """Find all markdown files"""
    markdown_files = []
    for root, dirs, files in os.walk(base_path):
        # Skip hidden directories and node_modules etc
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules"]

        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)
                markdown_files.append(filepath)

    return markdown_files


def extract_links(content):
    """Extract all links from markdown files"""
    # Match format links
    link_pattern = r"\[([^\]]*)\]\(([^)]+)\)"
    links = re.findall(link_pattern, content)
    return [(text, link) for text, link in links]


def is_internal_link(link):
    """Determine if it is an internal link"""
    parsed = urlparse(link)
    # If has scheme (http/https) then it is external link
    if parsed.scheme:
        return False
    # If starts with # then it is anchor link
    if link.startswith("#"):
        return False
    return True


def resolve_link_path(base_file, link):
    """Parse absolute path of link"""
    base_dir = os.path.dirname(base_file)

    # Handle anchor
    if "#" in link:
        link = link.split("#")[0]

    # If link is empty (pure anchor), then points to current file
    if not link:
        return base_file

    # Parse relative path
    if link.startswith("/"):
        # Absolute path (relative to project root)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        target_path = os.path.join(project_root, link.lstrip("/"))
    else:
        # Relative path
        target_path = os.path.join(base_dir, link)

    # Normalize path
    target_path = os.path.normpath(target_path)

    # If it is a directory, try to find README.md
    if os.path.isdir(target_path):
        readme_path = os.path.join(target_path, "README.md")
        if os.path.exists(readme_path):
            return readme_path

    return target_path


def validate_internal_links(base_path):
    """Validate internal links"""
    errors = []
    markdown_files = find_markdown_files(base_path)

    print(f"Check markdown files...")

    for filepath in markdown_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            errors.append(f"{filepath}: Unable to read file - {e}")
            continue

        links = extract_links(content)

        for text, link in links:
            if is_internal_link(link):
                target_path = resolve_link_path(filepath, link)

                if not os.path.exists(target_path):
                    relative_filepath = os.path.relpath(filepath, base_path)
                    errors.append(
                        f"{relative_filepath}: Link does not exist [{text}]({link}) -> {target_path}"
                    )

    return errors


def check_github_links():
    """Check if GitHub link format is correct"""
    errors = []
    expected_repo = "https://github.com/aliyun/wuying-agentbay-sdk"

    # Check GitHub links in main README files
    readme_files = [
        "README.md",
        "python/README.md",
        "typescript/README.md",
        "golang/README.md",
    ]

    for readme_file in readme_files:
        if os.path.exists(readme_file):
            try:
                with open(readme_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Find GitHub links
                github_links = re.findall(r"https://github\.com/[^)\s]+", content)

                for link in github_links:
                    if not link.startswith(expected_repo):
                        errors.append(
                            f"{readme_file}: GitHub link may be incorrect - {link}"
                        )

            except Exception as e:
                errors.append(f"{readme_file}: Unable to check GitHub links - {e}")

    return errors


def main():
    """Main function"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print("🔍 Start validating document links...")
    print(f"Project root directory: {base_path}")
    print()

    # Validate internal links
    print("📋 Validate internal links...")
    internal_errors = validate_internal_links(base_path)

    # Validate GitHub links
    print("🔗 Validating GitHub links...")
    github_errors = check_github_links()

    # Summary results
    all_errors = internal_errors + github_errors

    if all_errors:
        print(f"\n❌ Found link issues:")
        for error in all_errors:
            print(f"  - {error}")
        return 1
    else:
        print("\n✅ All links validation passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
