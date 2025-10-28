# Mobile Class API Reference

The `Mobile` class provides comprehensive mobile device UI automation operations in the AgentBay cloud environment. It offers touch operations, UI element interactions, application management, and screenshot capabilities for Android mobile device automation.

## 📖 Related Tutorials

- [Mobile UI Automation Guide](../../../docs/guides/mobile-use/mobile-ui-automation.md) - Detailed tutorial on mobile UI automation
- [Mobile Application Management Guide](../../../docs/guides/mobile-use/mobile-application-management.md) - Tutorial on managing mobile applications

## Overview

The `Mobile` class is available through `session.mobile` and is designed for use with Android mobile environments (use `image_id="mobile_latest"` when creating sessions).

## Constructor

The `Mobile` class is automatically instantiated when creating a session. Access it via:

```python
session.mobile
```

## KeyCode Class

Key codes for mobile device input.

```python
from agentbay.mobile.mobile import KeyCode

KeyCode.HOME        # 3  - Home button
KeyCode.BACK        # 4  - Back button
KeyCode.VOLUME_UP   # 24 - Volume up button
KeyCode.VOLUME_DOWN # 25 - Volume down button
KeyCode.POWER       # 26 - Power button
KeyCode.MENU        # 82 - Menu button
```

## Touch Operations

### tap()

Taps on the screen at the specified coordinates.

```python
tap(x: int, y: int) -> BoolResult
```

**Parameters:**
- `x` (int): X coordinate
- `y` (int): Y coordinate

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Example:**
```python
from agentbay import AgentBay, CreateSessionParams

# Create session with mobile image
agent_bay = AgentBay(api_key="your_api_key")
params = CreateSessionParams(image_id="mobile_latest")
session_result = agent_bay.create(params)
session = session_result.session

# Tap at coordinates (500, 500)
result = session.mobile.tap(500, 500)
# Verified: success=True

agent_bay.delete(session)
```

### swipe()

Performs a swipe gesture from one point to another.

```python
swipe(start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> BoolResult
```

**Parameters:**
- `start_x` (int): Starting X coordinate
- `start_y` (int): Starting Y coordinate
- `end_x` (int): Ending X coordinate
- `end_y` (int): Ending Y coordinate
- `duration_ms` (int, optional): Duration of the swipe in milliseconds. Defaults to 300.

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Example:**
```python
# Swipe up (from bottom to top)
result = session.mobile.swipe(540, 1500, 540, 500, duration_ms=300)
# Verified: success=True

# Swipe left (from right to left)
result = session.mobile.swipe(900, 500, 100, 500, duration_ms=200)
# Verified: success=True

# Swipe right (from left to right)
result = session.mobile.swipe(100, 500, 900, 500, duration_ms=200)
# Verified: success=True
```

### input_text()

Inputs text into the active field.

```python
input_text(text: str) -> BoolResult
```

**Parameters:**
- `text` (str): The text to input

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Example:**
```python
# Type text into active field
result = session.mobile.input_text("Hello Mobile")
# Verified: success=True
```

### send_key()

Sends a key press event.

```python
send_key(key: int) -> BoolResult
```

**Parameters:**
- `key` (int): The key code to send. Supported key codes:
  - 3  : HOME
  - 4  : BACK
  - 24 : VOLUME UP
  - 25 : VOLUME DOWN
  - 26 : POWER
  - 82 : MENU

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Example:**
```python
from agentbay.mobile.mobile import KeyCode

# Press HOME button
result = session.mobile.send_key(KeyCode.HOME)
# Verified: success=True

# Press BACK button
result = session.mobile.send_key(KeyCode.BACK)
# Verified: success=True

# Press MENU button
result = session.mobile.send_key(KeyCode.MENU)
# Verified: success=True
```

## UI Element Operations

### get_clickable_ui_elements()

Retrieves all clickable UI elements within the specified timeout.

```python
get_clickable_ui_elements(timeout_ms: int = 2000) -> UIElementListResult
```

**Parameters:**
- `timeout_ms` (int, optional): Timeout in milliseconds. Defaults to 2000.

**Returns:**
- `UIElementListResult`: Result object containing clickable UI elements and error message if any.

**Example:**
```python
# Get all clickable elements
result = session.mobile.get_clickable_ui_elements(timeout_ms=2000)
# Verified: success=True, returns list of clickable elements

if result.success:
    print(f"Found {len(result.elements)} clickable elements")
    for element in result.elements:
        print(f"Element: {element}")
```

### get_all_ui_elements()

Retrieves all UI elements within the specified timeout.

```python
get_all_ui_elements(timeout_ms: int = 2000) -> UIElementListResult
```

**Parameters:**
- `timeout_ms` (int, optional): Timeout in milliseconds. Defaults to 2000.

**Returns:**
- `UIElementListResult`: Result object containing all UI elements and error message if any.

**Example:**
```python
# Get all UI elements
result = session.mobile.get_all_ui_elements(timeout_ms=2000)
# Verified: success=True, returns list of all UI elements

if result.success:
    print(f"Found {len(result.elements)} total elements")
    for element in result.elements:
        print(f"Element: {element}")
```

## Application Management Operations

### get_installed_apps()

Retrieves a list of installed applications.

```python
get_installed_apps(start_menu: bool, desktop: bool, ignore_system_apps: bool) -> InstalledAppListResult
```

**Parameters:**
- `start_menu` (bool): Whether to include start menu applications
- `desktop` (bool): Whether to include desktop applications
- `ignore_system_apps` (bool): Whether to ignore system applications

**Returns:**
- `InstalledAppListResult`: The result containing the list of installed applications.

**Example:**
```python
# Get installed apps (excluding system apps)
result = session.mobile.get_installed_apps(
    start_menu=False,
    desktop=False,
    ignore_system_apps=True
)
# Verified: success=True, returns list of installed apps

if result.success:
    for app in result.data:
        print(f"App: {app.name}, Command: {app.start_cmd}")
```

### start_app()

Starts an application with the given command, optional working directory and optional activity.

```python
start_app(start_cmd: str, work_directory: str = "", activity: str = "") -> ProcessListResult
```

**Parameters:**
- `start_cmd` (str): The command to start the application. For Android apps, this should be in the format required by the system (e.g., using monkey command).
- `work_directory` (str, optional): The working directory for the application. Defaults to "".
- `activity` (str, optional): Activity name to launch (e.g., ".SettingsActivity" or "com.package/.Activity"). Defaults to "".

**Returns:**
- `ProcessListResult`: The result containing the list of processes started.

**Example:**
```python
# Start Settings app
# Note: start_cmd format is specific to the mobile automation system
result = session.mobile.start_app(
    "com.android.settings",
    activity=".Settings"
)
# Note: Requires specific command format. Check with system documentation.

if result.success:
    print(f"Started {len(result.data)} processes")
```

### stop_app_by_cmd()

Stops an application by stop command.

```python
stop_app_by_cmd(stop_cmd: str) -> AppOperationResult
```

**Parameters:**
- `stop_cmd` (str): The command to stop the application

**Returns:**
- `AppOperationResult`: The result of the operation.

**Example:**
```python
# Stop an application
result = session.mobile.stop_app_by_cmd("am force-stop com.example.app")

if result.success:
    print("App stopped successfully")
```

## Screenshot Operations

### screenshot()

Takes a screenshot of the current screen.

```python
screenshot() -> OperationResult
```

**Returns:**
- `OperationResult`: Result object containing the screenshot URL and error message if any.

**Example:**
```python
# Take a screenshot
result = session.mobile.screenshot()
# Verified: success=True, returns OSS URL to screenshot image

if result.success:
    print(f"Screenshot URL: {result.data}")
```

## Complete Example

```python
from agentbay import AgentBay, CreateSessionParams
from agentbay.mobile.mobile import KeyCode
import os

# Initialize SDK
api_key = os.getenv("AGENTBAY_API_KEY")
agent_bay = AgentBay(api_key=api_key)

# Create mobile session
params = CreateSessionParams(image_id="mobile_latest")
session_result = agent_bay.create(params)

if session_result.success:
    session = session_result.session
    
    # Touch operations
    session.mobile.tap(500, 500)
    # Verified: success=True
    
    session.mobile.swipe(540, 1500, 540, 500, duration_ms=300)
    # Verified: success=True
    
    session.mobile.input_text("Hello Mobile")
    # Verified: success=True
    
    # Key operations
    session.mobile.send_key(KeyCode.HOME)
    # Verified: success=True
    
    session.mobile.send_key(KeyCode.BACK)
    # Verified: success=True
    
    # Get UI elements
    clickable_elements = session.mobile.get_clickable_ui_elements(timeout_ms=2000)
    # Verified: success=True
    
    if clickable_elements.success:
        print(f"Found {len(clickable_elements.elements)} clickable elements")
    
    all_elements = session.mobile.get_all_ui_elements(timeout_ms=2000)
    # Verified: success=True
    
    if all_elements.success:
        print(f"Found {len(all_elements.elements)} total elements")
    
    # Get installed apps
    apps = session.mobile.get_installed_apps(
        start_menu=False,
        desktop=False,
        ignore_system_apps=True
    )
    # Verified: success=True
    
    if apps.success:
        print(f"Installed apps: {len(apps.data)}")
    
    # Take screenshot
    screenshot = session.mobile.screenshot()
    # Verified: success=True, returns screenshot URL
    
    if screenshot.success:
        print(f"Screenshot: {screenshot.data}")
    
    # Clean up
    agent_bay.delete(session)

```

## Usage Notes

1. **Session Image**: Always use `image_id="mobile_latest"` when creating sessions for mobile automation.

2. **Coordinates**: Mobile screen coordinates typically range based on the device resolution. Common Android emulator resolutions:
   - 1080x1920 (Full HD)
   - 720x1280 (HD)
   - Check screen size using UI elements or emulator settings.

3. **Swipe Duration**: The `duration_ms` parameter in `swipe()` affects the speed of the gesture. Shorter durations (100-200ms) create faster swipes, while longer durations (500-1000ms) create slower, more deliberate gestures.

4. **Key Codes**: Only the predefined key codes in the `KeyCode` class are supported. Custom key codes may not work as expected.

5. **App Management**: The `start_app()` command format is specific to the mobile automation system. Verify the correct format with system documentation.

6. **UI Elements**: UI element detection may take time. Adjust the `timeout_ms` parameter based on your application's loading speed.

## Related Documentation

- [Application Management API](./application.md) - Detailed application management operations
- [UI Automation API](./ui.md) - UI automation operations
- [Session API](./session.md) - Session management
