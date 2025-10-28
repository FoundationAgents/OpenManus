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
    MobileService,
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


class AgentBayMobileService(MobileService):
    """Mobile automation service backed by AgentBay Mobile APIs."""

    def __init__(self, session):
        self._session = session

    async def tap(self, x: int, y: int) -> None:
        result = await self._call(self._session.mobile.tap, x, y)
        self._ensure_success(result, f"Failed to tap ({x}, {y})")

    async def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 300,
    ) -> None:
        result = await self._call(
            self._session.mobile.swipe,
            start_x,
            start_y,
            end_x,
            end_y,
            duration_ms,
        )
        self._ensure_success(result, "Failed to perform swipe")

    async def input_text(self, text: str) -> None:
        result = await self._call(self._session.mobile.input_text, text)
        self._ensure_success(result, "Failed to input text")

    async def send_key(self, key_code: int) -> None:
        result = await self._call(self._session.mobile.send_key, key_code)
        self._ensure_success(result, f"Failed to send key {key_code}")

    async def screenshot(self) -> Dict[str, Any]:
        result = await self._call(self._session.mobile.screenshot)
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
                    "Failed to download mobile screenshot from %s: %s",
                    screenshot_ref,
                    exc,
                )
        return {"url": screenshot_ref, "base64": base64_image}

    async def get_clickable_ui_elements(self, timeout_ms: int = 2000) -> Dict[str, Any]:
        result = await self._call(
            self._session.mobile.get_clickable_ui_elements, timeout_ms
        )
        if not getattr(result, "success", False):
            error = getattr(result, "error_message", "Failed to get UI elements")
            raise RuntimeError(error)
        elements = getattr(result, "elements", []) or []
        return {"elements": elements, "count": len(elements)}

    async def _call(self, func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    def _ensure_success(self, result, default_error: str):
        if not getattr(result, "success", False):
            error = getattr(result, "error_message", "") or default_error
            raise RuntimeError(error)
        return result

    def _download_base64(self, url: str) -> str:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return base64.b64encode(response.content).decode("ascii")

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
        if not self._settings:
            raise RuntimeError("AgentBay settings are required when provider=agentbay")

        self._client: Optional[AgentBay] = None
        self._metadata = SandboxMetadata(provider="agentbay")

        self._sessions: Dict[str, Any] = {}
        self._session_locks: Dict[str, asyncio.Lock] = {}
        self._service_cache: Dict[tuple[str, str], Any] = {}

        self._shell_wrapper: Optional["AgentBayLazyShellService"] = None
        self._file_wrapper: Optional["AgentBayLazyFileService"] = None
        self._browser_wrapper: Optional["AgentBayLazyBrowserService"] = None
        self._computer_wrapper: Optional["AgentBayLazyComputerService"] = None
        self._mobile_wrapper: Optional["AgentBayLazyMobileService"] = None

    async def initialize(self) -> None:
        logger.info("Initializing AgentBay sandbox provider (lazy sessions)")
        self._metadata.links.clear()
        self._metadata.extra.clear()
        self._metadata.extra["sessions"] = []

    async def cleanup(self) -> None:
        for service in list(self._service_cache.values()):
            if isinstance(service, AgentBayBrowserService):
                try:
                    await service.cleanup()
                except Exception:
                    logger.warning("Failed to cleanup AgentBay browser", exc_info=True)

        if self._client:
            for image_id, session in list(self._sessions.items()):
                try:
                    await asyncio.to_thread(self._client.delete, session)
                except Exception:
                    logger.warning(
                        "Failed to delete AgentBay session %s for image %s",
                        getattr(session, "session_id", "unknown"),
                        image_id,
                        exc_info=True,
                    )
            self._sessions.clear()

        self._service_cache.clear()
        self._session_locks.clear()
        self._client = None
        self._shell_wrapper = None
        self._file_wrapper = None
        self._browser_wrapper = None
        self._computer_wrapper = None
        self._mobile_wrapper = None

    def metadata(self) -> SandboxMetadata:
        return self._metadata

    def shell_service(self) -> ShellService:
        if self._shell_wrapper is None:
            self._shell_wrapper = AgentBayLazyShellService(self)
        return self._shell_wrapper

    def file_service(self) -> FileService:
        if self._file_wrapper is None:
            self._file_wrapper = AgentBayLazyFileService(self)
        return self._file_wrapper

    def browser_service(self) -> Optional[BrowserService]:
        if self._get_image_id_for_role("browser") is None:
            return None
        if self._browser_wrapper is None:
            self._browser_wrapper = AgentBayLazyBrowserService(self)
        return self._browser_wrapper

    def vision_service(self) -> Optional[VisionService]:
        return None

    def computer_service(self) -> Optional[ComputerService]:
        if self._get_image_id_for_role("computer") is None:
            return None
        if self._computer_wrapper is None:
            self._computer_wrapper = AgentBayLazyComputerService(self)
        return self._computer_wrapper

    def mobile_service(self) -> Optional[MobileService]:
        if self._get_image_id_for_role("mobile") is None:
            return None
        if self._mobile_wrapper is None:
            self._mobile_wrapper = AgentBayLazyMobileService(self)
        return self._mobile_wrapper

    async def _get_service(self, kind: str, role: str):
        image_id = self._get_image_id_for_role(role)
        if not image_id:
            raise RuntimeError(f"No image configured for AgentBay role '{role}'")

        session = await self._ensure_session(image_id)
        cache_key = (image_id, kind)
        if cache_key in self._service_cache:
            return self._service_cache[cache_key]

        if kind == "shell":
            service = AgentBayShellService(session)
        elif kind == "file":
            service = AgentBayFileService(session)
        elif kind == "browser":
            service = AgentBayBrowserService(session)
        elif kind == "computer":
            service = AgentBayComputerService(session)
        elif kind == "mobile":
            service = AgentBayMobileService(session)
        else:
            raise ValueError(f"Unknown service kind: {kind}")

        self._service_cache[cache_key] = service
        return service

    async def _ensure_session(self, image_id: str):
        if image_id in self._sessions:
            return self._sessions[image_id]

        lock = self._session_locks.setdefault(image_id, asyncio.Lock())
        async with lock:
            if image_id in self._sessions:
                return self._sessions[image_id]

            if self._client is None:
                agentbay_cfg = AgentBayConfig(
                    endpoint=self._settings.endpoint,
                    timeout_ms=self._settings.timeout_ms,
                )
                api_key = self._settings.api_key or ""
                env_file = self._settings.env_file
                self._client = AgentBay(
                    api_key=api_key, cfg=agentbay_cfg, env_file=env_file
                )

            params = CreateSessionParams()
            params.is_vpc = self._settings.session_defaults.is_vpc
            params.image_id = image_id

            logger.info("Creating AgentBay session with image %s", image_id)
            session_result = await asyncio.to_thread(self._client.create, params)
            if not session_result.success:
                raise RuntimeError(
                    session_result.error_message
                    or f"Failed to create AgentBay session for image {image_id}"
                )

            session = session_result.session
            self._sessions[image_id] = session
            self._metadata.extra.setdefault("sessions", []).append(
                {
                    "image_id": image_id,
                    "session_id": session.session_id,
                }
            )
            if getattr(session, "resource_url", None):
                self._metadata.links[f"{image_id}_resource"] = session.resource_url
                logger.info(
                    "AgentBay session %s (image %s) resource: %s",
                    session.session_id,
                    image_id,
                    session.resource_url,
                )

            logger.info(
                "AgentBay session %s ready for image %s",
                session.session_id,
                image_id,
            )

            return session

    def _get_image_id_for_role(self, role: str) -> Optional[str]:
        desktop_image = self._settings.desktop_image_id
        browser_image = self._settings.browser_image_id
        mobile_image = self._settings.mobile_image_id
        default_image = self._settings.session_defaults.image_id

        if role == "computer":
            return desktop_image or default_image
        if role == "browser":
            return browser_image or default_image or desktop_image
        if role == "mobile":
            return mobile_image or default_image or desktop_image
        # shell/file default preference: use desktop if available, otherwise default, otherwise browser
        return default_image or desktop_image or browser_image or mobile_image


class AgentBayLazyShellService(ShellService):
    def __init__(self, provider: AgentBaySandboxProvider):
        self._provider = provider

    async def execute(
        self,
        command: str,
        *,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
        blocking: bool = False,
        session: Optional[str] = None,
    ) -> ShellCommandResult:
        service: AgentBayShellService = await self._provider._get_service(
            "shell", "shell"
        )
        return await service.execute(
            command, cwd=cwd, timeout=timeout, blocking=blocking, session=session
        )

    async def check(self, session: str) -> ShellCommandResult:
        service: AgentBayShellService = await self._provider._get_service(
            "shell", "shell"
        )
        return await service.check(session)

    async def terminate(self, session: str) -> ShellCommandResult:
        service: AgentBayShellService = await self._provider._get_service(
            "shell", "shell"
        )
        return await service.terminate(session)

    async def list_sessions(self) -> Sequence[str]:
        service: AgentBayShellService = await self._provider._get_service(
            "shell", "shell"
        )
        return await service.list_sessions()


class AgentBayLazyFileService(FileService):
    def __init__(self, provider: AgentBaySandboxProvider):
        self._provider = provider

    async def read(self, path: str) -> str:
        service: AgentBayFileService = await self._provider._get_service(
            "file", "shell"
        )
        return await service.read(path)

    async def write(
        self, path: str, content: str, *, overwrite: bool = True
    ) -> None:
        service: AgentBayFileService = await self._provider._get_service(
            "file", "shell"
        )
        await service.write(path, content, overwrite=overwrite)

    async def delete(self, path: str) -> None:
        service: AgentBayFileService = await self._provider._get_service(
            "file", "shell"
        )
        await service.delete(path)

    async def list(self, path: str) -> Sequence[Dict[str, Any]]:
        service: AgentBayFileService = await self._provider._get_service(
            "file", "shell"
        )
        return await service.list(path)

    async def exists(self, path: str) -> bool:
        service: AgentBayFileService = await self._provider._get_service(
            "file", "shell"
        )
        return await service.exists(path)


class AgentBayLazyBrowserService(BrowserService):
    def __init__(self, provider: AgentBaySandboxProvider):
        self._provider = provider

    async def perform_action(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        service: AgentBayBrowserService = await self._provider._get_service(
            "browser", "browser"
        )
        return await service.perform_action(action, payload)

    async def current_state(self) -> Dict[str, Any]:
        service: AgentBayBrowserService = await self._provider._get_service(
            "browser", "browser"
        )
        return await service.current_state()

    async def cleanup(self) -> None:
        image_id = self._provider._get_image_id_for_role("browser")
        if not image_id:
            return
        service = self._provider._service_cache.get((image_id, "browser"))
        if service:
            await service.cleanup()


class AgentBayLazyComputerService(ComputerService):
    def __init__(self, provider: AgentBaySandboxProvider):
        self._provider = provider

    async def move_mouse(self, x: int, y: int) -> None:
        service: AgentBayComputerService = await self._provider._get_service(
            "computer", "computer"
        )
        await service.move_mouse(x, y)

    async def click_mouse(
        self, x: int, y: int, *, button: str, count: int = 1
    ) -> None:
        service: AgentBayComputerService = await self._provider._get_service(
            "computer", "computer"
        )
        await service.click_mouse(x, y, button=button, count=count)

    async def drag_mouse(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        *,
        button: str = "left",
    ) -> None:
        service: AgentBayComputerService = await self._provider._get_service(
            "computer", "computer"
        )
        await service.drag_mouse(from_x, from_y, to_x, to_y, button=button)

    async def scroll(self, x: int, y: int, *, amount: int) -> None:
        service: AgentBayComputerService = await self._provider._get_service(
            "computer", "computer"
        )
        await service.scroll(x, y, amount=amount)

    async def input_text(self, text: str) -> None:
        service: AgentBayComputerService = await self._provider._get_service(
            "computer", "computer"
        )
        await service.input_text(text)

    async def press_keys(self, keys: Sequence[str], *, hold: bool = False) -> None:
        service: AgentBayComputerService = await self._provider._get_service(
            "computer", "computer"
        )
        await service.press_keys(keys, hold=hold)

    async def release_keys(self, keys: Sequence[str]) -> None:
        service: AgentBayComputerService = await self._provider._get_service(
            "computer", "computer"
        )
        await service.release_keys(keys)

    async def get_cursor_position(self) -> Dict[str, int]:
        service: AgentBayComputerService = await self._provider._get_service(
            "computer", "computer"
        )
        return await service.get_cursor_position()

    async def get_screen_size(self) -> Dict[str, Any]:
        service: AgentBayComputerService = await self._provider._get_service(
            "computer", "computer"
        )
        return await service.get_screen_size()

    async def screenshot(self) -> Dict[str, Any]:
        service: AgentBayComputerService = await self._provider._get_service(
            "computer", "computer"
        )
        return await service.screenshot()

    def supports_mouse_hold(self) -> bool:
        image_id = self._provider._get_image_id_for_role("computer")
        if not image_id:
            return False
        service = self._provider._service_cache.get((image_id, "computer"))
        if isinstance(service, AgentBayComputerService):
            return service.supports_mouse_hold()
        return False


class AgentBayLazyMobileService(MobileService):
    def __init__(self, provider: AgentBaySandboxProvider):
        self._provider = provider

    async def tap(self, x: int, y: int) -> None:
        service: AgentBayMobileService = await self._provider._get_service(
            "mobile", "mobile"
        )
        await service.tap(x, y)

    async def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 300,
    ) -> None:
        service: AgentBayMobileService = await self._provider._get_service(
            "mobile", "mobile"
        )
        await service.swipe(start_x, start_y, end_x, end_y, duration_ms)

    async def input_text(self, text: str) -> None:
        service: AgentBayMobileService = await self._provider._get_service(
            "mobile", "mobile"
        )
        await service.input_text(text)

    async def send_key(self, key_code: int) -> None:
        service: AgentBayMobileService = await self._provider._get_service(
            "mobile", "mobile"
        )
        await service.send_key(key_code)

    async def screenshot(self) -> Dict[str, Any]:
        service: AgentBayMobileService = await self._provider._get_service(
            "mobile", "mobile"
        )
        return await service.screenshot()

    async def get_clickable_ui_elements(self, timeout_ms: int = 2000) -> Dict[str, Any]:
        service: AgentBayMobileService = await self._provider._get_service(
            "mobile", "mobile"
        )
        return await service.get_clickable_ui_elements(timeout_ms)
