# Window Management for Computer Use

This guide covers window management capabilities for desktop environments (Windows/Linux) using the AgentBay SDK. Learn how to control window states, positions, focus, and interact with desktop windows in cloud environments.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Listing Windows](#listing-windows)
- [Window Control Operations](#window-control-operations)
- [Focus Management](#focus-management)
- [Getting Active Window](#getting-active-window)
- [Complete Workflow Example](#complete-workflow-example)
- [API Reference](#api-reference)

<a id="overview"></a>
## 🎯 Overview

The Computer Use module provides comprehensive window management capabilities for desktop environments:

1. **Window Discovery** - List and find windows in the system
2. **Window State Control** - Maximize, minimize, restore, and close windows
3. **Window Positioning** - Resize and reposition windows
4. **Focus Management** - Control window focus and activation
5. **Desktop Automation** - Build complex desktop automation workflows

These features have been verified with `windows_latest` and `linux_latest` system images.

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
else:
    print(f"Failed to create session: {result.error_message}")
    exit(1)
```

<a id="listing-windows"></a>
## 🔍 Listing Windows

Get information about all available windows in the desktop environment:

```python
result = session.computer.list_root_windows(timeout_ms=5000)

if result.success:
    windows = result.windows
    print(f"Found {len(windows)} windows")
    # Execution result: Found 0 windows (when no windows are open)
    # or: Found 5 windows (when applications are running)
    
    for window in windows:
        print(f"Title: {window.title}")
        # Execution result: Title: Google Chrome
        print(f"Window ID: {window.window_id}")
        # Execution result: Window ID: 12345678
        print(f"Process: {window.pname if window.pname else 'N/A'}")
        # Execution result: Process: chrome
        print(f"PID: {window.pid if window.pid else 'N/A'}")
        # Execution result: PID: 9876
        print(f"Position: ({window.absolute_upper_left_x}, {window.absolute_upper_left_y})")
        # Execution result: Position: (100, 50)
        print(f"Size: {window.width}x{window.height}")
        # Execution result: Size: 1280x720
        print(f"Child Windows: {len(window.child_windows)}")
        # Execution result: Child Windows: 0
        print("---")
else:
    print(f"Error listing windows: {result.error_message}")
```

**Parameters:**
- `timeout_ms` (int, optional): Timeout in milliseconds. Defaults to 3000.

**Window Object Properties:**
- `window_id` (int): Unique identifier for the window
- `title` (str): Window title/caption
- `absolute_upper_left_x` (Optional[int]): X-coordinate of window's upper-left corner
- `absolute_upper_left_y` (Optional[int]): Y-coordinate of window's upper-left corner
- `width` (Optional[int]): Window width in pixels
- `height` (Optional[int]): Window height in pixels
- `pid` (Optional[int]): Process ID that owns the window
- `pname` (Optional[str]): Process name that owns the window
- `child_windows` (List[Window]): List of child windows

<a id="window-control-operations"></a>
## 🎛️ Window Control Operations

Control window states and positions:

### Activate Window

```python
result = session.computer.list_root_windows()

if result.success and result.windows:
    window_id = result.windows[0].window_id
    
    activate_result = session.computer.activate_window(window_id)
    # Execution result: Window activated successfully
    
    if activate_result.success:
        print("Window activated successfully")
    else:
        print(f"Failed to activate window: {activate_result.error_message}")
```

### Maximize Window

```python
result = session.computer.list_root_windows()

if result.success and result.windows:
    window_id = result.windows[0].window_id
    
    maximize_result = session.computer.maximize_window(window_id)
    # Execution result: Window maximized successfully
    
    if maximize_result.success:
        print("Window maximized successfully")
    else:
        print(f"Failed to maximize window: {maximize_result.error_message}")
```

### Minimize Window

```python
result = session.computer.list_root_windows()

if result.success and result.windows:
    window_id = result.windows[0].window_id
    
    minimize_result = session.computer.minimize_window(window_id)
    # Execution result: Window minimized successfully
    
    if minimize_result.success:
        print("Window minimized successfully")
    else:
        print(f"Failed to minimize window: {minimize_result.error_message}")
```

### Restore Window

```python
result = session.computer.list_root_windows()

if result.success and result.windows:
    window_id = result.windows[0].window_id
    
    restore_result = session.computer.restore_window(window_id)
    # Execution result: Window restored successfully
    
    if restore_result.success:
        print("Window restored successfully")
    else:
        print(f"Failed to restore window: {restore_result.error_message}")
```

### Resize Window

```python
result = session.computer.list_root_windows()

if result.success and result.windows:
    window_id = result.windows[0].window_id
    
    resize_result = session.computer.resize_window(window_id, 800, 600)
    # Execution result: Window resized to 800x600
    
    if resize_result.success:
        print("Window resized to 800x600")
    else:
        print(f"Failed to resize window: {resize_result.error_message}")
```

### Fullscreen Window

```python
result = session.computer.list_root_windows()

if result.success and result.windows:
    window_id = result.windows[0].window_id
    
    fullscreen_result = session.computer.fullscreen_window(window_id)
    # Execution result: Window set to fullscreen
    
    if fullscreen_result.success:
        print("Window set to fullscreen")
    else:
        print(f"Failed to set fullscreen: {fullscreen_result.error_message}")
```

### Close Window

```python
# Note: Use with caution as it permanently closes windows
result = session.computer.list_root_windows()

if result.success and result.windows:
    window_id = result.windows[0].window_id
    
    close_result = session.computer.close_window(window_id)
    
    if close_result.success:
        print("Window closed successfully")
    else:
        print(f"Failed to close window: {close_result.error_message}")
```

### Complete Window Control Function

```python
import time

def control_window(session, window_id):
    print(f"Controlling window ID: {window_id}")
    
    try:
        session.computer.activate_window(window_id)
        print("Window activated")
    except Exception as e:
        print(f"Failed to activate: {e}")
    
    time.sleep(1)
    
    try:
        session.computer.maximize_window(window_id)
        print("Window maximized")
    except Exception as e:
        print(f"Failed to maximize: {e}")
    
    time.sleep(1)
    
    try:
        session.computer.minimize_window(window_id)
        print("Window minimized")
    except Exception as e:
        print(f"Failed to minimize: {e}")
    
    time.sleep(1)
    
    try:
        session.computer.restore_window(window_id)
        print("Window restored")
    except Exception as e:
        print(f"Failed to restore: {e}")
    
    try:
        session.computer.resize_window(window_id, 800, 600)
        print("Window resized to 800x600")
    except Exception as e:
        print(f"Failed to resize: {e}")

windows = session.computer.list_root_windows()
if windows.success and windows.windows:
    control_window(session, windows.windows[0].window_id)
```

<a id="focus-management"></a>
## 🎯 Focus Management

Control system focus behavior to prevent focus stealing:

```python
try:
    session.computer.focus_mode(True)
    # Execution result: Focus mode enabled - windows won't steal focus
    print("Focus mode enabled - windows won't steal focus")
except Exception as e:
    print(f"Failed to enable focus mode: {e}")

try:
    session.computer.focus_mode(False)
    # Execution result: Focus mode disabled
    print("Focus mode disabled")
except Exception as e:
    print(f"Failed to disable focus mode: {e}")
```

**Parameters:**
- `on` (bool): True to enable focus mode, False to disable it

<a id="getting-active-window"></a>
## 🖥️ Getting Active Window

Get information about the currently active window:

```python
# Note: May fail if no window is currently active
result = session.computer.get_active_window(timeout_ms=5000)

if result.success:
    active_window = result.window
    # Execution result when window is active:
    # Active Window:
    #   Title: Google Chrome
    #   Window ID: 87654321
    #   Process: chrome
    #   PID: 4321
    #   Position: (0, 0)
    #   Size: 1920x1080
    print(f"Active Window:")
    print(f"  Title: {active_window.title}")
    print(f"  Window ID: {active_window.window_id}")
    print(f"  Process: {active_window.pname}")
    print(f"  PID: {active_window.pid}")
    print(f"  Position: ({active_window.absolute_upper_left_x}, {active_window.absolute_upper_left_y})")
    print(f"  Size: {active_window.width}x{active_window.height}")
else:
    # Execution result when no window is active:
    # Failed to get active window: Error in response (expected if no window is active)
    print(f"Failed to get active window: {result.error_message}")
```

**Parameters:**
- `timeout_ms` (int, optional): Timeout in milliseconds. Defaults to 3000.

<a id="complete-workflow-example"></a>
## 🔄 Complete Workflow Example

Complete example showing how to launch an application and control its window:

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
# Execution result: Session created: session-04bdwfj7u688ec96t

print("Step 1: Finding installed applications...")
apps_result = session.computer.get_installed_apps(
    start_menu=True,
    desktop=False,
    ignore_system_apps=True
)
# Execution result: Found 76 applications

if not apps_result.success:
    print(f"Failed to get apps: {apps_result.error_message}")
    agent_bay.delete(session)
    exit(1)

target_app = None
for app in apps_result.data:
    if "chrome" in app.name.lower():
        target_app = app
        break

if not target_app:
    print("Google Chrome not found")
    agent_bay.delete(session)
    exit(1)

print(f"Found application: {target_app.name}")
# Execution result: Found application: Google Chrome

print("Step 2: Launching application...")
start_result = session.computer.start_app(target_app.start_cmd)

if not start_result.success:
    print(f"Failed to start app: {start_result.error_message}")
    agent_bay.delete(session)
    exit(1)

print(f"Application started with {len(start_result.data)} processes")
# Execution result: Application started with 6 processes

print("Step 3: Waiting for application window to load...")
time.sleep(5)

print("Step 4: Finding application window...")
windows_result = session.computer.list_root_windows()

if not windows_result.success:
    print(f"Failed to list windows: {windows_result.error_message}")
    agent_bay.delete(session)
    exit(1)

app_window = None
for window in windows_result.windows:
    if target_app.name.lower() in window.title.lower():
        app_window = window
        break

if not app_window and windows_result.windows:
    app_window = windows_result.windows[0]
    print("Using first available window")

if app_window:
    print(f"Found window: {app_window.title}")
    # Execution result: Found window: Welcome to Google Chrome
    
    print("Step 5: Controlling the window...")
    try:
        session.computer.activate_window(app_window.window_id)
        print("Window activated")
        # Execution result: Window activated
        
        time.sleep(1)
        session.computer.maximize_window(app_window.window_id)
        print("Window maximized")
        # Execution result: Window maximized
        
        time.sleep(1)
        session.computer.resize_window(app_window.window_id, 1024, 768)
        print("Window resized to 1024x768")
        # Execution result: Window resized to 1024x768
        
    except Exception as e:
        print(f"Window control failed: {e}")

print("Cleaning up session...")
agent_bay.delete(session)
print("Workflow completed!")
# Execution result: Session deleted successfully
```

<a id="api-reference"></a>
## 📚 API Reference

### Window Manager Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `list_root_windows()` | `timeout_ms: int = 3000` | `WindowListResult` | List all root windows |
| `get_active_window()` | `timeout_ms: int = 3000` | `WindowInfoResult` | Get currently active window |
| `activate_window()` | `window_id: int` | `BoolResult` | Activate a window |
| `maximize_window()` | `window_id: int` | `BoolResult` | Maximize a window |
| `minimize_window()` | `window_id: int` | `BoolResult` | Minimize a window |
| `restore_window()` | `window_id: int` | `BoolResult` | Restore a window |
| `close_window()` | `window_id: int` | `BoolResult` | Close a window |
| `fullscreen_window()` | `window_id: int` | `BoolResult` | Make window fullscreen |
| `resize_window()` | `window_id: int`<br/>`width: int`<br/>`height: int` | `BoolResult` | Resize a window |
| `focus_mode()` | `on: bool` | `BoolResult` | Toggle focus mode |

### Return Types

**WindowListResult**
- `success` (bool): Whether the operation succeeded
- `windows` (List[Window]): List of window objects
- `error_message` (str): Error message if operation failed
- `request_id` (str): Unique request identifier

**Window**
- `window_id` (int): Unique identifier for the window
- `title` (str): Window title/caption
- `absolute_upper_left_x` (Optional[int]): X-coordinate of upper-left corner
- `absolute_upper_left_y` (Optional[int]): Y-coordinate of upper-left corner
- `width` (Optional[int]): Window width in pixels
- `height` (Optional[int]): Window height in pixels
- `pid` (Optional[int]): Process ID that owns the window
- `pname` (Optional[str]): Process name that owns the window
- `child_windows` (List[Window]): List of child windows

**WindowInfoResult**
- `success` (bool): Whether the operation succeeded
- `window` (Window): Window object
- `error_message` (str): Error message if operation failed
- `request_id` (str): Unique request identifier

**BoolResult**
- `success` (bool): Whether the operation succeeded
- `data` (bool): Operation result data
- `error_message` (str): Error message if operation failed
- `request_id` (str): Unique request identifier

## 🎯 Summary

This guide covered desktop window management capabilities:

- **Window Discovery**: List and find windows in the system
- **Window Control**: Manage window states (maximize, minimize, restore, close)
- **Window Positioning**: Resize and reposition windows
- **Focus Management**: Control window focus and activation

These features enable you to build sophisticated desktop automation solutions that can interact with any application window in cloud environments, making AgentBay SDK's Computer Use module a powerful tool for automated testing, workflow automation, and remote desktop management.

## 📚 Related Guides

- [Computer UI Automation](computer-ui-automation.md) - Mouse and keyboard automation
- [Computer Application Management](computer-application-management.md) - Manage applications
- [Session Management](../common-features/basics/session-management.md) - Session lifecycle and configuration
- [Command Execution](../common-features/basics/command-execution.md) - Execute shell commands

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../README.md)
