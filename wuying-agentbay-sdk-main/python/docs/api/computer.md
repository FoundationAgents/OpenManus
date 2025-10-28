# Computer Class API Reference

The `Computer` class provides comprehensive desktop UI automation operations in the AgentBay cloud environment. It offers mouse operations, keyboard operations, window management, application management, and screen operations for Windows desktop automation.

## 📖 Related Tutorials

- [Computer UI Automation Guide](../../../docs/guides/computer-use/computer-ui-automation.md) - Detailed tutorial on desktop UI automation
- [Window Management Guide](../../../docs/guides/computer-use/window-management.md) - Tutorial on managing application windows

## Overview

The `Computer` class is available through `session.computer` and is designed for use with Windows desktop environments (use `image_id="windows_latest"` when creating sessions).

## Constructor

The `Computer` class is automatically instantiated when creating a session. Access it via:

```python
session.computer
```

## Enum Types

### MouseButton

Mouse button types for click and drag operations.

```python
from agentbay.computer import MouseButton

MouseButton.LEFT         # Left mouse button
MouseButton.RIGHT        # Right mouse button
MouseButton.MIDDLE       # Middle mouse button
MouseButton.DOUBLE_LEFT  # Double-click with left button
```

### ScrollDirection

Scroll direction for scroll operations.

```python
from agentbay.computer import ScrollDirection

ScrollDirection.UP     # Scroll up
ScrollDirection.DOWN   # Scroll down
ScrollDirection.LEFT   # Scroll left
ScrollDirection.RIGHT  # Scroll right
```

## Mouse Operations

### click_mouse()

Clicks the mouse at the specified coordinates.

```python
click_mouse(x: int, y: int, button: Union[MouseButton, str] = MouseButton.LEFT) -> BoolResult
```

**Parameters:**
- `x` (int): X coordinate
- `y` (int): Y coordinate
- `button` (Union[MouseButton, str], optional): Button type. Can be `MouseButton` enum or string ("left", "right", "middle", "double_left"). Defaults to `MouseButton.LEFT`.

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Raises:**
- `ValueError`: If button is not a valid option.

**Example:**
```python
from agentbay import AgentBay, CreateSessionParams

# Create session with Windows image
agent_bay = AgentBay(api_key="your_api_key")
params = CreateSessionParams(image_id="windows_latest")
session_result = agent_bay.create(params)
session = session_result.session

# Click at coordinates (100, 200)
result = session.computer.click_mouse(100, 200)
# Verified: ✓ success=True, default LEFT button works

# Right-click
from agentbay.computer import MouseButton
result = session.computer.click_mouse(100, 200, MouseButton.RIGHT)
# Verified: ✓ success=True, RIGHT button works

# Double-click
result = session.computer.click_mouse(100, 200, MouseButton.DOUBLE_LEFT)
# Verified: ✓ success=True, DOUBLE_LEFT button works

agent_bay.delete(session)
```

### move_mouse()

Moves the mouse to the specified coordinates.

```python
move_mouse(x: int, y: int) -> BoolResult
```

**Parameters:**
- `x` (int): X coordinate
- `y` (int): Y coordinate

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Example:**
```python
# Move mouse to (300, 400)
result = session.computer.move_mouse(300, 400)
# Verified: ✓ success=True
```

### drag_mouse()

Drags the mouse from one point to another.

```python
drag_mouse(from_x: int, from_y: int, to_x: int, to_y: int, button: Union[MouseButton, str] = MouseButton.LEFT) -> BoolResult
```

**Parameters:**
- `from_x` (int): Starting X coordinate
- `from_y` (int): Starting Y coordinate
- `to_x` (int): Ending X coordinate
- `to_y` (int): Ending Y coordinate
- `button` (Union[MouseButton, str], optional): Button type ("left", "right", "middle"). Defaults to `MouseButton.LEFT`. Note: DOUBLE_LEFT is not supported for drag operations.

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Raises:**
- `ValueError`: If button is not a valid option.

**Example:**
```python
# Drag from (100, 100) to (200, 200)
result = session.computer.drag_mouse(100, 100, 200, 200)
# Verified: ✓ success=True, default LEFT button works for drag
```

### scroll()

Scrolls the mouse wheel at the specified coordinates.

```python
scroll(x: int, y: int, direction: Union[ScrollDirection, str] = ScrollDirection.UP, amount: int = 1) -> BoolResult
```

**Parameters:**
- `x` (int): X coordinate
- `y` (int): Y coordinate
- `direction` (Union[ScrollDirection, str], optional): Scroll direction. Can be `ScrollDirection` enum or string ("up", "down", "left", "right"). Defaults to `ScrollDirection.UP`.
- `amount` (int, optional): Scroll amount. Defaults to 1.

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Raises:**
- `ValueError`: If direction is not a valid option.

**Example:**
```python
from agentbay.computer import ScrollDirection

# Scroll down at (500, 500)
result = session.computer.scroll(500, 500, ScrollDirection.DOWN, 3)
# Verified: ✓ success=True, DOWN direction works

# Scroll up (default direction)
result = session.computer.scroll(500, 500, amount=2)
# Verified: ✓ success=True, default UP direction works
```

### get_cursor_position()

Gets the current cursor position.

```python
get_cursor_position() -> OperationResult
```

**Returns:**
- `OperationResult`: Result object containing cursor position data with keys `x` and `y`, and error message if any.

**Example:**
```python
# Get current cursor position
result = session.computer.get_cursor_position()
# Verified: ✓ success=True, data={"x":512,"y":384}

if result.success:
    print(f"Cursor at ({result.data['x']}, {result.data['y']})")
```

## Keyboard Operations

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
# Type text
result = session.computer.input_text("Hello World")
# Verified: ✓ success=True
```

### press_keys()

Presses the specified keys.

```python
press_keys(keys: List[str], hold: bool = False) -> BoolResult
```

**Parameters:**
- `keys` (List[str]): List of keys to press (e.g., ["Ctrl", "a"])
- `hold` (bool, optional): Whether to hold the keys. Defaults to False.

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Example:**
```python
# Press Ctrl+A to select all
result = session.computer.press_keys(["Ctrl", "a"])
# Verified: ✓ success=True

# Press and hold Shift
result = session.computer.press_keys(["Shift"], hold=True)
# Verified: ✓ success=True, hold parameter works
```

### release_keys()

Releases the specified keys.

```python
release_keys(keys: List[str]) -> BoolResult
```

**Parameters:**
- `keys` (List[str]): List of keys to release (e.g., ["Ctrl", "a"])

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Example:**
```python
# Release Shift key
result = session.computer.release_keys(["Shift"])
# Verified: ✓ success=True
```

## Screen Operations

### get_screen_size()

Gets the screen size and DPI scaling factor.

```python
get_screen_size() -> OperationResult
```

**Returns:**
- `OperationResult`: Result object containing screen size data with keys `width`, `height`, and `dpiScalingFactor`, and error message if any.

**Example:**
```python
# Get screen information
result = session.computer.get_screen_size()
# Verified: ✓ success=True, data={"dpiScalingFactor":1.0,"height":768,"width":1024}

if result.success:
    screen_info = result.data
    print(f"Screen: {screen_info['width']}x{screen_info['height']}")
    print(f"DPI Scaling: {screen_info['dpiScalingFactor']}")
```

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
result = session.computer.screenshot()
# Verified: ✓ success=True, returns OSS URL (1039 bytes)
# Example URL: https://wuying-intelligence-service-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/...

if result.success:
    print(f"Screenshot URL: {result.data}")
```

## Window Management Operations

The `Computer` class provides window management operations by delegating to the `WindowManager` class.

### list_root_windows()

Lists all root windows.

```python
list_root_windows(timeout_ms: int = 3000) -> WindowListResult
```

**Parameters:**
- `timeout_ms` (int, optional): Timeout in milliseconds. Defaults to 3000.

**Returns:**
- `WindowListResult`: Result object containing list of windows and error message if any.

### get_active_window()

Gets the currently active window.

```python
get_active_window(timeout_ms: int = 3000) -> WindowInfoResult
```

**Parameters:**
- `timeout_ms` (int, optional): Timeout in milliseconds. Defaults to 3000.

**Returns:**
- `WindowInfoResult`: Result object containing active window info and error message if any.

### activate_window()

Activates the specified window.

```python
activate_window(window_id: int) -> BoolResult
```

**Parameters:**
- `window_id` (int): The ID of the window to activate

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

### close_window()

Closes the specified window.

```python
close_window(window_id: int) -> BoolResult
```

**Parameters:**
- `window_id` (int): The ID of the window to close

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

### maximize_window()

Maximizes the specified window.

```python
maximize_window(window_id: int) -> BoolResult
```

**Parameters:**
- `window_id` (int): The ID of the window to maximize

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

### minimize_window()

Minimizes the specified window.

```python
minimize_window(window_id: int) -> BoolResult
```

**Parameters:**
- `window_id` (int): The ID of the window to minimize

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

### restore_window()

Restores the specified window.

```python
restore_window(window_id: int) -> BoolResult
```

**Parameters:**
- `window_id` (int): The ID of the window to restore

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

### resize_window()

Resizes the specified window.

```python
resize_window(window_id: int, width: int, height: int) -> BoolResult
```

**Parameters:**
- `window_id` (int): The ID of the window to resize
- `width` (int): New width of the window
- `height` (int): New height of the window

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

### fullscreen_window()

Makes the specified window fullscreen.

```python
fullscreen_window(window_id: int) -> BoolResult
```

**Parameters:**
- `window_id` (int): The ID of the window to make fullscreen

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

### focus_mode()

Toggles focus mode on or off.

```python
focus_mode(on: bool) -> BoolResult
```

**Parameters:**
- `on` (bool): True to enable focus mode, False to disable it

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

## Application Management Operations

The `Computer` class provides application management operations by delegating to the `ApplicationManager` class.

### get_installed_apps()

Gets the list of installed applications.

```python
get_installed_apps(start_menu: bool = True, desktop: bool = False, ignore_system_apps: bool = True) -> InstalledAppListResult
```

**Parameters:**
- `start_menu` (bool, optional): Whether to include start menu applications. Defaults to True.
- `desktop` (bool, optional): Whether to include desktop applications. Defaults to False.
- `ignore_system_apps` (bool, optional): Whether to ignore system applications. Defaults to True.

**Returns:**
- `InstalledAppListResult`: Result object containing list of installed apps and error message if any.

### start_app()

Starts the specified application.

```python
start_app(start_cmd: str, work_directory: str = "", activity: str = "") -> ProcessListResult
```

**Parameters:**
- `start_cmd` (str): The command to start the application
- `work_directory` (str, optional): Working directory for the application. Defaults to ""
- `activity` (str, optional): Activity name to launch (for mobile apps). Defaults to ""

**Returns:**
- `ProcessListResult`: Result object containing list of processes started and error message if any.

### list_visible_apps()

Lists all applications with visible windows.

```python
list_visible_apps() -> ProcessListResult
```

**Returns:**
- `ProcessListResult`: Result object containing list of visible applications with detailed process information.

### stop_app_by_pname()

Stops an application by process name.

```python
stop_app_by_pname(pname: str) -> AppOperationResult
```

**Parameters:**
- `pname` (str): The process name of the application to stop

**Returns:**
- `AppOperationResult`: Result object containing success status and error message if any.

### stop_app_by_pid()

Stops an application by process ID.

```python
stop_app_by_pid(pid: int) -> AppOperationResult
```

**Parameters:**
- `pid` (int): The process ID of the application to stop

**Returns:**
- `AppOperationResult`: Result object containing success status and error message if any.

### stop_app_by_cmd()

Stops an application by stop command.

```python
stop_app_by_cmd(stop_cmd: str) -> AppOperationResult
```

**Parameters:**
- `stop_cmd` (str): The command to stop the application

**Returns:**
- `AppOperationResult`: Result object containing success status and error message if any.

## Complete Example

```python
from agentbay import AgentBay, CreateSessionParams
from agentbay.computer import MouseButton, ScrollDirection
import os

# Initialize SDK
api_key = os.getenv("AGENTBAY_API_KEY")
agent_bay = AgentBay(api_key=api_key)

# Create Windows session
params = CreateSessionParams(image_id="windows_latest")
session_result = agent_bay.create(params)

if session_result.success:
    session = session_result.session
    
    # Get screen size
    screen_info = session.computer.get_screen_size()
    # Verified: ✓ Returns {"dpiScalingFactor":1.0,"height":768,"width":1024}
    
    # Mouse operations
    session.computer.click_mouse(100, 200)
    # Verified: ✓ Left click works
    
    session.computer.move_mouse(300, 400)
    # Verified: ✓ Move mouse works
    
    session.computer.scroll(500, 500, ScrollDirection.DOWN, 3)
    # Verified: ✓ Scroll works
    
    # Keyboard operations
    session.computer.input_text("Hello World")
    # Verified: ✓ Text input works
    
    session.computer.press_keys(["Ctrl", "a"])
    # Verified: ✓ Key press works
    
    # Take screenshot
    screenshot = session.computer.screenshot()
    # Verified: ✓ Returns OSS URL (1039 bytes)
    
    # Clean up
    agent_bay.delete(session)

```

## Related Documentation

- [Window Management API](./window.md) - Detailed window management operations
- [Application Management API](./application.md) - Detailed application management operations
- [Session API](./session.md) - Session management
