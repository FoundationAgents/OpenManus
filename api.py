import asyncio
import base64
import os
import shutil
import tempfile
import threading
import tomllib
import uuid
import webbrowser
from datetime import datetime
from functools import partial
from json import dumps
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, cast

from fastapi import (
    Body,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from playwright.async_api import async_playwright
from pydantic import BaseModel
from watchfiles import Change, awatch

from app.config import LLMSettings
from app.tool.browser_use_tool import BrowserUseTool

AGENT_NAME = "Manus"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Task(BaseModel):
    id: str
    prompt: str
    created_at: datetime
    status: str
    steps: list = []
    agent: "Manus"

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        data["created_at"] = self.created_at.isoformat()
        return data


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.queues: Dict[str, asyncio.Queue] = {}

    def create_task(self, prompt: str, agent: "Manus") -> Task:
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            prompt=prompt,
            created_at=datetime.now(),
            status="pending",
            agent=agent,
        )
        self.tasks[task_id] = task
        self.queues[task_id] = asyncio.Queue()
        return task

    async def update_task_step(
        self, task_id: str, step: int, result: str, step_type: str = "step"
    ):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.steps.append({"step": step, "result": result, "type": step_type})
            await self.queues[task_id].put(
                {"type": step_type, "step": step, "result": result}
            )
            await self.queues[task_id].put(
                {"type": "status", "status": task.status, "steps": task.steps}
            )

    async def complete_task(self, task_id: str):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = "completed"
            await self.queues[task_id].put(
                {"type": "status", "status": task.status, "steps": task.steps}
            )
            await self.queues[task_id].put({"type": "complete"})

    async def fail_task(self, task_id: str, error: str):
        if task_id in self.tasks:
            self.tasks[task_id].status = f"failed: {error}"
            await self.queues[task_id].put({"type": "error", "message": error})


task_manager = TaskManager()


@app.get("/download")
async def download_file(file_path: str):
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, filename=os.path.basename(file_path))


@app.post("/tasks")
async def create_task(
    prompt: str = Body(..., embed=True),
    llm_config: Optional[LLMSettings] = Body(None, embed=True),
):
    print(f"Creating task with prompt: {prompt}")
    task = task_manager.create_task(
        prompt,
        Manus(
            name=AGENT_NAME,
            description="A versatile agent that can solve various tasks using multiple tools",
            llm=llm_config,
        ),
    )
    print("http://localhost:5172/ws/" + task.id)
    asyncio.create_task(run_task(task.id, prompt, llm_config))
    return {"task_id": task.id}


from app.agent.manus import Manus


async def run_task(task_id: str, prompt: str, llm_config: Optional[LLMSettings] = None):
    try:
        task_manager.tasks[task_id].status = "running"
        agent = cast(Manus, task_manager.tasks[task_id].agent)

        async def on_think(thought):
            await task_manager.update_task_step(task_id, 0, thought, "think")

        async def on_tool_execute(tool, input):
            await task_manager.update_task_step(
                task_id, 0, f"Executing tool: {tool}\nInput: {input}", "tool"
            )

        async def on_action(action):
            await task_manager.update_task_step(
                task_id, 0, f"Executing action: {action}", "act"
            )

        async def on_run(step, result):
            await task_manager.update_task_step(task_id, step, result, "run")

        from app.logger import logger

        class SSELogHandler:
            step: int = 0

            def __init__(self, task_id):
                self.task_id = task_id

            async def __call__(self, message):
                import re

                # Extract - Subsequent Content
                cleaned_message = re.sub(r"^.*? - ", "", message)

                # default event type
                event_type = "log"

                # think
                if f"✨ {AGENT_NAME}'s thoughts:" in cleaned_message:
                    event_type = "think"
                # step progress
                elif "Executing step" in cleaned_message:
                    event_type = "step"
                    self.step = int(
                        re.search(r"Executing step (\d+)/", cleaned_message).group(1)
                        or self.step
                    )
                # error
                elif "📝 Oops!" in cleaned_message:
                    event_type = "error"
                # complete [🏁 Special tool 'terminate' has completed the task!]
                elif "has completed the task" in cleaned_message:
                    event_type = "complete"

                # tool related
                # tool selected
                elif f"🛠️ {AGENT_NAME} selected" in cleaned_message:
                    event_type = "tool:selected"
                # tool prepared
                elif "🧰 Tools being prepared" in cleaned_message:
                    event_type = "tool:prepared"
                # tool arguments
                elif "🔧 Tool arguments" in cleaned_message:
                    event_type = "tool:arguments"
                # tool activiting
                elif "🔧 Activating tool" in cleaned_message:
                    event_type = "tool:activating"
                # tool completed
                elif "🎯 Tool" in cleaned_message:
                    event_type = "tool:completed"
                elif "Token usage" in cleaned_message:
                    event_type = "token-usage"

                await task_manager.update_task_step(
                    self.task_id, self.step, cleaned_message, event_type
                )

        sse_handler = SSELogHandler(task_id)
        logger.add(sse_handler)

        result = await agent.run(prompt)
        # Wait for all logs to be processed
        await asyncio.sleep(0.1)
        await task_manager.complete_task(task_id)
        await task_manager.update_task_step(
            task_id, agent.current_step, result, "result"
        )
    except Exception as e:
        await task_manager.fail_task(task_id, str(e))


@app.get("/tasks/{task_id}/events")
async def task_events(task_id: str):
    async def event_generator():
        if task_id not in task_manager.queues:
            yield f"event: error\ndata: {dumps({'message': 'Task not found'})}\n\n"
            return

        queue = task_manager.queues[task_id]

        task = task_manager.tasks.get(task_id)
        if task:
            yield f"event: status\ndata: {dumps({'type': 'status', 'status': task.status, 'steps': task.steps})}\n\n"

        while True:
            try:
                event = await queue.get()
                formatted_event = dumps(event)

                yield ": heartbeat\n\n"

                if event.get("type") == "complete":
                    yield f"event: {event.get('type')}\ndata: {formatted_event}\n\n"
                    break
                elif event.get("type") == "error":
                    yield f"event: {event.get('type')}\ndata: {formatted_event}\n\n"
                    break
                elif event.get("type") == "step":
                    task = task_manager.tasks.get(task_id)
                    if task:
                        yield f"event: status\ndata: {dumps({'type': 'status', 'status': task.status, 'steps': task.steps})}\n\n"
                    yield f"event: {event.get('type')}\ndata: {formatted_event}\n\n"
                else:
                    yield f"event: {event.get('type')}\ndata: {formatted_event}\n\n"

            except asyncio.CancelledError:
                print(f"Client disconnected for task {task_id}")
                break
            except Exception as e:
                print(f"Error in event stream: {str(e)}")
                yield f"event: error\ndata: {dumps({'message': str(e)})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def format_event(event: dict) -> str:
    return f"event: {event.get('type')}\ndata: {dumps(event)}\n\n"


@app.get("/tasks")
async def get_tasks():
    sorted_tasks = sorted(
        task_manager.tasks.values(), key=lambda task: task.created_at, reverse=True
    )
    return JSONResponse(
        content=[task.model_dump() for task in sorted_tasks],
        headers={"Content-Type": "application/json"},
    )


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    if task_id not in task_manager.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_manager.tasks[task_id]


@app.get("/config/status")
async def check_config_status():
    config_path = Path(__file__).parent / "config" / "config.toml"
    example_config_path = Path(__file__).parent / "config" / "config.example.toml"

    if config_path.exists():
        return {"status": "exists"}
    elif example_config_path.exists():
        try:
            with open(example_config_path, "rb") as f:
                example_config = tomllib.load(f)
            return {"status": "missing", "example_config": example_config}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    else:
        return {"status": "no_example"}


@app.post("/config/save")
async def save_config(config_data: dict = Body(...)):
    try:
        config_dir = Path(__file__).parent / "config"
        config_dir.mkdir(exist_ok=True)

        config_path = config_dir / "config.toml"

        toml_content = ""

        if "llm" in config_data:
            toml_content += "# Global LLM configuration\n[llm]\n"
            llm_config = config_data["llm"]
            for key, value in llm_config.items():
                if key != "vision":
                    if isinstance(value, str):
                        toml_content += f'{key} = "{value}"\n'
                    else:
                        toml_content += f"{key} = {value}\n"

        if "server" in config_data:
            toml_content += "\n# Server configuration\n[server]\n"
            server_config = config_data["server"]
            for key, value in server_config.items():
                if isinstance(value, str):
                    toml_content += f'{key} = "{value}"\n'
                else:
                    toml_content += f"{key} = {value}\n"

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(toml_content)

        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500, content={"message": f"Server error: {str(exc)}"}
    )


def open_local_browser(config):
    webbrowser.open_new_tab(
        f"http://{config.get('host', 'localhost')}:{config.get('port', 5172)}"
    )


def load_config():
    try:
        config_path = Path(__file__).parent / "config" / "config.toml"

        if not config_path.exists():
            return {"host": "localhost", "port": 5172}

        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        return {"host": config["server"]["host"], "port": config["server"]["port"]}
    except FileNotFoundError:
        return {"host": "localhost", "port": 5172}
    except KeyError as e:
        print(
            f"The configuration file is missing necessary fields: {str(e)}, use default configuration"
        )
        return {"host": "localhost", "port": 5172}


# File operation related models
class FileInfo(BaseModel):
    name: str
    path: str
    size: int
    is_dir: bool
    modified_time: datetime
    children: Optional[List["FileInfo"]] = None
    parent_path: Optional[str] = None
    depth: int = 0

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        data["modified_time"] = self.modified_time.isoformat()
        return data


# Workspace utility functions
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


# API endpoints for file operations
@app.get("/workspace/files")
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


@app.get("/workspace/file")
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


@app.get("/workspace/info")
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


# File system monitoring
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


@app.websocket("/workspace/watch/dir")
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


@app.websocket("/workspace/watch/file")
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


@app.get("/workspace/download/directory")
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
    workspace_path = get_workspace_path()
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


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()

    agent = cast(Manus, task_manager.tasks[task_id].agent)

    browser_use_tool = cast(
        BrowserUseTool, agent.available_tools.get_tool("browser_use")
    )
    page = browser_use_tool.dom_service.page
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")

    try:
        while True:

            content = await page.screenshot(full_page=True)
            await websocket.send_bytes(content)

            await asyncio.sleep(1)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import uvicorn

    config = load_config()
    open_with_config = partial(open_local_browser, config)
    threading.Timer(3, open_with_config).start()
    uvicorn.run(app, host=config["host"], port=config["port"])
