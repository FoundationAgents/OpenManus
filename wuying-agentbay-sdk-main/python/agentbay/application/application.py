import json
from typing import Any, Dict, List, Optional

from agentbay.api.base_service import BaseService
from agentbay.deprecation import deprecated
from agentbay.exceptions import AgentBayError, ApplicationError
from agentbay.model import ApiResponse


class InstalledApp:
    """
    Represents an installed application.

    Attributes:
        name (str): The name of the application.
        start_cmd (str): The command to start the application.
        stop_cmd (Optional[str]): The command to stop the application.
        work_directory (Optional[str]): The working directory for the application.
    """

    def __init__(
        self,
        name: str,
        start_cmd: str,
        stop_cmd: Optional[str] = None,
        work_directory: Optional[str] = None,
    ):
        """
        Initialize an InstalledApp object.

        Args:
            name (str): The name of the application.
            start_cmd (str): The command to start the application.
            stop_cmd (Optional[str], optional): The command to stop the application.
                Defaults to None.
            work_directory (Optional[str], optional): The working directory for the
                application. Defaults to None.
        """
        self.name = name
        self.start_cmd = start_cmd
        self.stop_cmd = stop_cmd
        self.work_directory = work_directory

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InstalledApp":
        """
        Create an InstalledApp object from a dictionary.

        Args:
            data (Dict[str, Any]): The dictionary containing the application data.

        Returns:
            InstalledApp: The created InstalledApp object.
        """
        return cls(
            name=data.get("name", ""),
            start_cmd=data.get("start_cmd", ""),
            stop_cmd=data.get("stop_cmd"),
            work_directory=data.get("work_directory"),
        )

    def __repr__(self):
        return (
            f"InstalledApp(name='{self.name}', "
            f"start_cmd='{self.start_cmd}', "
            f"stop_cmd='{self.stop_cmd}', "
            f"work_directory='{self.work_directory}')"
        )


class Process:
    """
    Represents a running process.

    Attributes:
        pname (str): The name of the process.
        pid (int): The process ID.
        cmdline (Optional[str]): The command line used to start the process.
    """

    def __init__(self, pname: str, pid: int, cmdline: Optional[str] = None):
        """
        Initialize a Process object.

        Args:
            pname (str): The name of the process.
            pid (int): The process ID.
            cmdline (Optional[str], optional): The command line used to start the
                process. Defaults to None.
        """
        self.pname = pname
        self.pid = pid
        self.cmdline = cmdline

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Process":
        """
        Create a Process object from a dictionary.

        Args:
            data (Dict[str, Any]): The dictionary containing the process data.

        Returns:
            Process: The created Process object.
        """
        return cls(
            pname=data.get("pname", ""),
            pid=data.get("pid", 0),
            cmdline=data.get("cmdline"),
        )

    def __repr__(self):
        return (
            f"Process(pname='{self.pname}', "
            f"pid={self.pid}, "
            f"cmdline='{self.cmdline}')"
        )


class ProcessListResult(ApiResponse):
    """Result of operations returning a list of Processes."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        data: Optional[List[Process]] = None,
        error_message: str = "",
    ):
        """
        Initialize a ProcessListResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
                Defaults to "".
            success (bool, optional): Whether the operation was successful.
                Defaults to False.
            data (Optional[List[Process]], optional): The list of process objects.
                Defaults to None.
            error_message (str, optional): Error message if the operation failed.
                Defaults to "".
        """
        super().__init__(request_id)
        self.success = success
        self.data = data if data is not None else []
        self.error_message = error_message


class InstalledAppListResult(ApiResponse):
    """Result of operations returning a list of InstalledApps."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        data: Optional[List[InstalledApp]] = None,
        error_message: str = "",
    ):
        """
        Initialize an InstalledAppListResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
            success (bool, optional): Whether the operation was successful.
            data (Optional[List[InstalledApp]], optional): The list of installed
                app objects.
            error_message (str, optional): Error message if the operation failed.
        """
        super().__init__(request_id)
        self.success = success
        self.data = data if data is not None else []
        self.error_message = error_message


class AppInfoResult(ApiResponse):
    """Result of application info operations."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        app_info: Optional[Dict[str, Any]] = None,
        error_message: str = "",
    ):
        """
        Initialize an AppInfoResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
            success (bool, optional): Whether the operation was successful.
            app_info (Dict[str, Any], optional): Application information.
            error_message (str, optional): Error message if the operation failed.
        """
        super().__init__(request_id)
        self.success = success
        self.app_info = app_info or {}
        self.error_message = error_message


class AppListResult(ApiResponse):
    """Result of application listing operations."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        apps: Optional[List[Dict[str, Any]]] = None,
        error_message: str = "",
    ):
        """
        Initialize an AppListResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
            success (bool, optional): Whether the operation was successful.
            apps (List[Dict[str, Any]], optional): List of applications.
            error_message (str, optional): Error message if the operation failed.
        """
        super().__init__(request_id)
        self.success = success
        self.apps = apps or []
        self.error_message = error_message


class AppOperationResult(ApiResponse):
    """Result of application operations like start/stop."""

    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        error_message: str = "",
    ):
        """
        Initialize an AppOperationResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
            success (bool, optional): Whether the operation was successful.
            error_message (str, optional): Error message if the operation failed.
        """
        super().__init__(request_id)
        self.success = success
        self.error_message = error_message


class AppInstallResult(ApiResponse):
    """Result of application installation operations."""

    def __init__(self, request_id: str = "", success: bool = False, message: str = ""):
        """
        Initialize an AppInstallResult.

        Args:
            request_id (str, optional): Unique identifier for the API request.
            success (bool, optional): Whether the installation was successful.
            message (str, optional): Result description or error message.
        """
        super().__init__(request_id)
        self.success = success
        self.message = message


class ApplicationManager(BaseService):
    """
    Handles application operations in the AgentBay cloud environment.
    """

    def _handle_error(self, e):
        """
        Convert AgentBayError to ApplicationError for compatibility.

        Args:
            e (Exception): The exception to convert.

        Returns:
            ApplicationError: The converted exception.
        """
        if isinstance(e, ApplicationError):
            return e
        if isinstance(e, AgentBayError):
            return ApplicationError(str(e))
        return e

    @deprecated(


        reason="Application management has been moved to platform-specific modules",


        replacement="session.computer.get_installed_apps() or session.mobile.get_installed_apps()",


        version="2.0.0"


    )


    def get_installed_apps(
        self, start_menu: bool, desktop: bool, ignore_system_apps: bool
    ) -> InstalledAppListResult:
        """
        Retrieves a list of installed applications.

        Args:
            start_menu (bool): Whether to include start menu applications.
            desktop (bool): Whether to include desktop applications.
            ignore_system_apps (bool): Whether to ignore system applications.

        Returns:
            InstalledAppListResult: The result containing the list of installed
                applications.
        """
        try:
            args = {
                "start_menu": start_menu,
                "desktop": desktop,
                "ignore_system_apps": ignore_system_apps,
            }

            result = self._call_mcp_tool("get_installed_apps", args)

            if not result.success:
                return InstalledAppListResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message,
                )

            try:
                apps_json = json.loads(result.data)
                installed_apps = []

                for app_data in apps_json:
                    app = InstalledApp.from_dict(app_data)
                    installed_apps.append(app)

                return InstalledAppListResult(
                    request_id=result.request_id,
                    success=True,
                    data=installed_apps,
                )
            except json.JSONDecodeError as e:
                return InstalledAppListResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=f"Failed to parse applications JSON: {e}",
                )
        except Exception as e:
            handled_error = self._handle_error(e)
            return InstalledAppListResult(
                success=False, error_message=str(handled_error)
            )

    @deprecated(


        reason="Application management has been moved to platform-specific modules",


        replacement="session.computer.start_app() or session.mobile.start_app()",


        version="2.0.0"


    )


    def start_app(
        self, start_cmd: str, work_directory: str = "", activity: str = ""
    ) -> ProcessListResult:
        """
        Starts an application with the given command, optional working directory and
            optional activity.

        Args:
            start_cmd (str): The command to start the application.
            work_directory (str, optional): The working directory for the application.
            activity (str, optional): Activity name to launch (e.g. ".SettingsActivity"
                or "com.package/.Activity"). Defaults to "".

        Returns:
            ProcessListResult: The result containing the list of processes started.
        """
        try:
            args = {"start_cmd": start_cmd}
            if work_directory:
                args["work_directory"] = work_directory
            if activity:
                args["activity"] = activity

            result = self._call_mcp_tool("start_app", args)

            if not result.success:
                return ProcessListResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message,
                )

            try:
                processes_json = json.loads(result.data)
                processes = []

                for process_data in processes_json:
                    process = Process.from_dict(process_data)
                    processes.append(process)

                return ProcessListResult(
                    request_id=result.request_id, success=True, data=processes
                )
            except json.JSONDecodeError as e:
                return ProcessListResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=f"Failed to parse processes JSON: {e}",
                )
        except Exception as e:
            handled_error = self._handle_error(e)
            return ProcessListResult(success=False, error_message=str(handled_error))

    @deprecated(


        reason="Application management has been moved to platform-specific modules",


        replacement="session.computer.stop_app_by_pname() or session.mobile.stop_app_by_pname()",


        version="2.0.0"


    )


    def stop_app_by_pname(self, pname: str) -> AppOperationResult:
        """
        Stops an application by process name.

        Args:
            pname (str): The name of the process to stop.

        Returns:
            AppOperationResult: The result of the operation.
        """
        try:
            args = {"pname": pname}
            result = self._call_mcp_tool("stop_app_by_pname", args)

            return AppOperationResult(
                request_id=result.request_id,
                success=result.success,
                error_message=result.error_message,
            )
        except Exception as e:
            handled_error = self._handle_error(e)
            return AppOperationResult(success=False, error_message=str(handled_error))

    @deprecated(


        reason="Application management has been moved to platform-specific modules",


        replacement="session.computer.stop_app_by_pid()",


        version="2.0.0"


    )


    def stop_app_by_pid(self, pid: int) -> AppOperationResult:
        """
        Stops an application by process ID.

        Args:
            pid (int): The process ID to stop.

        Returns:
            AppOperationResult: The result of the operation.
        """
        try:
            args = {"pid": pid}
            result = self._call_mcp_tool("stop_app_by_pid", args)

            return AppOperationResult(
                request_id=result.request_id,
                success=result.success,
                error_message=result.error_message,
            )
        except Exception as e:
            handled_error = self._handle_error(e)
            return AppOperationResult(success=False, error_message=str(handled_error))

    @deprecated(


        reason="Application management has been moved to platform-specific modules",


        replacement="session.computer.stop_app_by_cmd()",


        version="2.0.0"


    )


    def stop_app_by_cmd(self, stop_cmd: str) -> AppOperationResult:
        """
        Stops an application by stop command.

        Args:
            stop_cmd (str): The command to stop the application.

        Returns:
            AppOperationResult: The result of the operation.
        """
        try:
            args = {"stop_cmd": stop_cmd}
            result = self._call_mcp_tool("stop_app_by_cmd", args)

            return AppOperationResult(
                request_id=result.request_id,
                success=result.success,
                error_message=result.error_message,
            )
        except Exception as e:
            handled_error = self._handle_error(e)
            return AppOperationResult(success=False, error_message=str(handled_error))

    @deprecated(
        reason="Application management has been moved to platform-specific modules",
        replacement="session.computer.list_visible_apps()",
        version="2.0.0"
    )
    def list_visible_apps(self) -> ProcessListResult:
        """
        Returns a list of currently visible applications.

        Returns:
            ProcessListResult: The result containing the list of visible
                applications/processes.
        """
        try:
            result = self._call_mcp_tool("list_visible_apps", {})

            if not result.success:
                return ProcessListResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=result.error_message,
                )

            try:
                processes_json = json.loads(result.data)
                processes = []

                for process_data in processes_json:
                    process = Process.from_dict(process_data)
                    processes.append(process)

                return ProcessListResult(
                    request_id=result.request_id, success=True, data=processes
                )
            except json.JSONDecodeError as e:
                return ProcessListResult(
                    request_id=result.request_id,
                    success=False,
                    error_message=f"Failed to parse processes JSON: {e}",
                )
        except Exception as e:
            handled_error = self._handle_error(e)
            return ProcessListResult(success=False, error_message=str(handled_error))
