import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from fastapi import HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.apis.models.file import FileInfo


def get_workspace_path() -> Path:
    """Get the workspace root path from environment variable or current working directory"""
    return Path(os.getenv("WORKSPACE_PATH", os.getcwd()))


def is_safe_path(base_path: Path, requested_path: Path) -> bool:
    """
    Check if the requested path is within the workspace boundary

    Args:
        base_path: The workspace root path
        requested_path: The path to be checked

    Returns:
        bool: True if the path is safe to access, False otherwise
    """
    try:
        requested_path.relative_to(base_path)
        return True
    except ValueError:
        return False


def get_file_info(path: Path, depth: int = 0, max_depth: int = 0) -> FileInfo:
    """
    Get file information for the given path with optional recursive directory scanning

    Args:
        path: Path to the file or directory
        depth: Current depth in the directory tree
        max_depth: Maximum depth to scan (-1 for unlimited, 0 for current level only)

    Returns:
        FileInfo: Object containing file metadata and optional children
    """
    stat = path.stat()
    workspace_path = get_workspace_path()

    try:
        relative_path = str(path.relative_to(workspace_path))
    except ValueError:
        relative_path = str(path)

    parent_path = (
        str(path.parent.relative_to(workspace_path))
        if path.parent != workspace_path
        else ""
    )

    file_info = FileInfo(
        name=path.name,
        path=relative_path,
        size=stat.st_size,
        is_dir=path.is_dir(),
        modified_time=datetime.fromtimestamp(stat.st_mtime),
        parent_path=parent_path,
        depth=depth,
    )

    # If it's a directory and we haven't reached max_depth, scan its contents
    if path.is_dir() and (max_depth == -1 or depth < max_depth):
        try:
            children = []
            for item in sorted(
                path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
            ):
                if item.name.startswith("."):
                    continue
                child_info = get_file_info(item, depth + 1, max_depth)
                children.append(child_info)
            file_info.children = children
        except PermissionError:
            pass

    return file_info


async def list_workspace_files(
    path: str = "", depth: int = 1, flat: bool = False
) -> Union[List[Dict], Dict]:
    """
    List files and directories in the workspace with optional recursive scanning

    Args:
        path: Relative path within the workspace (optional)
        depth: Maximum depth to scan (-1 for unlimited, 0 for current level only)
        flat: If True, returns a flat list instead of a tree structure

    Returns:
        Union[List[Dict], Dict]: List of file and directory information or tree structure

    Raises:
        HTTPException: If path is not found or access is denied
    """
    workspace_path = get_workspace_path()
    target_path = workspace_path / path

    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Path not found")

    if not is_safe_path(workspace_path, target_path):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        if flat:
            # Return flat list of all files and directories
            files = []
            for item in sorted(
                target_path.rglob("*"), key=lambda x: (not x.is_dir(), x.name.lower())
            ):
                if item.name.startswith("."):
                    continue
                try:
                    current_depth = len(item.relative_to(target_path).parts)
                    if depth == -1 or current_depth <= depth:
                        files.append(get_file_info(item, current_depth, 0).model_dump())
                except ValueError:
                    continue
            return files
        else:
            # Return tree structure
            return get_file_info(target_path, 0, depth).model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_file_content(path: str):
    """
    Get the content of a file in the workspace

    Args:
        path: Relative path to the file within the workspace

    Returns:
        FileResponse: File content with appropriate headers

    Raises:
        HTTPException: If file is not found, is a directory, or access is denied
    """
    workspace_path = get_workspace_path()
    target_path = workspace_path / path

    if not target_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not is_safe_path(workspace_path, target_path):
        raise HTTPException(status_code=403, detail="Access denied")

    if target_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is a directory")

    try:
        return FileResponse(target_path, filename=target_path.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_workspace_info():
    """
    Get information about the workspace

    Returns:
        dict: Workspace path and status information
    """
    workspace_path = get_workspace_path()
    return {
        "path": str(workspace_path),
        "exists": workspace_path.exists(),
        "is_dir": workspace_path.is_dir() if workspace_path.exists() else None,
    }
