"""
Daytona-backed sandbox provider implementation.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import mimetypes
import time
from typing import Any, Dict, Optional, Sequence, Tuple
from uuid import uuid4

from PIL import Image

from app.config import Config, SandboxSettings
from app.daytona.sandbox import SessionExecuteRequest, create_sandbox, delete_sandbox
from app.utils.logger import logger

from .base import (
    BrowserService,
    FileService,
    SandboxMetadata,
    SandboxProvider,
    ShellCommandResult,
    ShellService,
    VisionService,
)


class DaytonaShellService(ShellService):
    """Shell service implementation backed by Daytona sandbox tmux sessions."""

    def __init__(self, sandbox):
        self._sandbox = sandbox
        self.workspace_path = "/workspace"
        self._sessions: dict[str, str] = {}

    async def _ensure_session(self, session_name: str) -> str:
        """Ensure tmux session exists and return underlying session id."""
        if session_name in self._sessions:
            return self._sessions[session_name]

        session_id = str(uuid4())
        self._sandbox.process.create_session(session_id)
        self._sessions[session_name] = session_id
        return session_id

    async def _execute_raw_command(self, command: str) -> Tuple[str, int]:
        """Execute command directly within the sandbox control session."""
        session_id = await self._ensure_session("_raw")
        req = SessionExecuteRequest(
            command=command,
            run_async=False,
            cwd=self.workspace_path,
        )
        response = self._sandbox.process.execute_session_command(
            session_id=session_id, req=req, timeout=30
        )
        logs = self._sandbox.process.get_session_command_logs(
            session_id=session_id, command_id=response.cmd_id
        )
        return logs, getattr(response, "exit_code", 0)

    async def _kill_tmux_session(self, session_name: str) -> None:
        try:
            await self._execute_raw_command(f"tmux kill-session -t {session_name}")
        except Exception:
            logger.debug(f"Unable to kill tmux session {session_name}", exc_info=True)
        self._sessions.pop(session_name, None)

    def _default_session(self, supplied: Optional[str]) -> str:
        return supplied or f"session_{uuid4().hex[:8]}"

    async def execute(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        blocking: bool = False,
        session: Optional[str] = None,
    ) -> ShellCommandResult:
        session_name = self._default_session(session)
        working_dir = self.workspace_path
        if cwd:
            working_dir = f"{self.workspace_path}/{cwd.strip('/')}"

        try:
            await self._ensure_session(session_name)
        except Exception as exc:
            return ShellCommandResult(
                success=False,
                error=f"Failed to create tmux session {session_name}: {exc}",
            )

        # Create tmux session if not exists
        try:
            result, _ = await self._execute_raw_command(
                f"tmux has-session -t {session_name} 2>/dev/null || echo 'not_exists'"
            )
            if "not_exists" in result:
                await self._execute_raw_command(
                    f"tmux new-session -d -s {session_name}"
                )
        except Exception as exc:
            return ShellCommandResult(
                success=False,
                error=f"Failed to prepare tmux session {session_name}: {exc}",
            )

        escaped_command = f"cd {working_dir} && {command}".replace('"', '\\"')
        try:
            await self._execute_raw_command(
                f'tmux send-keys -t {session_name} "{escaped_command}" Enter'
            )
        except Exception as exc:
            return ShellCommandResult(
                success=False,
                error=f"Failed to dispatch command to tmux: {exc}",
            )

        if not blocking:
            return ShellCommandResult(
                success=True,
                output=(
                    f"Command sent to session '{session_name}'. "
                    "Use check to retrieve output."
                ),
                session_name=session_name,
                completed=False,
                metadata={"cwd": working_dir},
            )

        timeout_s = timeout or 60
        start_time = time.time()
        while time.time() - start_time < timeout_s:
            await asyncio.sleep(2)
            result, _ = await self._execute_raw_command(
                f"tmux has-session -t {session_name} 2>/dev/null || echo 'not_exists'"
            )
            if "not_exists" in result:
                break

        output, _ = await self._execute_raw_command(
            f"tmux capture-pane -t {session_name} -p -S - -E -"
        )
        await self._kill_tmux_session(session_name)

        return ShellCommandResult(
            success=True,
            output=output,
            session_name=session_name,
            completed=True,
            metadata={"cwd": working_dir},
        )

    async def check(self, session: str) -> ShellCommandResult:
        try:
            exists_output, _ = await self._execute_raw_command(
                f"tmux has-session -t {session} 2>/dev/null || echo 'not_exists'"
            )
            if "not_exists" in exists_output:
                return ShellCommandResult(
                    success=False,
                    error=f"Session '{session}' not found.",
                    session_name=session,
                )

            output, _ = await self._execute_raw_command(
                f"tmux capture-pane -t {session} -p -S - -E -"
            )
            return ShellCommandResult(
                success=True, output=output, session_name=session, completed=False
            )
        except Exception as exc:
            return ShellCommandResult(
                success=False,
                error=f"Failed to read session '{session}': {exc}",
                session_name=session,
            )

    async def terminate(self, session: str) -> ShellCommandResult:
        try:
            await self._kill_tmux_session(session)
            return ShellCommandResult(
                success=True,
                output=f"Session '{session}' terminated.",
                session_name=session,
                completed=True,
            )
        except Exception as exc:
            return ShellCommandResult(
                success=False,
                error=f"Failed to terminate session '{session}': {exc}",
                session_name=session,
            )

    async def list_sessions(self) -> Sequence[str]:
        try:
            output, _ = await self._execute_raw_command(
                "tmux list-sessions 2>/dev/null || echo 'No sessions'"
            )
            if "No sessions" in output:
                return []
            sessions = []
            for line in output.splitlines():
                if ":" in line:
                    sessions.append(line.split(":", 1)[0].strip())
            return sessions
        except Exception:
            logger.debug("Failed to list tmux sessions", exc_info=True)
            return []

    async def cleanup(self) -> None:
        for session in list(self._sessions.keys()):
            await self._kill_tmux_session(session)
        try:
            await self._execute_raw_command("tmux kill-server 2>/dev/null || true")
        except Exception:
            logger.debug("Failed to kill tmux server during cleanup", exc_info=True)


class DaytonaFileService(FileService):
    """File management service for Daytona sandbox."""

    def __init__(self, sandbox):
        self._sandbox = sandbox
        self.workspace_path = "/workspace"

    def _resolve(self, path: str) -> str:
        if path.startswith("/"):
            return path
        return f"{self.workspace_path}/{path}".rstrip("/")

    async def read(self, path: str) -> str:
        full_path = self._resolve(path)
        content = self._sandbox.fs.download_file(full_path)
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="ignore")
        return str(content)

    async def write(self, path: str, content: str, *, overwrite: bool = True) -> None:
        full_path = self._resolve(path)
        parent = "/".join(full_path.split("/")[:-1])
        if parent:
            self._sandbox.fs.create_folder(parent, "755")
        if not overwrite:
            try:
                self._sandbox.fs.get_file_info(full_path)
                raise FileExistsError(f"File '{path}' already exists")
            except Exception:
                pass

        self._sandbox.fs.upload_file(content.encode("utf-8"), full_path)
        self._sandbox.fs.set_file_permissions(full_path, "644")

    async def delete(self, path: str) -> None:
        full_path = self._resolve(path)
        self._sandbox.fs.delete_file(full_path)

    async def list(self, path: str) -> Sequence[Dict[str, Any]]:
        full_path = self._resolve(path) if path else self.workspace_path
        entries = []
        for info in self._sandbox.fs.list_files(full_path):
            entries.append(
                {
                    "name": info.name,
                    "is_dir": bool(getattr(info, "is_dir", False)),
                    "size": getattr(info, "size", 0),
                    "modified": getattr(info, "mod_time", None),
                }
            )
        return entries

    async def exists(self, path: str) -> bool:
        full_path = self._resolve(path)
        try:
            self._sandbox.fs.get_file_info(full_path)
            return True
        except Exception:
            return False


class DaytonaBrowserService(BrowserService):
    """Browser automation service using Daytona sandbox automation API."""

    def __init__(self, sandbox):
        self._sandbox = sandbox
        self._last_state: Optional[Dict[str, Any]] = None

    async def perform_action(
        self, action: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        endpoint, method = self._map_action(action)
        if not endpoint:
            return {
                "success": False,
                "message": f"Unsupported browser action: {action}",
            }

        response = self._call_browser_api(endpoint, payload, method)
        if response.get("success"):
            self._last_state = response
        return response

    async def current_state(self) -> Dict[str, Any]:
        return self._last_state or {}

    def _map_action(self, action: str) -> Tuple[Optional[str], str]:
        endpoint_map: Dict[str, Tuple[str, str]] = {
            "navigate_to": ("navigate_to", "POST"),
            "go_back": ("go_back", "POST"),
            "click_element": ("click_element", "POST"),
            "input_text": ("input_text", "POST"),
            "send_keys": ("send_keys", "POST"),
            "switch_tab": ("switch_tab", "POST"),
            "close_tab": ("close_tab", "POST"),
            "scroll_down": ("scroll_down", "POST"),
            "scroll_up": ("scroll_up", "POST"),
            "scroll_to_text": ("scroll_to_text", "POST"),
            "get_dropdown_options": ("get_dropdown_options", "POST"),
            "select_dropdown_option": ("select_dropdown_option", "POST"),
            "click_coordinates": ("click_coordinates", "POST"),
            "drag_drop": ("drag_drop", "POST"),
            "wait": ("wait", "POST"),
        }
        return endpoint_map.get(action, (None, "POST"))

    def _call_browser_api(
        self, endpoint: str, params: Dict[str, Any], method: str = "POST"
    ) -> Dict[str, Any]:
        base_url = f"http://localhost:8003/api/automation/{endpoint}"
        if method == "GET" and params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            command = (
                f"curl -s -X {method} '{base_url}?{query}' "
                "-H 'Content-Type: application/json'"
            )
        else:
            body = json.dumps(params) if params else ""
            data_flag = f" -d '{body}'" if body else ""
            command = (
                f"curl -s -X {method} '{base_url}' "
                "-H 'Content-Type: application/json'" + data_flag
            )

        result = self._sandbox.process.exec(command, timeout=30)
        if getattr(result, "exit_code", 0) != 0:
            return {
                "success": False,
                "message": f"Browser automation failed: {result.result}",
            }

        try:
            payload = json.loads(result.result or "{}")
        except json.JSONDecodeError as exc:
            return {
                "success": False,
                "message": f"Invalid browser response: {exc}",
            }

        if "screenshot_base64" in payload:
            if not self._validate_base64(payload["screenshot_base64"]):
                payload.pop("screenshot_base64", None)
        return payload

    def _validate_base64(self, data: str) -> bool:
        if not data:
            return False
        try:
            base64.b64decode(data, validate=True)
            return True
        except Exception:
            logger.debug("Invalid base64 screenshot", exc_info=True)
            return False


class DaytonaVisionService(VisionService):
    """Vision service that reads images from Daytona sandbox filesystem."""

    MAX_IMAGE_SIZE = 10 * 1024 * 1024
    MAX_COMPRESSED_SIZE = 5 * 1024 * 1024
    DEFAULT_MAX_WIDTH = 1920
    DEFAULT_MAX_HEIGHT = 1080
    DEFAULT_JPEG_QUALITY = 85
    DEFAULT_PNG_COMPRESS_LEVEL = 6

    def __init__(self, sandbox):
        self._sandbox = sandbox
        self.workspace_path = "/workspace"

    def _resolve(self, path: str) -> str:
        if path.startswith("/"):
            return path
        return f"{self.workspace_path}/{path}".rstrip("/")

    async def read_image(self, path: str) -> Dict[str, Any]:
        full_path = self._resolve(path)
        info = self._sandbox.fs.get_file_info(full_path)
        if info.is_dir:
            raise IsADirectoryError(f"'{path}' is a directory")
        if info.size > self.MAX_IMAGE_SIZE:
            raise ValueError(
                f"Image too large ({info.size} bytes). Max {self.MAX_IMAGE_SIZE}."
            )

        raw = self._sandbox.fs.download_file(full_path)
        buffer, mime_type = self._compress_image(raw, full_path)
        if len(buffer) > self.MAX_COMPRESSED_SIZE:
            raise ValueError(
                f"Compressed image still too large ({len(buffer)} bytes). "
                f"Max {self.MAX_COMPRESSED_SIZE}."
            )

        return {
            "mime_type": mime_type,
            "base64": base64.b64encode(buffer).decode("utf-8"),
            "file_path": path,
            "original_size": info.size,
            "compressed_size": len(buffer),
        }

    def _compress_image(self, data: bytes, path: str) -> Tuple[bytes, str]:
        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type:
            mime_type = "image/jpeg"
        try:
            with Image.open(io.BytesIO(data)) as img:
                if img.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(
                        img, mask=img.split()[-1] if img.mode == "RGBA" else None
                    )
                    img = background

                width, height = img.size
                if width > self.DEFAULT_MAX_WIDTH or height > self.DEFAULT_MAX_HEIGHT:
                    ratio = min(
                        self.DEFAULT_MAX_WIDTH / width, self.DEFAULT_MAX_HEIGHT / height
                    )
                    img = img.resize(
                        (int(width * ratio), int(height * ratio)),
                        Image.Resampling.LANCZOS,
                    )

                output = io.BytesIO()
                if mime_type == "image/png":
                    img.save(
                        output,
                        format="PNG",
                        optimize=True,
                        compress_level=self.DEFAULT_PNG_COMPRESS_LEVEL,
                    )
                    mime_type = "image/png"
                elif mime_type == "image/gif":
                    img.save(output, format="GIF", optimize=True)
                    mime_type = "image/gif"
                else:
                    img.save(
                        output,
                        format="JPEG",
                        quality=self.DEFAULT_JPEG_QUALITY,
                        optimize=True,
                    )
                    mime_type = "image/jpeg"
                return output.getvalue(), mime_type
        except Exception:
            logger.debug("Image compression failed, returning raw bytes", exc_info=True)
            return data, mime_type


class DaytonaSandboxProvider(SandboxProvider):
    """Concrete sandbox provider backed by Daytona remote environments."""

    def __init__(self, app_config: Config, sandbox_settings: SandboxSettings):
        super().__init__("daytona")
        self._config = app_config
        self._settings = sandbox_settings

        self._sandbox = None
        self._metadata = SandboxMetadata(provider="daytona")

        self._shell_service: Optional[DaytonaShellService] = None
        self._file_service: Optional[DaytonaFileService] = None
        self._browser_service: Optional[DaytonaBrowserService] = None
        self._vision_service: Optional[DaytonaVisionService] = None

    async def initialize(self) -> None:
        password = self._config.daytona.VNC_password
        if not password:
            raise ValueError("Daytona VNC password must be configured")

        logger.info("Creating Daytona sandbox...")
        self._sandbox = create_sandbox(password=password)

        self._metadata.extra["sandbox_id"] = getattr(self._sandbox, "id", None)

        try:
            vnc_link = self._sandbox.get_preview_link(6080)
            website_link = self._sandbox.get_preview_link(8080)
            self._metadata.links["vnc"] = (
                vnc_link.url if hasattr(vnc_link, "url") else str(vnc_link)
            )
            self._metadata.links["website"] = (
                website_link.url if hasattr(website_link, "url") else str(website_link)
            )
        except Exception:
            logger.debug("Failed to fetch sandbox preview links", exc_info=True)

        self._shell_service = DaytonaShellService(self._sandbox)
        self._file_service = DaytonaFileService(self._sandbox)
        self._browser_service = DaytonaBrowserService(self._sandbox)
        self._vision_service = DaytonaVisionService(self._sandbox)

    async def cleanup(self) -> None:
        if self._shell_service:
            await self._shell_service.cleanup()

        if self._sandbox:
            sandbox_id = getattr(self._sandbox, "id", None)
            if sandbox_id:
                try:
                    await delete_sandbox(sandbox_id)
                except Exception:
                    logger.warning(
                        f"Failed to delete sandbox {sandbox_id}", exc_info=True
                    )
            self._sandbox = None

    def metadata(self) -> SandboxMetadata:
        return self._metadata

    def shell_service(self) -> ShellService:
        if not self._shell_service:
            raise RuntimeError("Daytona sandbox not initialized")
        return self._shell_service

    def file_service(self) -> FileService:
        if not self._file_service:
            raise RuntimeError("Daytona sandbox not initialized")
        return self._file_service

    def browser_service(self) -> Optional[BrowserService]:
        return self._browser_service

    def vision_service(self) -> Optional[VisionService]:
        return self._vision_service
