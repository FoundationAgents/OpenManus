# ApplicationManager Class

> **⚠️ DEPRECATED**: This API is deprecated. Please use the [Computer API](computer.md) instead for application management functionality.

The ApplicationManager class provides methods for managing applications in the AgentBay cloud environment, including listing installed applications, starting applications, and stopping running processes.

## Class Properties

###

```python
class ApplicationManager:
    def __init__(self, session):
        self.session = session
```

## Data Types


Represents an installed application.


```python
class InstalledApp:
    name: str          # The name of the application
    start_cmd: str     # The command used to start the application
    stop_cmd: str      # The command used to stop the application (optional)
    work_directory: str # The working directory for the application (optional)
```


```python
class Process:
    pname: str    # The name of the process
    pid: int      # The process ID
    cmdline: Optional[str]  # The command line used to start the process (optional)
```

## Result Types

```python
class ProcessListResult(ApiResponse):
    success: bool
    data: List[Process]
    error_message: str
```

```python
class InstalledAppListResult(ApiResponse):
    success: bool
    data: List[InstalledApp]
    error_message: str
```

```python
class AppInfoResult(ApiResponse):
    success: bool
    app_info: Dict[str, Any]
    error_message: str
```

```python
class AppListResult(ApiResponse):
    success: bool
    apps: List[Dict[str, Any]]
    error_message: str
```

```python
class AppOperationResult(ApiResponse):
    success: bool
    error_message: str
```

```python
class AppInstallResult(ApiResponse):
    success: bool
    message: str
```


```python
def get_installed_apps(self, start_menu: bool, desktop: bool, ignore_system_apps: bool) -> InstalledAppListResult:
```

**Parameters:**
- `start_menu` (bool): Whether to include start menu applications.
- `desktop` (bool): Whether to include desktop applications.
- `ignore_system_apps` (bool): Whether to ignore system applications.

**Returns:**
- `InstalledAppListResult`: The result containing the list of installed applications.

**Raises:**
- `ApplicationError`: If there's an error retrieving the installed applications.


```python
def start_app(self, start_cmd: str, work_directory: str = "", activity: str = "") -> ProcessListResult:
```

**Parameters:**
- `start_cmd` (str): The command to start the application.
- `work_directory` (str, optional): The working directory for the application.
- `activity` (str, optional): Activity name to launch (e.g. ".SettingsActivity" or "com.package/.Activity").

**Returns:**
- `ProcessListResult`: The result containing the list of processes started.

**Raises:**
- `ApplicationError`: If there's an error starting the application.


```python
def stop_app_by_pname(self, pname: str) -> AppOperationResult:
```

**Parameters:**
- `pname` (str): The name of the process to stop.

**Returns:**
- `AppOperationResult`: The result of the operation.

**Raises:**
- `ApplicationError`: If there's an error stopping the application.


```python
def stop_app_by_pid(self, pid: int) -> AppOperationResult:
```

**Parameters:**
- `pid` (int): The process ID to stop.

**Returns:**
- `AppOperationResult`: The result of the operation.

**Raises:**
- `ApplicationError`: If there's an error stopping the application.


```python
def stop_app_by_cmd(self, stop_cmd: str) -> AppOperationResult:
```

**Parameters:**
- `stop_cmd` (str): The command to stop the application.

**Returns:**
- `AppOperationResult`: The result of the operation.

**Raises:**
- `ApplicationError`: If there's an error stopping the application.


```python
def list_visible_apps(self) -> ProcessListResult:
```

**Returns:**
- `ProcessListResult`: The result containing the list of visible applications/processes.

**Raises:**
- `ApplicationError`: If there's an error listing the visible applications.
