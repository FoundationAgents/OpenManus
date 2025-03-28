import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect
from watchfiles import Change, awatch

from app.apis.models.file import FileInfo
from app.apis.services.workspace import get_file_info, get_workspace_path, is_safe_path


class FileSystemMonitor:
    def __init__(self):
        self.dir_connections: Dict[str, Set[WebSocket]] = (
            {}
        )  # path -> set of websockets
        self.file_connections: Dict[str, Set[WebSocket]] = (
            {}
        )  # path -> set of websockets
        self.monitor_tasks: Dict[str, asyncio.Task] = {}  # path -> monitor task

    async def connect_dir(self, websocket: WebSocket, dir_path: str):
        """Connect to monitor a directory"""
        await websocket.accept()

        # Convert to absolute path
        workspace_path = get_workspace_path()
        abs_path = (workspace_path / dir_path).resolve()

        # Security check
        if not is_safe_path(workspace_path, abs_path):
            await websocket.close(code=4003, reason="Access denied")
            return

        if not abs_path.is_dir():
            await websocket.close(code=4004, reason="Not a directory")
            return

        # Add to connections
        if dir_path not in self.dir_connections:
            self.dir_connections[dir_path] = set()
        self.dir_connections[dir_path].add(websocket)

        # Start monitoring if not already monitoring this directory
        if dir_path not in self.monitor_tasks:
            self.monitor_tasks[dir_path] = asyncio.create_task(
                self.monitor_directory(dir_path)
            )

    async def connect_file(self, websocket: WebSocket, file_path: str):
        """Connect to monitor a single file"""
        await websocket.accept()

        # Convert to absolute path
        workspace_path = get_workspace_path()
        abs_path = (workspace_path / file_path).resolve()

        # Security check
        if not is_safe_path(workspace_path, abs_path):
            await websocket.close(code=4003, reason="Access denied")
            return

        if not abs_path.is_file():
            await websocket.close(code=4004, reason="Not a file")
            return

        # Add to connections
        if file_path not in self.file_connections:
            self.file_connections[file_path] = set()
        self.file_connections[file_path].add(websocket)

        # Start monitoring if not already monitoring this file
        if file_path not in self.monitor_tasks:
            self.monitor_tasks[file_path] = asyncio.create_task(
                self.monitor_file(file_path)
            )

    def disconnect(self, websocket: WebSocket, path: str = None):
        """Disconnect from monitoring"""
        # Remove from directory connections
        for dir_path, connections in list(self.dir_connections.items()):
            if websocket in connections:
                connections.remove(websocket)
                if not connections:
                    # No more connections for this directory
                    self.dir_connections.pop(dir_path)
                    if dir_path in self.monitor_tasks:
                        self.monitor_tasks[dir_path].cancel()
                        self.monitor_tasks.pop(dir_path)

        # Remove from file connections
        for file_path, connections in list(self.file_connections.items()):
            if websocket in connections:
                connections.remove(websocket)
                if not connections:
                    # No more connections for this file
                    self.file_connections.pop(file_path)
                    if file_path in self.monitor_tasks:
                        self.monitor_tasks[file_path].cancel()
                        self.monitor_tasks.pop(file_path)

    async def broadcast_to_dir(self, dir_path: str, message: dict):
        """Broadcast message to all connections monitoring a directory"""
        if dir_path not in self.dir_connections:
            return

        dead_connections = set()
        for connection in self.dir_connections[dir_path]:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                dead_connections.add(connection)
            except Exception as e:
                print(f"Error broadcasting to connection: {e}")
                dead_connections.add(connection)

        # Clean up dead connections
        for dead in dead_connections:
            self.disconnect(dead, dir_path)

    async def broadcast_to_file(self, file_path: str, message: dict):
        """Broadcast message to all connections monitoring a file"""
        if file_path not in self.file_connections:
            return

        dead_connections = set()
        for connection in self.file_connections[file_path]:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                dead_connections.add(connection)
            except Exception as e:
                print(f"Error broadcasting to connection: {e}")
                dead_connections.add(connection)

        # Clean up dead connections
        for dead in dead_connections:
            self.disconnect(dead, file_path)

    async def monitor_directory(self, dir_path: str):
        """Monitor directory for changes"""
        workspace_path = get_workspace_path()
        target_path = workspace_path / dir_path

        try:
            async for changes in awatch(target_path):
                for change_type, file_path in changes:
                    try:
                        relative_path = Path(file_path).relative_to(workspace_path)
                        # Skip hidden files and directories
                        if any(part.startswith(".") for part in relative_path.parts):
                            continue

                        change_info = {
                            "type": change_type.name,  # ADDED, MODIFIED, DELETED
                            "path": str(relative_path),
                            "timestamp": datetime.now().isoformat(),
                            "event_type": "directory_change",
                        }

                        # If file still exists, add its information
                        if change_type != Change.deleted and Path(file_path).exists():
                            try:
                                file_info = get_file_info(Path(file_path))
                                change_info["file"] = file_info.model_dump()
                            except Exception as e:
                                print(f"Error getting file info: {e}")

                        await self.broadcast_to_dir(dir_path, change_info)
                    except Exception as e:
                        print(f"Error processing directory change: {e}")

        except asyncio.CancelledError:
            print(f"Directory monitoring stopped for {dir_path}")
        except Exception as e:
            print(f"Error in directory monitor: {e}")
            # Try to restart monitoring if still has connections
            if dir_path in self.dir_connections and self.dir_connections[dir_path]:
                self.monitor_tasks[dir_path] = asyncio.create_task(
                    self.monitor_directory(dir_path)
                )

    async def monitor_file(self, file_path: str):
        """Monitor single file for changes"""
        workspace_path = get_workspace_path()
        target_path = workspace_path / file_path

        try:
            last_content = target_path.read_text() if target_path.exists() else ""
            last_mtime = target_path.stat().st_mtime if target_path.exists() else 0

            async for changes in awatch(target_path.parent):
                for change_type, changed_path in changes:
                    try:
                        if Path(changed_path) == target_path:
                            if not target_path.exists():
                                change_info = {
                                    "type": "DELETED",
                                    "path": file_path,
                                    "timestamp": datetime.now().isoformat(),
                                    "event_type": "file_change",
                                }
                                await self.broadcast_to_file(file_path, change_info)
                                continue

                            current_mtime = target_path.stat().st_mtime
                            if current_mtime != last_mtime:
                                current_content = target_path.read_text()
                                if current_content != last_content:
                                    change_info = {
                                        "type": "MODIFIED",
                                        "path": file_path,
                                        "timestamp": datetime.now().isoformat(),
                                        "event_type": "file_change",
                                        "content": current_content,
                                    }
                                    await self.broadcast_to_file(file_path, change_info)
                                    last_content = current_content
                                last_mtime = current_mtime

                    except Exception as e:
                        print(f"Error processing file change: {e}")

        except asyncio.CancelledError:
            print(f"File monitoring stopped for {file_path}")
        except Exception as e:
            print(f"Error in file monitor: {e}")
            # Try to restart monitoring if still has connections
            if file_path in self.file_connections and self.file_connections[file_path]:
                self.monitor_tasks[file_path] = asyncio.create_task(
                    self.monitor_file(file_path)
                )


file_monitor = FileSystemMonitor()
