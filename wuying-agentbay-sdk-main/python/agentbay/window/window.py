import json
from typing import Any, Dict, List, Optional

from agentbay.api.base_service import BaseService
from agentbay.deprecation import deprecated
from agentbay.model import ApiResponse, BoolResult


class WindowListResult(ApiResponse):
    """Result of window listing operations."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        windows: Optional[List[Any]] = None,
        error_message: str = "",
    ):
        """
        Initialize a WindowListResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
                Defaults to "".
            success (bool, optional): Whether the operation was successful.
                Defaults to False.
            windows (List[Any], optional): List of Windows. Defaults to None.
            error_message (str, optional): Error message if the operation failed.
                Defaults to "".
        """
        super().__init__(request_id)
        self.success = success
        self.windows = windows or []
        self.error_message = error_message


class WindowInfoResult(ApiResponse):
    """Result of window info operations."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        window: Any = None,
        error_message: str = "",
    ):
        """
        Initialize a WindowInfoResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
                Defaults to "".
            success (bool, optional): Whether the operation was successful.
                Defaults to False.
            window (Any, optional): Window object. Defaults to None.
            error_message (str, optional): Error message if the operation failed.
                Defaults to "".
        """
        super().__init__(request_id)
        self.success = success
        self.window = window
        self.error_message = error_message


class Window:
    """
    Represents a window in the system.

    Attributes:
        window_id (int): The ID of the window.
        title (str): The title of the window.
        absolute_upper_left_x (Optional[int]): The x-coordinate of the upper left corner
            of the window.
        absolute_upper_left_y (Optional[int]): The y-coordinate of the upper left corner
            of the window.
        width (Optional[int]): The width of the window.
        height (Optional[int]): The height of the window.
        pid (Optional[int]): The process ID of the window.
        pname (Optional[str]): The process name of the window.
        child_windows (List['Window']): The child windows of this window.
    """

    def __init__(
        self,
        window_id: int,
        title: str,
        absolute_upper_left_x: Optional[int] = None,
        absolute_upper_left_y: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        pid: Optional[int] = None,
        pname: Optional[str] = None,
        child_windows: Optional[List["Window"]] = None,
    ):
        """
        Initialize a Window object.

        Args:
            window_id (int): The ID of the window.
            title (str): The title of the window.
            absolute_upper_left_x (Optional[int], optional): The x-coordinate of the
                upper left corner of the window. Defaults to None.
            absolute_upper_left_y (Optional[int], optional): The y-coordinate of the
                upper left corner of the window. Defaults to None.
            width (Optional[int], optional): The width of the window.
                Defaults to None.
            height (Optional[int], optional): The height of the window.
                Defaults to None.
            pid (Optional[int], optional): The process ID of the window.
                Defaults to None.
            pname (Optional[str], optional): The process name of the window.
                Defaults to None.
            child_windows (Optional[List['Window']], optional): The child windows of
                this window. Defaults to None.
        """
        self.window_id = window_id
        self.title = title
        self.absolute_upper_left_x = absolute_upper_left_x
        self.absolute_upper_left_y = absolute_upper_left_y
        self.width = width
        self.height = height
        self.pid = pid
        self.pname = pname
        self.child_windows = child_windows or []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Window":
        """
        Create a Window object from a dictionary.

        Args:
            data (Dict[str, Any]): The dictionary containing the window data.

        Returns:
            Window: The created Window object.
        """
        child_windows = []
        if "child_windows" in data and data["child_windows"]:
            child_windows = [cls.from_dict(child) for child in data["child_windows"]]

        return cls(
            window_id=data.get("window_id", 0),
            title=data.get("title", ""),
            absolute_upper_left_x=data.get("absolute_upper_left_x"),
            absolute_upper_left_y=data.get("absolute_upper_left_y"),
            width=data.get("width"),
            height=data.get("height"),
            pid=data.get("pid"),
            pname=data.get("pname"),
            child_windows=child_windows,
        )


class WindowManager(BaseService):
    """
    Handles window management operations in the AgentBay cloud environment.
    """

    @deprecated(
        reason="Window management has been moved to Computer module",
        replacement="session.computer.list_root_windows()",
        version="2.0.0"
    )
    def list_root_windows(self, timeout_ms: int = 3000) -> WindowListResult:
        """
        Lists all root windows in the system.

        Returns:
            WindowListResult: Result object containing list of windows and error
                message if any.
        """
        args = {"timeout_ms": timeout_ms}

        try:
            result = self._call_mcp_tool("list_root_windows", args)
            if not result.success:
                return WindowListResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message,
                )

            data = json.loads(result.data)
            windows = [Window.from_dict(window) for window in data]
            return WindowListResult(
                request_id=result.request_id, success=True, windows=windows
            )
        except Exception as e:
            return WindowListResult(
                request_id="",
                success=False,
                error_message=f"Failed to list root windows: {e}",
            )

    @deprecated(
        reason="Window management has been moved to Computer module",
        replacement="session.computer.get_active_window()",
        version="2.0.0"
    )
    def get_active_window(self, timeout_ms: int = 3000) -> WindowInfoResult:
        """
        Gets the currently active window.

        Returns:
            WindowInfoResult: Result object containing window information and error
                message if any.
        """
        args = {"timeout_ms": timeout_ms}

        try:
            result = self._call_mcp_tool("get_active_window", args)
            if not result.success:
                return WindowInfoResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message,
                )

            data = json.loads(result.data)
            window = Window.from_dict(data)
            return WindowInfoResult(
                request_id=result.request_id, success=True, window=window
            )
        except Exception as e:
            return WindowInfoResult(
                request_id="",
                success=False,
                error_message=f"Failed to get active window: {e}",
            )

    @deprecated(
        reason="Window management has been moved to Computer module",
        replacement="session.computer.activate_window()",
        version="2.0.0"
    )
    def activate_window(self, window_id: int) -> BoolResult:
        """
        Activates a window by its ID.

        Args:
            window_id (int): The ID of the window to activate.

        Returns:
            BoolResult: Result object containing success status and error
                message if any.
        """
        args = {"window_id": window_id}

        try:
            result = self._call_mcp_tool("activate_window", args)
            if not result.success:
                return BoolResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message,
                )

            return BoolResult(request_id=result.request_id, success=True, data=True)
        except Exception as e:
            return BoolResult(
                request_id="",
                success=False,
                error_message=f"Failed to activate window: {e}",
            )

    @deprecated(


        reason="Window management has been moved to Computer module",


        replacement="session.computer.maximize_window()",


        version="2.0.0"


    )


    def maximize_window(self, window_id: int) -> BoolResult:
        """
        Maximizes a window by its ID.

        Args:
            window_id (int): The ID of the window to maximize.

        Returns:
            BoolResult: Result object containing success status and error
                message if any.
        """
        args = {"window_id": window_id}

        try:
            result = self._call_mcp_tool("maximize_window", args)
            if not result.success:
                return BoolResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message,
                )

            return BoolResult(request_id=result.request_id, success=True, data=True)
        except Exception as e:
            return BoolResult(
                request_id="",
                success=False,
                error_message=f"Failed to maximize window: {e}",
            )

    @deprecated(


        reason="Window management has been moved to Computer module",


        replacement="session.computer.minimize_window()",


        version="2.0.0"


    )


    def minimize_window(self, window_id: int) -> BoolResult:
        """
        Minimizes a window by its ID.

        Args:
            window_id (int): The ID of the window to minimize.

        Returns:
            BoolResult: Result object containing success status and error
                message if any.
        """
        args = {"window_id": window_id}

        try:
            result = self._call_mcp_tool("minimize_window", args)
            if not result.success:
                return BoolResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message,
                )

            return BoolResult(request_id=result.request_id, success=True, data=True)
        except Exception as e:
            return BoolResult(
                request_id="",
                success=False,
                error_message=f"Failed to minimize window: {e}",
            )

    @deprecated(


        reason="Window management has been moved to Computer module",


        replacement="session.computer.restore_window()",


        version="2.0.0"


    )


    def restore_window(self, window_id: int) -> BoolResult:
        """
        Restores a window by its ID.

        Args:
            window_id (int): The ID of the window to restore.

        Returns:
            BoolResult: Result object containing success status and error
                message if any.
        """
        args = {"window_id": window_id}

        try:
            result = self._call_mcp_tool("restore_window", args)
            if not result.success:
                return BoolResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message,
                )

            return BoolResult(request_id=result.request_id, success=True, data=True)
        except Exception as e:
            return BoolResult(
                request_id="",
                success=False,
                error_message=f"Failed to restore window: {e}",
            )

    @deprecated(


        reason="Window management has been moved to Computer module",


        replacement="session.computer.close_window()",


        version="2.0.0"


    )


    def close_window(self, window_id: int) -> BoolResult:
        """
        Closes a window by its ID.

        Args:
            window_id (int): The ID of the window to close.

        Returns:
            BoolResult: Result object containing success status and error
                message if any.
        """
        args = {"window_id": window_id}

        try:
            result = self._call_mcp_tool("close_window", args)
            if not result.success:
                return BoolResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message,
                )

            return BoolResult(request_id=result.request_id, success=True, data=True)
        except Exception as e:
            return BoolResult(
                request_id="",
                success=False,
                error_message=f"Failed to close window: {e}",
            )

    @deprecated(


        reason="Window management has been moved to Computer module",


        replacement="session.computer.fullscreen_window()",


        version="2.0.0"


    )


    def fullscreen_window(self, window_id: int) -> BoolResult:
        """
        Makes a window fullscreen by its ID.

        Args:
            window_id (int): The ID of the window to make fullscreen.

        Returns:
            BoolResult: Result object containing success status and error
                message if any.
        """
        args = {"window_id": window_id}

        try:
            result = self._call_mcp_tool("fullscreen_window", args)
            if not result.success:
                return BoolResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message,
                )

            return BoolResult(request_id=result.request_id, success=True, data=True)
        except Exception as e:
            return BoolResult(
                request_id="",
                success=False,
                error_message=f"Failed to make window fullscreen: {e}",
            )

    @deprecated(


        reason="Window management has been moved to Computer module",


        replacement="session.computer.resize_window()",


        version="2.0.0"


    )


    def resize_window(self, window_id: int, width: int, height: int) -> BoolResult:
        """
        Resizes a window by its ID.

        Args:
            window_id (int): The ID of the window to resize.
            width (int): The new width of the window.
            height (int): The new height of the window.

        Returns:
            BoolResult: Result object containing success status and error
                message if any.
        """
        args = {"window_id": window_id, "width": width, "height": height}

        try:
            result = self._call_mcp_tool("resize_window", args)
            if not result.success:
                return BoolResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message,
                )

            return BoolResult(request_id=result.request_id, success=True, data=True)
        except Exception as e:
            return BoolResult(
                request_id="",
                success=False,
                error_message=f"Failed to resize window: {e}",
            )

    @deprecated(


        reason="Window management has been moved to Computer module",


        replacement="session.computer.focus_mode()",


        version="2.0.0"


    )


    def focus_mode(self, on: bool) -> BoolResult:
        """
        Toggles focus mode on or off.

        Args:
            on (bool): True to enable focus mode, False to disable it.

        Returns:
            BoolResult: Result object containing success status and error
                message if any.
        """
        args = {"on": on}

        try:
            result = self._call_mcp_tool("focus_mode", args)
            if not result.success:
                return BoolResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message,
                )

            return BoolResult(request_id=result.request_id, success=True, data=True)
        except Exception as e:
            return BoolResult(
                request_id="",
                success=False,
                error_message=f"Failed to toggle focus mode: {e}",
            )
