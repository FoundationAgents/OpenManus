import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

from app.apis.services.file_monitor import file_monitor
from app.apis.services.workspace import (
    get_file_content,
    get_workspace_info,
    is_safe_path,
    list_workspace_files,
)

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("/files")
async def list_files(path: str = "", depth: int = 1, flat: bool = False):
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
    return await list_workspace_files(path, depth, flat)


@router.get("/file")
async def get_file(path: str):
    """
    Get the content of a file in the workspace

    Args:
        path: Relative path to the file within the workspace

    Returns:
        FileResponse: File content with appropriate headers

    Raises:
        HTTPException: If file is not found, is a directory, or access is denied
    """
    return await get_file_content(path)


@router.get("/info")
async def get_info():
    """
    Get information about the workspace

    Returns:
        dict: Workspace path and status information
    """
    return await get_workspace_info()


@router.websocket("/watch/dir")
async def watch_directory(websocket: WebSocket, path: str = ""):
    """
    WebSocket endpoint for monitoring directory changes

    Args:
        path: Relative path to the directory to monitor

    Messages format:
    {
        "type": "ADDED" | "MODIFIED" | "DELETED",
        "path": "relative/path/to/file",
        "timestamp": "2024-03-25T10:30:00",
        "event_type": "directory_change",
        "file": FileInfo  # Only for ADDED and MODIFIED events
    }
    """
    await file_monitor.connect_dir(websocket, path)
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        file_monitor.disconnect(websocket, path)
    except Exception as e:
        print(f"WebSocket error: {e}")
        file_monitor.disconnect(websocket, path)


@router.websocket("/watch/file")
async def watch_file(websocket: WebSocket, path: str):
    """
    WebSocket endpoint for monitoring single file changes

    Args:
        path: Relative path to the file to monitor

    Messages format:
    {
        "type": "MODIFIED" | "DELETED",
        "path": "relative/path/to/file",
        "timestamp": "2024-03-25T10:30:00",
        "event_type": "file_change",
        "content": "file content"  # Only for MODIFIED events
    }
    """
    await file_monitor.connect_file(websocket, path)
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        file_monitor.disconnect(websocket, path)
    except Exception as e:
        print(f"WebSocket error: {e}")
        file_monitor.disconnect(websocket, path)


@router.get("/download/directory")
async def download_directory(path: str = ""):
    """
    Download a directory as a zip file

    Args:
        path: Relative path to the directory within the workspace

    Returns:
        FileResponse: Zip file containing the directory contents

    Raises:
        HTTPException: If directory is not found or access is denied
    """
    workspace_path = Path(os.getenv("WORKSPACE_PATH", os.getcwd()))
    target_path = workspace_path / path

    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Directory not found")

    if not is_safe_path(workspace_path, target_path):
        raise HTTPException(status_code=403, detail="Access denied")

    if not target_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    try:
        # Create a temporary directory for the zip file
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate zip file name based on directory name
            zip_name = (
                f"{target_path.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            )
            zip_path = Path(temp_dir) / zip_name

            # Create zip file
            shutil.make_archive(
                str(zip_path.with_suffix("")),  # Remove .zip as make_archive adds it
                "zip",
                target_path,
            )

            return FileResponse(
                zip_path,
                filename=zip_name,
                media_type="application/zip",
                headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating zip file: {str(e)}"
        )
