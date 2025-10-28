"""
AgentBay-backed sandbox provider implementation.
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any, Dict, List, Optional, Sequence

import requests
from agentbay import AgentBay
from agentbay.agentbay import Config as AgentBayConfig
from agentbay.browser import BrowserOption
from agentbay.command.command import CommandResult
from agentbay.computer import MouseButton, ScrollDirection
from agentbay.filesystem.filesystem import (
    BoolResult,
    DirectoryListResult,
    FileContentResult,
    FileInfoResult,
)
from agentbay.session_params import CreateSessionParams
from browser_use import Browser as BrowserUseBrowser, BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use.dom.service import DomService
from app.tool.browser_use_tool import BrowserUseTool


from app.config import AgentBaySettings, Config, SandboxSettings
from app.utils.logger import logger

from .base import (
    BrowserService,
    ComputerService,
    FileService,
    SandboxMetadata,
    SandboxProvider,
    ShellCommandResult,
    ShellService,
    VisionService,
)


class AgentBayShellService(ShellService):
    """Shell service using AgentBay session command API."""

    def __init__(self, session):
        self._session = session

    async def execute(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        blocking: bool = False,
        session: Optional[str] = None,
    ) -> ShellCommandResult:
        if cwd:
            command = f"cd {cwd} && {command}"
        timeout_ms = (timeout or 60) * 1000
        result: CommandResult = self._session.command.execute_command(
            command, timeout_ms=timeout_ms
        )
        if result.success:
            return ShellCommandResult(
                success=True,
                output=result.output,
                completed=True,
            )
        return ShellCommandResult(
            success=False,
            error=result.error_message or "AgentBay command execution failed",
        )

    async def check(self, session: str) -> ShellCommandResult:
        return ShellCommandResult(
            success=False,
            error="AgentBay shell does not support session inspection",
        )

    async def terminate(self, session: str) -> ShellCommandResult:
        return ShellCommandResult(
            success=False,
            error="AgentBay shell does not support terminating sessions",
        )

    async def list_sessions(self) -> Sequence[str]:
        return []


class AgentBayBrowserUseTool(BrowserUseTool[None]):
    """BrowserUse tool configured to attach to AgentBay CDP endpoint."""

    def __init__(self, endpoint_url: str):
        super().__init__()
        self._endpoint_url = endpoint_url

    async def _ensure_browser_initialized(self) -> BrowserContext:  # type: ignore[override]
        if self.browser is None:
            browser_config = BrowserConfig(
                headless=False,
                disable_security=True,
                cdp_url=self._endpoint_url,
            )
            self.browser = BrowserUseBrowser(browser_config)

        if self.context is None:
            context_config = BrowserContextConfig()
            self.context = await self.browser.new_context(context_config)
            self.dom_service = DomService(await self.context.get_current_page())

        return self.context


class AgentBayFileService(FileService):
    """File service built on AgentBay FileSystem APIs."""

    def __init__(self, session):
        self._session = session

    async def read(self, path: str) -> str:
        result: FileContentResult = self._session.file_system.read_file(path)
        if not result.success:
            raise FileNotFoundError(result.error_message or f"Failed to read {path}")
        return result.content or ""

    async def write(self, path: str, content: str, *, overwrite: bool = True) -> None:
        mode = "overwrite" if overwrite else "append"
        result: BoolResult = self._session.file_system.write_file(path, content, mode)
        if not result.success:
            raise IOError(result.error_message or f"Failed to write {path}")

    async def delete(self, path: str) -> None:
        command = f"rm -rf '{path}'"
        exec_result = self._session.command.execute_command(command, timeout_ms=10000)
        if not exec_result.success:
            raise IOError(exec_result.error_message or f"Failed to delete {path}")

    async def list(self, path: str) -> Sequence[dict]:
        result: DirectoryListResult = self._session.file_system.list_directory(path)
        if not result.success:
            raise IOError(result.error_message or f"Failed to list {path}")
        entries = []
        for entry in result.entries or []:
            entries.append(
                {
                    "name": entry.get("name"),
                    "is_dir": entry.get("isDirectory", False),
                }
            )
        return entries

    async def exists(self, path: str) -> bool:
        try:
            result: FileInfoResult = self._session.file_system.get_file_info(path)
            return result.success
        except Exception:
            return False


class AgentBayComputerService(ComputerService):
    """Computer automation service backed by AgentBay Computer APIs."""

    def __init__(self, session):
        self._session = session

    async def move_mouse(self, x: int, y: int) -> None:
        result = await self._call(self._session.computer.move_mouse, x, y)
        self._ensure_success(result, f"Failed to move mouse to ({x}, {y})")

    async def click_mouse(
        self, x: int, y: int, *, button: str, count: int = 1
    ) -> None:
        normalized_button = self._normalize_button(button)
        clicks = max(1, min(3, count))

        # AgentBay provides a dedicated double-left click option; prefer it when possible.
        if clicks == 2 and normalized_button == MouseButton.LEFT.value:
            result = await self._call(
                self._session.computer.click_mouse,
                x,
                y,
                MouseButton.DOUBLE_LEFT,
            )
            self._ensure_success(result, "Failed to perform double left click")
            return

        for _ in range(clicks):
            result = await self._call(
                self._session.computer.click_mouse,
                x,
                y,
                normalized_button,
            )
            self._ensure_success(result, "Failed to perform mouse click")

    async def drag_mouse(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        *,
        button: str = "left",
    ) -> None:
        normalized_button = self._normalize_button(button, allow_double=False)
        result = await self._call(
            self._session.computer.drag_mouse,
            from_x,
            from_y,
            to_x,
            to_y,
            normalized_button,
        )
        self._ensure_success(result, "Failed to drag mouse")

    async def scroll(self, x: int, y: int, *, amount: int) -> None:
        if amount == 0:
            return
        direction = ScrollDirection.UP.value if amount > 0 else ScrollDirection.DOWN.value
        result = await self._call(
            self._session.computer.scroll,
            x,
            y,
            direction,
            abs(amount),
        )
        self._ensure_success(result, "Failed to scroll")

    async def input_text(self, text: str) -> None:
        result = await self._call(self._session.computer.input_text, text)
        self._ensure_success(result, "Failed to input text")

    async def press_keys(self, keys: Sequence[str], *, hold: bool = False) -> None:
        formatted_keys = [self._format_key(key) for key in keys if key]
        if not formatted_keys:
            raise RuntimeError("No keys provided for press_keys")
        result = await self._call(
            self._session.computer.press_keys, formatted_keys, hold
        )
        self._ensure_success(result, "Failed to press keys")

    async def release_keys(self, keys: Sequence[str]) -> None:
        formatted_keys = [self._format_key(key) for key in keys if key]
        if not formatted_keys:
            raise RuntimeError("No keys provided for release_keys")
        result = await self._call(self._session.computer.release_keys, formatted_keys)
        self._ensure_success(result, "Failed to release keys")

    async def get_cursor_position(self) -> Dict[str, int]:
        result = await self._call(self._session.computer.get_cursor_position)
        operation = self._ensure_success(
            result, "Failed to get cursor position"
        )
        data = getattr(operation, "data", None) or {}
        x = int(data.get("x", 0))
        y = int(data.get("y", 0))
        return {"x": x, "y": y}

    async def get_screen_size(self) -> Dict[str, Any]:
        result = await self._call(self._session.computer.get_screen_size)
        operation = self._ensure_success(result, "Failed to get screen size")
        data = getattr(operation, "data", None) or {}
        return data

    async def screenshot(self) -> Dict[str, Any]:
        result = await self._call(self._session.computer.screenshot)
        operation = self._ensure_success(result, "Failed to capture screenshot")
        screenshot_ref = getattr(operation, "data", None)
        base64_image: Optional[str] = None
        if isinstance(screenshot_ref, str) and screenshot_ref:
            try:
                base64_image = await asyncio.to_thread(
                    self._download_base64, screenshot_ref
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to download screenshot from %s: %s",
                    screenshot_ref,
                    exc,
                )
        return {"url": screenshot_ref, "base64": base64_image}

    def supports_mouse_hold(self) -> bool:
        # AgentBay Computer API does not expose explicit mouse down/up operations yet.
        return False

    async def _call(self, func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    def _ensure_success(self, result, default_error: str):
        if not getattr(result, "success", False):
            error = getattr(result, "error_message", "") or default_error
            raise RuntimeError(error)
        return result

    def _normalize_button(self, button: str, allow_double: bool = True) -> str:
        value = (button or "left").lower()
        mapping = {
            "left": MouseButton.LEFT.value,
            "right": MouseButton.RIGHT.value,
            "middle": MouseButton.MIDDLE.value,
        }
        if allow_double:
            mapping["double_left"] = MouseButton.DOUBLE_LEFT.value
        if value not in mapping:
            raise RuntimeError(f"Unsupported mouse button: {button}")
        normalized = mapping[value]
        if normalized == MouseButton.DOUBLE_LEFT.value and not allow_double:
            raise RuntimeError("Double click button is not supported for this action")
        return normalized

    def _format_key(self, raw: str) -> str:
        key = (raw or "").strip()
        if not key:
            raise RuntimeError("Empty key provided")
        lower = key.lower()
        special_map = {
            "enter": "Enter",
            "esc": "Esc",
            "escape": "Esc",
            "backspace": "Backspace",
            "tab": "Tab",
            "space": "Space",
            "delete": "Delete",
            "ctrl": "Ctrl",
            "control": "Ctrl",
            "alt": "Alt",
            "shift": "Shift",
            "win": "Win",
            "cmd": "Meta",
            "command": "Meta",
            "meta": "Meta",
            "up": "Up",
            "down": "Down",
            "left": "Left",
            "right": "Right",
            "pageup": "PageUp",
            "pagedown": "PageDown",
            "home": "Home",
            "end": "End",
            "insert": "Insert",
        }
        if lower in special_map:
            return special_map[lower]
        if lower.startswith("f") and lower[1:].isdigit():
            return lower.upper()
        if len(lower) == 1 and lower.isalpha():
            return lower
        if lower.isdigit():
            return lower
        return key

    def _download_base64(self, url: str) -> str:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return base64.b64encode(response.content).decode("ascii")


class AgentBayBrowserService(BrowserService):
    """Browser automation service backed by BrowserUse over AgentBay CDP."""

    ACTION_MAP = {
        "navigate_to": "go_to_url",
        "go_to_url": "go_to_url",
        "go_back": "go_back",
        "click_element": "click_element",
        "input_text": "input_text",
        "scroll_down": "scroll_down",
        "scroll_up": "scroll_up",
        "scroll_to_text": "scroll_to_text",
        "send_keys": "send_keys",
        "switch_tab": "switch_tab",
        "open_tab": "open_tab",
        "close_tab": "close_tab",
        "wait": "wait",
        "get_dropdown_options": "get_dropdown_options",
        "select_dropdown_option": "select_dropdown_option",
    }

    def __init__(self, session):
        self._session = session
        self._tool: Optional[AgentBayBrowserUseTool] = None
        self._endpoint_url: Optional[str] = None

    async def _ensure_tool(self) -> AgentBayBrowserUseTool:
        if self._tool is not None:
            return self._tool

        option = BrowserOption()
        success = await self._session.browser.initialize_async(option)
        if not success:
            raise RuntimeError("Failed to initialize AgentBay browser session")

        endpoint_url = self._session.browser.get_endpoint_url()
        if not endpoint_url:
            raise RuntimeError("AgentBay browser endpoint URL unavailable")

        self._endpoint_url = endpoint_url
        self._tool = AgentBayBrowserUseTool(endpoint_url)
        return self._tool

    async def perform_action(
        self, action: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        tool = await self._ensure_tool()
        mapped_action = self.ACTION_MAP.get(action.lower())
        params: Dict[str, Any] = {}

        if mapped_action is None:
            return {
                "success": False,
                "message": f"Unsupported browser action: {action}",
            }

        def add_if(name: str, value: Any) -> None:
            if value is not None:
                params[name] = value

        if mapped_action == "go_to_url":
            add_if("url", payload.get("url"))
            if "url" not in params:
                return {"success": False, "message": "url is required for navigate_to"}
        elif mapped_action in ("click_element", "get_dropdown_options"):
            add_if("index", payload.get("index"))
            if "index" not in params:
                return {"success": False, "message": "index is required for action"}
        elif mapped_action == "input_text":
            add_if("index", payload.get("index"))
            add_if("text", payload.get("text"))
            if len(params) != 2:
                return {
                    "success": False,
                    "message": "index and text required for input_text",
                }
        elif mapped_action == "scroll_down" or mapped_action == "scroll_up":
            add_if("scroll_amount", payload.get("amount"))
        elif mapped_action == "scroll_to_text":
            add_if("text", payload.get("text"))
            if "text" not in params:
                return {"success": False, "message": "text required for scroll_to_text"}
        elif mapped_action == "send_keys":
            add_if("keys", payload.get("keys"))
            if "keys" not in params:
                return {"success": False, "message": "keys required for send_keys"}
        elif mapped_action == "switch_tab":
            add_if("tab_id", payload.get("page_id"))
            if "tab_id" not in params:
                return {"success": False, "message": "page_id required for switch_tab"}
        elif mapped_action == "open_tab":
            add_if("url", payload.get("url"))
            if "url" not in params:
                return {"success": False, "message": "url required for open_tab"}
        elif mapped_action == "select_dropdown_option":
            add_if("index", payload.get("index"))
            add_if("text", payload.get("text"))
            if len(params) != 2:
                return {
                    "success": False,
                    "message": "index and text required for select_dropdown_option",
                }
        elif mapped_action == "wait":
            add_if("seconds", payload.get("seconds"))

        try:
            result = await tool.execute(action=mapped_action, **params)
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "message": f"Browser action failed: {exc}"}

        if result.error:
            return {"success": False, "message": result.error}

        message = (
            result.output
            if isinstance(result.output, str)
            else json.dumps(result.output)
        )

        state_info = await self._collect_state(tool)
        response: Dict[str, Any] = {
            "success": True,
            "message": message,
        }
        if state_info:
            response["state"] = state_info
        return response

    async def current_state(self) -> Dict[str, Any]:
        tool = await self._ensure_tool()
        state = await self._collect_state(tool)
        return state or {}

    async def cleanup(self) -> None:
        if self._tool and self._tool.browser:
            try:
                await self._tool.browser.close()  # type: ignore[attr-defined]
            except Exception:
                logger.debug("Failed to close BrowserUse browser", exc_info=True)
        try:
            await self._session.browser.agent.close_async()
        except Exception:
            logger.debug("Failed to close AgentBay browser session", exc_info=True)
        self._tool = None
        self._endpoint_url = None

    async def _collect_state(
        self, tool: AgentBayBrowserUseTool
    ) -> Optional[Dict[str, Any]]:
        try:
            result = await tool.get_current_state()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to obtain browser state: %s", exc)
            return None
        if result.error or not result.output:
            return None
        try:
            state = json.loads(result.output)
        except Exception:
            state = {"raw_output": result.output}
        if result.base64_image:
            state["screenshot_base64"] = result.base64_image
        return state


class AgentBaySandboxProvider(SandboxProvider):
    """Sandbox provider backed by AgentBay cloud sessions."""

    def __init__(self, app_config: Config, sandbox_settings: SandboxSettings):
        super().__init__("agentbay")
        self._config = app_config
        self._sandbox_settings = sandbox_settings
        self._settings: AgentBaySettings = app_config.agentbay

        self._client: Optional[AgentBay] = None
        self._session = None

        self._metadata = SandboxMetadata(provider="agentbay")
        self._shell_service: Optional[AgentBayShellService] = None
        self._file_service: Optional[AgentBayFileService] = None
        self._browser_service: Optional[AgentBayBrowserService] = None
        self._computer_service: Optional[AgentBayComputerService] = None

    async def initialize(self) -> None:
        logger.info("Initializing AgentBay sandbox provider")

        agentbay_cfg = AgentBayConfig(
            endpoint=self._settings.endpoint,
            timeout_ms=self._settings.timeout_ms,
        )
        api_key = self._settings.api_key or ""
        env_file = self._settings.env_file

        self._client = AgentBay(api_key=api_key, cfg=agentbay_cfg, env_file=env_file)

        params = CreateSessionParams()
        params.is_vpc = self._settings.session_defaults.is_vpc
        if self._settings.session_defaults.image_id:
            params.image_id = self._settings.session_defaults.image_id

        # AgentBay.create is synchronous; run in executor to avoid blocking event loop
        session_result = await asyncio.to_thread(self._client.create, params)
        if not session_result.success:
            raise RuntimeError(
                session_result.error_message
                or "Failed to create AgentBay sandbox session"
            )

        self._session = session_result.session
        logger.info(f"AgentBay session created: {self._session.session_id}")

        self._metadata.extra["session_id"] = self._session.session_id
        if getattr(self._session, "resource_url", None):
            self._metadata.links["resource"] = self._session.resource_url

        self._shell_service = AgentBayShellService(self._session)
        self._file_service = AgentBayFileService(self._session)
        self._browser_service = AgentBayBrowserService(self._session)
        self._computer_service = AgentBayComputerService(self._session)

    async def cleanup(self) -> None:
        if self._browser_service:
            try:
                await self._browser_service.cleanup()
            except Exception:
                logger.warning("Failed to cleanup AgentBay browser", exc_info=True)
            self._browser_service = None
        if self._client and self._session:
            try:
                await asyncio.to_thread(self._client.delete, self._session)
            except Exception:
                logger.warning(
                    f"Failed to delete AgentBay session {self._session.session_id}",
                    exc_info=True,
                )
        self._session = None
        self._client = None
        self._computer_service = None

    def metadata(self) -> SandboxMetadata:
        return self._metadata

    def shell_service(self) -> ShellService:
        if not self._shell_service:
            raise RuntimeError("AgentBay sandbox not initialized")
        return self._shell_service

    def file_service(self) -> FileService:
        if not self._file_service:
            raise RuntimeError("AgentBay sandbox not initialized")
        return self._file_service

    def browser_service(self) -> Optional[BrowserService]:
        return self._browser_service

    def vision_service(self) -> Optional[VisionService]:
        return None

    def computer_service(self) -> Optional[ComputerService]:
        return self._computer_service
