import os


# Files to exclude from operations
EXCLUDED_FILES = {
    ".DS_Store",
    ".gitignore",
    "package-lock.json",
    "postcss.config.js",
    "postcss.config.mjs",
    "jsconfig.json",
    "components.json",
    "tsconfig.tsbuildinfo",
    "tsconfig.json",
}

# Directories to exclude from operations
EXCLUDED_DIRS = {"node_modules", ".next", "dist", "build", ".git"}

# File extensions to exclude from operations
EXCLUDED_EXT = {
    ".ico",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tiff",
    ".webp",
    ".db",
    ".sql",
}


def should_exclude_file(rel_path: str) -> bool:
    """Check if a file should be excluded based on path, name, or extension

    Args:
        rel_path: Relative path of the file to check

    Returns:
        True if the file should be excluded, False otherwise
    """
    # Check filename
    filename = os.path.basename(rel_path)
    if filename in EXCLUDED_FILES:
        return True

    # Check directory
    dir_path = os.path.dirname(rel_path)
    if any(excluded in dir_path for excluded in EXCLUDED_DIRS):
        return True

    # Check extension
    _, ext = os.path.splitext(filename)
    if ext.lower() in EXCLUDED_EXT:
        return True

    return False


def clean_path(path: str, workspace_path: str = "/workspace") -> str:
    """Clean and normalize a path to be relative to the workspace

    Args:
        path: The path to clean
        workspace_path: The base workspace path to remove (default: "/workspace")

    Returns:
        The cleaned path, relative to the workspace
    """
    # Remove any leading slash
    path = path.lstrip("/")

    # Remove workspace prefix if present
    if path.startswith(workspace_path.lstrip("/")):
        path = path[len(workspace_path.lstrip("/")) :]

    # Remove workspace/ prefix if present
    if path.startswith("workspace/"):
        path = path[9:]

    # Remove any remaining leading slash
    path = path.lstrip("/")

    return path
