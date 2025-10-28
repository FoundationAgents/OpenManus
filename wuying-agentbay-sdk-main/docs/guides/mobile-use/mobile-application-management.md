# Application Management for Mobile Use

This guide covers application management capabilities for mobile devices (Android) using the AgentBay SDK. Learn how to launch, monitor, and control mobile applications in cloud environments.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Getting Installed Applications](#getting-installed-applications)
- [Starting Applications](#starting-applications)
- [Stopping Applications](#stopping-applications)
- [Complete Workflow Example](#complete-workflow-example)
- [API Reference](#api-reference)

<a id="overview"></a>
## 🎯 Overview

The Mobile Use module provides application management capabilities for Android mobile devices:

1. **Application Discovery** - Query installed applications on the device
2. **Application Lifecycle** - Start and stop mobile applications using package names
3. **Activity Management** - Launch specific Android activities
4. **Process Monitoring** - Track running applications and their processes

**Note:** This guide has been verified with the `mobile_latest` system image. These features should also work with other mobile system images.

<a id="prerequisites"></a>
## 📦 Prerequisites

First, create a session with a mobile environment:

```python
import os
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

api_key = os.getenv("AGENTBAY_API_KEY")
if not api_key:
    raise ValueError("AGENTBAY_API_KEY environment variable is required")

agent_bay = AgentBay(api_key=api_key)

params = CreateSessionParams(image_id="mobile_latest")
result = agent_bay.create(params)

if result.success:
    session = result.session
    print(f"Session created: {session.session_id}")
else:
    print(f"Failed to create session: {result.error_message}")
    exit(1)

# Actual output:
# Session created: session-04bdw8o39c9uiwet4
```

<a id="getting-installed-applications"></a>
## 🔍 Getting Installed Applications

Query the list of installed applications on the mobile device:

```python
result = session.mobile.get_installed_apps(
    start_menu=True,
    desktop=False,
    ignore_system_apps=True
)

if result.success:
    apps = result.data
    print(f"Found {len(apps)} installed applications")
    
    for app in apps[:5]:
        print(f"Name: {app.name}")
        print(f"Start Command: {app.start_cmd}")
        print(f"Stop Command: {app.stop_cmd if app.stop_cmd else 'N/A'}")
        print(f"Work Directory: {app.work_directory if app.work_directory else 'N/A'}")
        print("---")
else:
    print(f"Error: {result.error_message}")

# Actual output (with current mobile_latest image):
# Found 0 installed applications
```

**Parameters:**
- `start_menu` (bool): Whether to include start menu applications
- `desktop` (bool): Whether to include desktop applications
- `ignore_system_apps` (bool): Whether to filter out system applications

**Returns:**
- `InstalledAppListResult` containing a list of `InstalledApp` objects

**Note:** The current `mobile_latest` image does not include pre-installed applications in the listing, so this method returns an empty list. However, you can still launch applications using their package names (see below).

<a id="starting-applications"></a>
## 🚀 Starting Applications

Launch mobile applications using the "monkey -p" command format with package names:

### Start by Package Name

```python
# Use "monkey -p" format for Android package names
start_cmd = "monkey -p com.android.settings"

result = session.mobile.start_app(start_cmd)

if result.success:
    processes = result.data
    print(f"Application started with {len(processes)} processes")
    
    for process in processes:
        print(f"Process: {process.pname} (PID: {process.pid})")
else:
    print(f"Failed to start application: {result.error_message}")

# Actual output:
# Application started with 1 processes
# Process: com.android.settings (PID: 2805)
```

**Important Notes:**
- **Command Format**: Always use `"monkey -p <package_name>"` format for starting apps
- **Package Names**: Common Android package names:
  - Settings: `com.android.settings`
  - Chrome: `com.android.chrome`
  - Calculator: `com.android.calculator2`
  - Contacts: `com.android.contacts`

### Start with Specific Activity (Android)

```python
start_cmd = "monkey -p com.android.settings"
activity = ".Settings"

result = session.mobile.start_app(
    start_cmd=start_cmd,
    activity=activity
)

if result.success:
    processes = result.data
    print(f"Application started with activity {activity}")
    print(f"Found {len(processes)} processes")
    
    for process in processes:
        print(f"Process: {process.pname} (PID: {process.pid})")
else:
    print(f"Failed to start application: {result.error_message}")

# Actual output:
# Application started with activity .Settings
# Found 1 processes
# Process: com.android.settings (PID: 2921)
```

**Note:** The `activity` parameter allows you to launch a specific activity within an app. Activities can be specified as:
- Relative name: `".SettingsActivity"`
- Full name: `"com.package/.Activity"`

Common activity examples:
- Settings: `com.android.settings` with activity `.Settings`
- Browser: `com.android.chrome` with activity `com.google.android.apps.chrome.Main`
- Calculator: `com.android.calculator2` with activity `.Calculator`

<a id="stopping-applications"></a>
## 🛑 Stopping Applications

Stop running mobile applications using the stop command:

```python
# Start an application
start_result = session.mobile.start_app("monkey -p com.android.settings")

if start_result.success:
    print("Application started successfully")
    for process in start_result.data:
        print(f"  Process: {process.pname} (PID: {process.pid})")
    
    # Stop the application using package name
    result = session.mobile.stop_app_by_cmd("com.android.settings")
    
    if result.success:
        print("Successfully stopped application")
    else:
        print(f"Failed to stop application: {result.error_message}")

# Actual output:
# Application started successfully
#   Process: com.android.settings (PID: 3042)
# Successfully stopped application
```

**Note:** The `stop_cmd` parameter should be the package name (e.g., `"com.android.settings"`).

<a id="complete-workflow-example"></a>
## 🔄 Complete Workflow Example

Complete example showing how to launch and control a mobile application:

```python
import os
import time
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

api_key = os.getenv("AGENTBAY_API_KEY")
if not api_key:
    raise ValueError("AGENTBAY_API_KEY environment variable is required")

agent_bay = AgentBay(api_key=api_key)

# Create mobile session
params = CreateSessionParams(image_id="mobile_latest")
result = agent_bay.create(params)

if not result.success:
    print(f"Failed to create session: {result.error_message}")
    exit(1)

session = result.session
print(f"Session created: {session.session_id}")

# Step 1: Launching application
print("Step 1: Launching Settings application...")
start_result = session.mobile.start_app("monkey -p com.android.settings")

if not start_result.success:
    print(f"Failed to start app: {start_result.error_message}")
    agent_bay.delete(session)
    exit(1)

print(f"Application started with {len(start_result.data)} processes")
for process in start_result.data:
    print(f"  - {process.pname} (PID: {process.pid})")

# Step 2: Waiting for application to load
print("Step 2: Waiting for application to load...")
time.sleep(3)

# Step 3: Stopping application
print("Step 3: Stopping application...")
stop_result = session.mobile.stop_app_by_cmd("com.android.settings")
if stop_result.success:
    print("Application stopped successfully")
else:
    print(f"Failed to stop application: {stop_result.error_message}")

# Cleanup
print("Cleaning up session...")
agent_bay.delete(session)
print("Workflow completed!")

# Actual output:
# Session created: session-04bdwfj7tnhfnzibx
# Step 1: Launching Settings application...
# Application started with 1 processes
#   - com.android.settings (PID: 3268)
# Step 2: Waiting for application to load...
# Step 3: Stopping application...
# Application stopped successfully
# Cleaning up session...
# Workflow completed!
```

<a id="api-reference"></a>
## 📚 API Reference

### Mobile Manager Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `get_installed_apps()` | `start_menu: bool`<br/>`desktop: bool`<br/>`ignore_system_apps: bool` | `InstalledAppListResult` | Get list of installed applications |
| `start_app()` | `start_cmd: str`<br/>`work_directory: str = ""`<br/>`activity: str = ""` | `ProcessListResult` | Start a mobile application |
| `stop_app_by_cmd()` | `stop_cmd: str` | `AppOperationResult` | Stop application by package name |

### Return Types

**InstalledAppListResult**
- `success` (bool): Whether the operation succeeded
- `data` (List[InstalledApp]): List of installed applications
- `error_message` (str): Error message if operation failed
- `request_id` (str): Unique request identifier

**InstalledApp**
- `name` (str): Application name
- `start_cmd` (str): Command/package name to start the application
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

### Mobile-Specific Parameters

**Start Command Format**

The `start_cmd` parameter must use the "monkey -p" format:

```python
session.mobile.start_app("monkey -p com.android.settings")
```

**Stop Command Format**

The `stop_cmd` parameter should be the package name:

```python
session.mobile.stop_app_by_cmd("com.android.settings")
```

**Activity Parameter (Android)**

The `activity` parameter allows launching a specific activity:

```python
session.mobile.start_app(
    start_cmd="monkey -p com.android.settings",
    activity=".Settings"
)
```

Activity names can be specified as:
- **Relative name**: `.SettingsActivity` (package prefix will be added automatically)
- **Full name**: `com.package/.Activity` (complete activity identifier)

## 🎯 Summary

This guide covered mobile application management capabilities:

- **Application Discovery**: Query installed applications on the device
- **Application Lifecycle**: Start and stop Android apps using monkey command format
- **Activity Management**: Launch specific Android activities
- **Process Monitoring**: Track running mobile processes

These features enable you to build automated mobile workflows for testing, automation, and remote mobile device management scenarios using AgentBay SDK's Mobile Use capabilities.

## 📝 Platform Differences

**Mobile vs. Desktop:**
- **Mobile** (this guide): Uses "monkey -p" command format (e.g., `"monkey -p com.android.chrome"`) and supports Android activities
- **Desktop**: Uses executable paths (e.g., `/usr/bin/google-chrome-stable`) and supports working directories
- **Window Management**: Only available for desktop environments; mobile apps use full-screen activities instead
- **Application Discovery**: The current `mobile_latest` image returns an empty list from `get_installed_apps()`, but the API is available for future image versions
- **Stop Methods**: Mobile only supports `stop_app_by_cmd()` using package names; desktop supports additional methods like `stop_app_by_pid()` and `stop_app_by_pname()`

For desktop application management, see the [Computer Use Application Management Guide](../computer-use/computer-application-management.md).

## 📚 Related Guides

- [Mobile UI Automation](mobile-ui-automation.md) - Touch gestures and UI interaction
- [Computer Application Management](../computer-use/computer-application-management.md) - Desktop application management
- [Session Management](../common-features/basics/session-management.md) - Session lifecycle and configuration
- [Command Execution](../common-features/basics/command-execution.md) - Execute shell commands

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../README.md)
