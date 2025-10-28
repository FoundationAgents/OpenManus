# Application Management for Computer Use

This guide covers application management capabilities for desktop environments (Windows/Linux) using the AgentBay SDK. Learn how to discover, launch, monitor, and control desktop applications in cloud environments.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Getting Installed Applications](#getting-installed-applications)
- [Starting Applications](#starting-applications)
- [Stopping Applications](#stopping-applications)
- [Listing Running Applications](#listing-running-applications)
- [Complete Workflow Example](#complete-workflow-example)
- [API Reference](#api-reference)

<a id="overview"></a>
## 🎯 Overview

The Computer Use module provides comprehensive application management capabilities for desktop environments:

1. **Application Discovery** - Find installed applications in the system
2. **Application Lifecycle** - Start and stop desktop applications
3. **Process Monitoring** - Track running applications and their processes
4. **Desktop Automation** - Automate complex desktop workflows

These features have been tested and verified on `windows_latest` and `linux_latest` system images.

<a id="prerequisites"></a>
## 📦 Prerequisites

First, create a session with a desktop environment:

```python
import os
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

api_key = os.getenv("AGENTBAY_API_KEY")
if not api_key:
    raise ValueError("AGENTBAY_API_KEY environment variable is required")

agent_bay = AgentBay(api_key=api_key)

params = CreateSessionParams(image_id="linux_latest")
result = agent_bay.create(params)

if result.success:
    session = result.session
    print(f"Session created: {session.session_id}")
    # Output: Session created: session-xxxxxxxxxxxxxxxxx
else:
    print(f"Failed to create session: {result.error_message}")
    exit(1)
```

<a id="getting-installed-applications"></a>
## 🔍 Getting Installed Applications

Discover all applications available in the desktop environment:

```python
result = session.computer.get_installed_apps(
    start_menu=True,
    desktop=False,
    ignore_system_apps=True
)

# Verification: Result type is InstalledAppListResult
# Verification: Success = True
# Verification: Found 76 installed applications on test system

if result.success:
    apps = result.data
    print(f"Found {len(apps)} installed applications")
    # Output: Found 76 installed applications
    
    for app in apps[:5]:
        print(f"Name: {app.name}")
        print(f"Start Command: {app.start_cmd}")
        print(f"Stop Command: {app.stop_cmd if app.stop_cmd else 'N/A'}")
        print(f"Work Directory: {app.work_directory if app.work_directory else 'N/A'}")
        print("---")
    # Output example:
    # Name: AptURL
    # Start Command: apturl %u
    # Stop Command: N/A
    # Work Directory: N/A
    # ---
    # Name: Bluetooth Transfer
    # Start Command: bluetooth-sendto
    # Stop Command: N/A
    # Work Directory: N/A
    # ---
else:
    print(f"Error: {result.error_message}")
```

**Parameters:**
- `start_menu` (bool): Whether to include start menu applications
- `desktop` (bool): Whether to include desktop applications
- `ignore_system_apps` (bool): Whether to filter out system applications

**Returns:**
- `InstalledAppListResult` containing a list of `InstalledApp` objects

<a id="starting-applications"></a>
## 🚀 Starting Applications

Launch desktop applications using their start commands:

### Method 1: Start by Command

```python
start_cmd = "/usr/bin/google-chrome-stable"

result = session.computer.start_app(start_cmd)

# Verification: Result type is ProcessListResult
# Verification: Success = True
# Verification: Started 6 processes (chrome main process + helper processes)

if result.success:
    processes = result.data
    print(f"Application started with {len(processes)} processes")
    # Output: Application started with 6 processes
    
    for process in processes:
        print(f"Process: {process.pname} (PID: {process.pid})")
    # Output example:
    # Process: chrome (PID: 4443)
    # Process: cat (PID: 4448)
    # Process: cat (PID: 4449)
    # Process: chrome (PID: 4459)
    # Process: chrome (PID: 4460)
    # Process: chrome (PID: 4462)
else:
    print(f"Failed to start application: {result.error_message}")
```

### Method 2: Start with Working Directory

```python
start_cmd = "/usr/bin/google-chrome-stable"
work_directory = "/tmp"

result = session.computer.start_app(
    start_cmd=start_cmd,
    work_directory=work_directory
)

# Verification: Result type is ProcessListResult
# Verification: Success = True
# Verification: Application starts in the specified working directory

if result.success:
    processes = result.data
    print(f"Application started with {len(processes)} processes")
    # Output: Application started with 6 processes
else:
    print(f"Failed to start application: {result.error_message}")
```

### Method 3: Start from Installed Apps List

```python
result = session.computer.get_installed_apps(
    start_menu=True,
    desktop=False,
    ignore_system_apps=True
)

# Verification: Successfully retrieves installed apps list

if result.success:
    apps = result.data
    
    target_app = None
    for app in apps:
        if "chrome" in app.name.lower():
            target_app = app
            break
    
    # Verification: Found "Google Chrome" in the apps list
    
    if target_app:
        print(f"Starting {target_app.name}...")
        # Output: Starting Google Chrome...
        
        start_result = session.computer.start_app(target_app.start_cmd)
        
        # Verification: Successfully started the application
        
        if start_result.success:
            print("Application started successfully!")
            # Output: Application started successfully!
        else:
            print(f"Failed to start: {start_result.error_message}")
    else:
        print("Target application not found")
```

<a id="stopping-applications"></a>
## 🛑 Stopping Applications

Stop running applications using process ID, process name, or stop command:

### Method 1: Stop by Process ID (PID)

```python
start_result = session.computer.start_app("/usr/bin/google-chrome-stable")

# Verification: Application started successfully with multiple processes

if start_result.success:
    target_pid = None
    for process in start_result.data:
        print(f"Process: {process.pname} (PID: {process.pid})")
        # Output example:
        # Process: chrome (PID: 6378)
        # Process: cat (PID: 6383)
        # Process: cat (PID: 6384)
        
        if 'chrome' in process.pname.lower():
            target_pid = process.pid
            break
    
    if target_pid:
        result = session.computer.stop_app_by_pid(target_pid)
        
        # Verification: Result type is AppOperationResult
        # Verification: Success = True
        
        if result.success:
            print(f"Successfully stopped process {target_pid}")
            # Output: Successfully stopped process 6378
        else:
            print(f"Failed to stop process: {result.error_message}")
```

### Method 2: Stop by Process Name

```python
start_result = session.computer.start_app("/usr/bin/google-chrome-stable")

# Verification: Application started successfully

if start_result.success:
    target_pname = None
    for process in start_result.data:
        print(f"Process: {process.pname} (PID: {process.pid})")
        target_pname = process.pname
        break
    
    # Verification: Retrieved process name "chrome"
    
    if target_pname:
        result = session.computer.stop_app_by_pname(target_pname)
        
        # Verification: Result type is AppOperationResult
        # Verification: Success = True
        
        if result.success:
            print(f"Successfully stopped process {target_pname}")
            # Output: Successfully stopped process chrome
        else:
            print(f"Failed to stop process: {result.error_message}")
```

### Method 3: Stop by Stop Command

```python
result = session.computer.get_installed_apps(
    start_menu=True,
    desktop=False,
    ignore_system_apps=True
)

# Verification: Successfully retrieved installed apps

if result.success:
    apps = result.data
    
    target_app = None
    for app in apps:
        if app.stop_cmd:
            target_app = app
            break
    
    # Note: Most desktop apps on Linux don't have stop_cmd defined
    # This is normal - use stop_app_by_pid or stop_app_by_pname instead
    
    if target_app:
        start_result = session.computer.start_app(target_app.start_cmd)
        
        if start_result.success:
            print("Application started successfully!")
            
            result = session.computer.stop_app_by_cmd(target_app.stop_cmd)
            
            # Verification: Result type is AppOperationResult
            
            if result.success:
                print("Successfully stopped application using command")
            else:
                print(f"Failed to stop application: {result.error_message}")
```

<a id="listing-running-applications"></a>
## 📊 Listing Running Applications

Monitor currently running applications with visible windows:

```python
result = session.computer.list_visible_apps()

# Verification: Result type is ProcessListResult
# Verification: Success = True
# Verification: Found 1 visible application (chrome with visible window)

if result.success:
    visible_apps = result.data
    print(f"Found {len(visible_apps)} running applications")
    # Output: Found 1 running applications
    
    for app in visible_apps:
        print(f"Process: {app.pname}")
        print(f"PID: {app.pid}")
        print(f"Command: {app.cmdline}")
        print("---")
    # Output example:
    # Process: chrome
    # PID: 6378
    # Command: /opt/google/chrome/chrome
    # ---
else:
    print(f"Error: {result.error_message}")
```

**Process Object Properties:**
- `pname` (str): Process name
- `pid` (int): Process ID
- `cmdline` (str): Full command line used to start the process

<a id="complete-workflow-example"></a>
## 🔄 Complete Workflow Example

Complete example showing how to find, launch, and control a desktop application:

```python
import os
import time
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

api_key = os.getenv("AGENTBAY_API_KEY")
if not api_key:
    raise ValueError("AGENTBAY_API_KEY environment variable is required")

agent_bay = AgentBay(api_key=api_key)

params = CreateSessionParams(image_id="linux_latest")
result = agent_bay.create(params)

if not result.success:
    print(f"Failed to create session: {result.error_message}")
    exit(1)

session = result.session
print(f"Session created: {session.session_id}")
# Output: Session created: session-xxxxxxxxxxxxxxxxx

print("Step 1: Finding installed applications...")
apps_result = session.computer.get_installed_apps(
    start_menu=True,
    desktop=False,
    ignore_system_apps=True
)

# Verification: Successfully retrieved 76 applications

if not apps_result.success:
    print(f"Failed to get apps: {apps_result.error_message}")
    agent_bay.delete(session)
    exit(1)

target_app = None
for app in apps_result.data:
    if "chrome" in app.name.lower():
        target_app = app
        break

# Verification: Found "Google Chrome" application

if not target_app:
    print("Google Chrome not found")
    agent_bay.delete(session)
    exit(1)

print(f"Found application: {target_app.name}")
# Output: Found application: Google Chrome

print("Step 2: Launching application...")
start_result = session.computer.start_app(target_app.start_cmd)

# Verification: Successfully started with 6 processes

if not start_result.success:
    print(f"Failed to start app: {start_result.error_message}")
    agent_bay.delete(session)
    exit(1)

print(f"Application started with {len(start_result.data)} processes")
# Output: Application started with 6 processes

for process in start_result.data:
    print(f"  - {process.pname} (PID: {process.pid})")
# Output example:
#   - chrome (PID: 6420)
#   - cat (PID: 6425)
#   - cat (PID: 6426)
#   - chrome (PID: 6436)
#   - chrome (PID: 6437)
#   - chrome (PID: 6439)

print("Step 3: Waiting for application to load...")
time.sleep(5)

print("Step 4: Checking running applications...")
visible_result = session.computer.list_visible_apps()

# Verification: Found 1 visible application

if visible_result.success:
    print(f"Found {len(visible_result.data)} visible applications")
    # Output: Found 1 visible applications

print("Step 5: Stopping application...")
if start_result.data:
    stop_result = session.computer.stop_app_by_pid(start_result.data[0].pid)
    
    # Verification: Successfully stopped the application
    
    if stop_result.success:
        print("Application stopped successfully")
        # Output: Application stopped successfully
    else:
        print(f"Failed to stop application: {stop_result.error_message}")

print("Cleaning up session...")
agent_bay.delete(session)
print("Workflow completed!")
# Output: Workflow completed!

# === Complete Workflow Verification Results ===
# ✓ Session creation: Success
# ✓ Get installed apps: 76 applications found
# ✓ Find target app: Google Chrome found
# ✓ Start application: 6 processes started
# ✓ List visible apps: 1 visible application
# ✓ Stop application: Successfully stopped
# ✓ Session cleanup: Success
```

<a id="api-reference"></a>
## 📚 API Reference

### Computer Application Management Methods

All application management methods are accessed through `session.computer.*`:

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_installed_apps()` | `start_menu: bool = True`<br/>`desktop: bool = False`<br/>`ignore_system_apps: bool = True` | `InstalledAppListResult` | Get list of installed applications |
| `start_app()` | `start_cmd: str`<br/>`work_directory: str = ""`<br/>`activity: str = ""` | `ProcessListResult` | Start an application |
| `stop_app_by_pid()` | `pid: int` | `AppOperationResult` | Stop application by process ID |
| `stop_app_by_pname()` | `pname: str` | `AppOperationResult` | Stop application by process name |
| `stop_app_by_cmd()` | `stop_cmd: str` | `AppOperationResult` | Stop application by stop command |
| `list_visible_apps()` | None | `ProcessListResult` | List currently visible applications |

### Return Types

**InstalledAppListResult**
- `success` (bool): Whether the operation succeeded
- `data` (List[InstalledApp]): List of installed applications
- `error_message` (str): Error message if operation failed
- `request_id` (str): Unique request identifier

**InstalledApp**
- `name` (str): Application name
- `start_cmd` (str): Command to start the application
- `stop_cmd` (Optional[str]): Command to stop the application
- `work_directory` (Optional[str]): Working directory for the application

**ProcessListResult**
- `success` (bool): Whether the operation succeeded
- `data` (List[Process]): List of process objects
- `error_message` (str): Error message if operation failed
- `request_id` (str): Unique request identifier

**Process**
- `pname` (str): Process name
- `pid` (int): Process ID
- `cmdline` (Optional[str]): Full command line

**AppOperationResult**
- `success` (bool): Whether the operation succeeded
- `error_message` (str): Error message if operation failed
- `request_id` (str): Unique request identifier

## 🎯 Summary

This guide covered desktop application management capabilities:

- **Application Discovery**: Find installed desktop applications
- **Application Lifecycle**: Start and stop applications reliably
- **Process Monitoring**: Track running processes
- **Desktop Automation**: Build automated desktop workflows

These features enable you to build sophisticated desktop automation solutions for testing, workflow automation, and remote desktop management scenarios using AgentBay SDK's Computer Use capabilities.

## 📚 Related Guides

- [Computer UI Automation](computer-ui-automation.md) - Mouse and keyboard automation
- [Window Management](window-management.md) - Window control and positioning
- [Session Management](../common-features/basics/session-management.md) - Session lifecycle and configuration
- [Command Execution](../common-features/basics/command-execution.md) - Execute shell commands

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../README.md)
