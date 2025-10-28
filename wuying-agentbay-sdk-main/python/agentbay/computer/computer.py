"""
Computer module for desktop UI automation.
Handles mouse operations, keyboard operations, window management, 
application management, and screen operations.
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Union

from agentbay.api.base_service import BaseService
from agentbay.exceptions import AgentBayError
from agentbay.model import BoolResult, OperationResult
from agentbay.application.application import InstalledAppListResult, InstalledApp, ProcessListResult, AppOperationResult
from agentbay.window.window import WindowListResult, WindowInfoResult


class MouseButton(str, Enum):
    """Mouse button types for click and drag operations."""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"
    DOUBLE_LEFT = "double_left"


class ScrollDirection(str, Enum):
    """Scroll direction for scroll operations."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
class Computer(BaseService):
    """
    Handles computer UI automation operations in the AgentBay cloud environment.
    Provides comprehensive desktop automation capabilities including mouse, keyboard,
    window management, application management, and screen operations.
    """

    def __init__(self, session):
        """
        Initialize a Computer object.

        Args:
            session: The session object that provides access to the AgentBay API.
        """
        super().__init__(session)

    # Mouse Operations
    def click_mouse(self, x: int, y: int, button: Union[MouseButton, str] = MouseButton.LEFT) -> BoolResult:
        """
        Clicks the mouse at the specified coordinates.

        Args:
            x (int): X coordinate.
            y (int): Y coordinate.
            button (Union[MouseButton, str], optional): Button type. Can be MouseButton enum or string.
                Valid values: MouseButton.LEFT, MouseButton.RIGHT, MouseButton.MIDDLE, MouseButton.DOUBLE_LEFT
                or their string equivalents. Defaults to MouseButton.LEFT.

        Returns:
            BoolResult: Result object containing success status and error message if any.

        Raises:
            ValueError: If button is not a valid option.
        """
        button_str = button.value if isinstance(button, MouseButton) else button
        valid_buttons = [b.value for b in MouseButton]
        if button_str not in valid_buttons:
            raise ValueError(f"Invalid button '{button_str}'. Must be one of {valid_buttons}")

        args = {"x": x, "y": y, "button": button_str}
        try:
            result = self._call_mcp_tool("click_mouse", args)

            if not result.success:
                return BoolResult(
                    request_id=result.request_id,
                    success=False,
                    data=None,
                    error_message=result.error_message,
                )

            return BoolResult(
                request_id=result.request_id,
                success=True,
                data=True,
                error_message="",
            )
        except Exception as e:
            return BoolResult(
                request_id="",
                success=False,
                data=None,
                error_message=f"Failed to click mouse: {str(e)}",
            )

    def move_mouse(self, x: int, y: int) -> BoolResult:
        """
        Moves the mouse to the specified coordinates.

        Args:
            x (int): X coordinate.
            y (int): Y coordinate.

        Returns:
            BoolResult: Result object containing success status and error message if any.
        """
        args = {"x": x, "y": y}
        try:
            result = self._call_mcp_tool("move_mouse", args)

            if not result.success:
                return BoolResult(
                    request_id=result.request_id,
                    success=False,
                    data=None,
                    error_message=result.error_message,
                )

            return BoolResult(
                request_id=result.request_id,
                success=True,
                data=True,
                error_message="",
            )
        except Exception as e:
            return BoolResult(
                request_id="",
                success=False,
                data=None,
                error_message=f"Failed to move mouse: {str(e)}",
            )

    def drag_mouse(
        self, from_x: int, from_y: int, to_x: int, to_y: int, button: Union[MouseButton, str] = MouseButton.LEFT
    ) -> BoolResult:
        """
        Drags the mouse from one point to another.

        Args:
            from_x (int): Starting X coordinate.
            from_y (int): Starting Y coordinate.
            to_x (int): Ending X coordinate.
            to_y (int): Ending Y coordinate.
            button (Union[MouseButton, str], optional): Button type. Can be MouseButton enum or string.
                Valid values: MouseButton.LEFT, MouseButton.RIGHT, MouseButton.MIDDLE
                or their string equivalents. Defaults to MouseButton.LEFT.
                Note: DOUBLE_LEFT is not supported for drag operations.

        Returns:
            BoolResult: Result object containing success status and error message if any.

        Raises:
            ValueError: If button is not a valid option.
        """
        button_str = button.value if isinstance(button, MouseButton) else button
        valid_buttons = ["left", "right", "middle"]
        if button_str not in valid_buttons:
            raise ValueError(f"Invalid button '{button_str}'. Must be one of {valid_buttons}")

        args = {
            "from_x": from_x,
            "from_y": from_y,
            "to_x": to_x,
            "to_y": to_y,
            "button": button_str,
        }
        try:
            result = self._call_mcp_tool("drag_mouse", args)

            if not result.success:
                return BoolResult(
                    request_id=result.request_id,
                    success=False,
                    data=None,
                    error_message=result.error_message,
                )

            return BoolResult(
                request_id=result.request_id,
                success=True,
                data=True,
                error_message="",
            )
        except Exception as e:
            return BoolResult(
                request_id="",
                success=False,
                data=None,
                error_message=f"Failed to drag mouse: {str(e)}",
            )

    def scroll(
        self, x: int, y: int, direction: Union[ScrollDirection, str] = ScrollDirection.UP, amount: int = 1
    ) -> BoolResult:
        """
        Scrolls the mouse wheel at the specified coordinates.

        Args:
            x (int): X coordinate.
            y (int): Y coordinate.
            direction (Union[ScrollDirection, str], optional): Scroll direction. Can be ScrollDirection enum or string.
                Valid values: ScrollDirection.UP, ScrollDirection.DOWN, ScrollDirection.LEFT, ScrollDirection.RIGHT
                or their string equivalents. Defaults to ScrollDirection.UP.
            amount (int, optional): Scroll amount. Defaults to 1.

        Returns:
            BoolResult: Result object containing success status and error message if any.

        Raises:
            ValueError: If direction is not a valid option.
        """
        direction_str = direction.value if isinstance(direction, ScrollDirection) else direction
        valid_directions = [d.value for d in ScrollDirection]
        if direction_str not in valid_directions:
            raise ValueError(f"Invalid direction '{direction_str}'. Must be one of {valid_directions}")

        args = {"x": x, "y": y, "direction": direction_str, "amount": amount}
        try:
            result = self._call_mcp_tool("scroll", args)

            if not result.success:
                return BoolResult(
                    request_id=result.request_id,
                    success=False,
                    data=None,
                    error_message=result.error_message,
                )

            return BoolResult(
                request_id=result.request_id,
                success=True,
                data=True,
                error_message="",
            )
        except Exception as e:
            return BoolResult(
                request_id="",
                success=False,
                data=None,
                error_message=f"Failed to scroll: {str(e)}",
            )

    def get_cursor_position(self) -> OperationResult:
        """
        Gets the current cursor position.

        Returns:
            OperationResult: Result object containing cursor position data
                with keys 'x' and 'y', and error message if any.
        """
        args = {}
        try:
            result = self._call_mcp_tool("get_cursor_position", args)

            if not result.success:
                return OperationResult(
                    request_id=result.request_id,
                    success=False,
                    data=None,
                    error_message=result.error_message,
                )

            return OperationResult(
                request_id=result.request_id,
                success=True,
                data=result.data,
                error_message="",
            )
        except Exception as e:
            return OperationResult(
                request_id="",
                success=False,
                data=None,
                error_message=f"Failed to get cursor position: {str(e)}",
            )

    # Keyboard Operations
    def input_text(self, text: str) -> BoolResult:
        """
        Inputs text into the active field.

        Args:
            text (str): The text to input.

        Returns:
            BoolResult: Result object containing success status and error message if any.
        """
        args = {"text": text}
        try:
            result = self._call_mcp_tool("input_text", args)

            if not result.success:
                return BoolResult(
                    request_id=result.request_id,
                    success=False,
                    data=None,
                    error_message=result.error_message,
                )

            return BoolResult(
                request_id=result.request_id,
                success=True,
                data=True,
                error_message="",
            )
        except Exception as e:
            return BoolResult(
                request_id="",
                success=False,
                data=None,
                error_message=f"Failed to input text: {str(e)}",
            )

    def press_keys(self, keys: List[str], hold: bool = False) -> BoolResult:
        """
        Presses the specified keys.

        Args:
            keys (List[str]): List of keys to press (e.g., ["Ctrl", "a"]).
            hold (bool, optional): Whether to hold the keys. Defaults to False.

        Returns:
            BoolResult: Result object containing success status and error message if any.
        """
        args = {"keys": keys, "hold": hold}
        try:
            result = self._call_mcp_tool("press_keys", args)

            if not result.success:
                return BoolResult(
                    request_id=result.request_id,
                    success=False,
                    data=None,
                    error_message=result.error_message,
                )

            return BoolResult(
                request_id=result.request_id,
                success=True,
                data=True,
                error_message="",
            )
        except Exception as e:
            return BoolResult(
                request_id="",
                success=False,
                data=None,
                error_message=f"Failed to press keys: {str(e)}",
            )

    def release_keys(self, keys: List[str]) -> BoolResult:
        """
        Releases the specified keys.

        Args:
            keys (List[str]): List of keys to release (e.g., ["Ctrl", "a"]).

        Returns:
            BoolResult: Result object containing success status and error message if any.
        """
        args = {"keys": keys}
        try:
            result = self._call_mcp_tool("release_keys", args)

            if not result.success:
                return BoolResult(
                    request_id=result.request_id,
                    success=False,
                    data=None,
                    error_message=result.error_message,
                )

            return BoolResult(
                request_id=result.request_id,
                success=True,
                data=True,
                error_message="",
            )
        except Exception as e:
            return BoolResult(
                request_id="",
                success=False,
                data=None,
                error_message=f"Failed to release keys: {str(e)}",
            )

    # Screen Operations
    def get_screen_size(self) -> OperationResult:
        """
        Gets the screen size and DPI scaling factor.

        Returns:
            OperationResult: Result object containing screen size data
                with keys 'width', 'height', and 'dpiScalingFactor',
                and error message if any.
        """
        args = {}
        try:
            result = self._call_mcp_tool("get_screen_size", args)

            if not result.success:
                return OperationResult(
                    request_id=result.request_id,
                    success=False,
                    data=None,
                    error_message=result.error_message,
                )

            return OperationResult(
                request_id=result.request_id,
                success=True,
                data=result.data,
                error_message="",
            )
        except Exception as e:
            return OperationResult(
                request_id="",
                success=False,
                data=None,
                error_message=f"Failed to get screen size: {str(e)}",
            )

    def screenshot(self) -> OperationResult:
        """
        Takes a screenshot of the current screen.

        Returns:
            OperationResult: Result object containing the path to the screenshot
                and error message if any.
        """
        args = {}
        try:
            result = self._call_mcp_tool("system_screenshot", args)

            if not result.success:
                return OperationResult(
                    request_id=result.request_id,
                    success=False,
                    data=None,
                    error_message=result.error_message,
                )

            return OperationResult(
                request_id=result.request_id,
                success=True,
                data=result.data,
                error_message="",
            )
        except Exception as e:
            return OperationResult(
                request_id="",
                success=False,
                data=None,
                error_message=f"Failed to take screenshot: {str(e)}",
            )

    # Window Management Operations (delegated to existing window module)
    def list_root_windows(self, timeout_ms: int = 3000) -> WindowListResult:
        """
        Lists all root windows.

        Args:
            timeout_ms (int, optional): Timeout in milliseconds. Defaults to 3000.
        Returns:
            WindowListResult: Result object containing list of windows and error message if any.
        """
        from agentbay.window import WindowManager
        window_manager = WindowManager(self.session)
        return window_manager.list_root_windows(timeout_ms)

    def get_active_window(self, timeout_ms: int = 3000) -> WindowInfoResult:
        """
        Gets the currently active window.

        Args:
            timeout_ms (int, optional): Timeout in milliseconds. Defaults to 3000.
        Returns:
            WindowInfoResult: Result object containing active window info and error message if any.
        """
        from agentbay.window import WindowManager
        window_manager = WindowManager(self.session)
        return window_manager.get_active_window(timeout_ms)

    def activate_window(self, window_id: int) -> BoolResult:
        """
        Activates the specified window.

        Args:
            window_id (int): The ID of the window to activate.

        Returns:
            BoolResult: Result object containing success status and error message if any.
        """
        from agentbay.window import WindowManager
        window_manager = WindowManager(self.session)
        return window_manager.activate_window(window_id)

    def close_window(self, window_id: int) -> BoolResult:
        """
        Closes the specified window.

        Args:
            window_id (int): The ID of the window to close.

        Returns:
            BoolResult: Result object containing success status and error message if any.
        """
        from agentbay.window import WindowManager
        window_manager = WindowManager(self.session)
        return window_manager.close_window(window_id)

    def maximize_window(self, window_id: int) -> BoolResult:
        """
        Maximizes the specified window.

        Args:
            window_id (int): The ID of the window to maximize.

        Returns:
            BoolResult: Result object containing success status and error message if any.
        """
        from agentbay.window import WindowManager
        window_manager = WindowManager(self.session)
        return window_manager.maximize_window(window_id)

    def minimize_window(self, window_id: int) -> BoolResult:
        """
        Minimizes the specified window.

        Args:
            window_id (int): The ID of the window to minimize.

        Returns:
            BoolResult: Result object containing success status and error message if any.
        """
        from agentbay.window import WindowManager
        window_manager = WindowManager(self.session)
        return window_manager.minimize_window(window_id)

    def restore_window(self, window_id: int) -> BoolResult:
        """
        Restores the specified window.

        Args:
            window_id (int): The ID of the window to restore.

        Returns:
            BoolResult: Result object containing success status and error message if any.
        """
        from agentbay.window import WindowManager
        window_manager = WindowManager(self.session)
        return window_manager.restore_window(window_id)

    def resize_window(self, window_id: int, width: int, height: int) -> BoolResult:
        """
        Resizes the specified window.

        Args:
            window_id (int): The ID of the window to resize.
            width (int): New width of the window.
            height (int): New height of the window.

        Returns:
            BoolResult: Result object containing success status and error message if any.
        """
        from agentbay.window import WindowManager
        window_manager = WindowManager(self.session)
        return window_manager.resize_window(window_id, width, height)

    def fullscreen_window(self, window_id: int) -> BoolResult:
        """
        Makes the specified window fullscreen.

        Args:
            window_id (int): The ID of the window to make fullscreen.

        Returns:
            BoolResult: Result object containing success status and error message if any.
        """
        from agentbay.window import WindowManager
        window_manager = WindowManager(self.session)
        return window_manager.fullscreen_window(window_id)

    def focus_mode(self, on: bool) -> BoolResult:
        """
        Toggles focus mode on or off.

        Args:
            on (bool): True to enable focus mode, False to disable it.

        Returns:
            BoolResult: Result object containing success status and error message if any.
        """
        from agentbay.window import WindowManager
        window_manager = WindowManager(self.session)
        return window_manager.focus_mode(on)

    # Application Management Operations (delegated to existing application module)
    def get_installed_apps(
        self, start_menu: bool = True, desktop: bool = False, ignore_system_apps: bool = True
    ) -> InstalledAppListResult:
        """
        Gets the list of installed applications.

        Args:
            start_menu (bool, optional): Whether to include start menu applications. Defaults to True.
            desktop (bool, optional): Whether to include desktop applications. Defaults to False.
            ignore_system_apps (bool, optional): Whether to ignore system applications. Defaults to True.

        Returns:
            InstalledAppListResult: Result object containing list of installed apps and error message if any.
        """
        from agentbay.application import ApplicationManager
        app_manager = ApplicationManager(self.session)
        return app_manager.get_installed_apps(start_menu, desktop, ignore_system_apps)

    def start_app(self, start_cmd: str, work_directory: str = "", activity: str = "") -> ProcessListResult:
        """
        Starts the specified application.

        Args:
            start_cmd (str): The command to start the application.
            work_directory (str, optional): Working directory for the application. Defaults to "".
            activity (str, optional): Activity name to launch (for mobile apps). Defaults to "".

        Returns:
            ProcessListResult: Result object containing list of processes started and error message if any.
        """
        from agentbay.application import ApplicationManager
        app_manager = ApplicationManager(self.session)
        return app_manager.start_app(start_cmd, work_directory, activity)

    def list_visible_apps(self):
        """
        Lists all visible applications.

        Returns:
            Result object containing list of visible apps and error message if any.
        """
        from agentbay.application import ApplicationManager
        app_manager = ApplicationManager(self.session)
        return app_manager.list_visible_apps()

    def stop_app_by_pname(self, pname: str) -> AppOperationResult:
        """
        Stops an application by process name.

        Args:
            pname (str): The process name of the application to stop.

        Returns:
            AppOperationResult: Result object containing success status and error message if any.
        """
        from agentbay.application import ApplicationManager
        app_manager = ApplicationManager(self.session)
        return app_manager.stop_app_by_pname(pname)

    def stop_app_by_pid(self, pid: int) -> AppOperationResult:
        """
        Stops an application by process ID.

        Args:
            pid (int): The process ID of the application to stop.

        Returns:
            AppOperationResult: Result object containing success status and error message if any.
        """
        from agentbay.application import ApplicationManager
        app_manager = ApplicationManager(self.session)
        return app_manager.stop_app_by_pid(pid)

    def stop_app_by_cmd(self, stop_cmd: str) -> AppOperationResult:
        """
        Stops an application by stop command.

        Args:
            stop_cmd (str): The command to stop the application.

        Returns:
            AppOperationResult: Result object containing success status and error message if any.
        """
        from agentbay.application import ApplicationManager
        app_manager = ApplicationManager(self.session)
        return app_manager.stop_app_by_cmd(stop_cmd)

    def list_visible_apps(self) -> ProcessListResult:
        """
        Lists all applications with visible windows.
        
        Returns detailed process information for applications that have visible windows,
        including process ID, name, command line, and other system information.
        This is useful for system monitoring and process management tasks.

        Returns:
            ProcessListResult: Result object containing list of visible applications
                with detailed process information.
        """
        from agentbay.application import ApplicationManager
        app_manager = ApplicationManager(self.session)
        return app_manager.list_visible_apps() 