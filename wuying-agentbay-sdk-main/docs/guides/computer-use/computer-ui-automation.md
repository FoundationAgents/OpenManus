# Computer UI Automation Guide

This guide covers computer UI automation capabilities in AgentBay SDK for desktop environments, including mouse operations, keyboard operations, and screen operations.

**Verified System Images:** These features have been verified to work with `windows_latest` and `linux_latest` system images.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Mouse Operations](#mouse-operations)
- [Keyboard Operations](#keyboard-operations)
- [Screen Operations](#screen-operations)
- [Best Practices](#best-practices)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)

<a id="overview"></a>
## 🎯 Overview

AgentBay provides powerful computer UI automation capabilities for interacting with Windows desktop environments in the cloud. You can:

1. **Mouse Operations** - Click, move, drag, and scroll with precise control
2. **Keyboard Operations** - Type text and send key combinations
3. **Screen Operations** - Capture screenshots and get screen information

All operations are performed through the `session.computer` module, which provides a comprehensive API for desktop automation tasks.

<a id="prerequisites"></a>
## ⚙️ Prerequisites

Computer UI automation requires creating a session with a computer use system image:

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

agent_bay = AgentBay()
# Use windows_latest or linux_latest
session_params = CreateSessionParams(image_id="windows_latest")
session = agent_bay.create(session_params).session
```

<a id="mouse-operations"></a>
## 🖱️ Mouse Operations

### Click Operations

The `click_mouse()` method supports multiple click types. You can use the `MouseButton` enum for type safety:

```python
from agentbay.computer import MouseButton

session_params = CreateSessionParams(image_id="windows_latest")
session = agent_bay.create(session_params).session

# Left click
result = session.computer.click_mouse(x=500, y=300, button=MouseButton.LEFT)
if result.success:
    print("Left click successful")
# Output: Left click successful

# Right click
result = session.computer.click_mouse(x=500, y=300, button=MouseButton.RIGHT)
if result.success:
    print("Right click successful")
# Output: Right click successful

# Middle click
result = session.computer.click_mouse(x=500, y=300, button=MouseButton.MIDDLE)
if result.success:
    print("Middle click successful")
# Output: Middle click successful

# Double left click
result = session.computer.click_mouse(x=500, y=300, button=MouseButton.DOUBLE_LEFT)
if result.success:
    print("Double click successful")
# Output: Double click successful

agent_bay.delete(session)
```

**Supported button types:** `MouseButton.LEFT`, `MouseButton.RIGHT`, `MouseButton.MIDDLE`, `MouseButton.DOUBLE_LEFT`

### Move Mouse

Move the mouse cursor to specific coordinates:

```python
session_params = CreateSessionParams(image_id="windows_latest")
session = agent_bay.create(session_params).session

result = session.computer.move_mouse(x=600, y=400)
if result.success:
    print("Mouse moved successfully")
# Output: Mouse moved successfully

agent_bay.delete(session)
```

### Drag Operations

Drag the mouse from one point to another using the `MouseButton` enum:

```python
from agentbay.computer import MouseButton

session_params = CreateSessionParams(image_id="windows_latest")
session = agent_bay.create(session_params).session

# Drag with left button
result = session.computer.drag_mouse(
    from_x=100, 
    from_y=100, 
    to_x=200, 
    to_y=200, 
    button=MouseButton.LEFT
)
if result.success:
    print("Drag operation successful")
# Output: Drag operation successful

agent_bay.delete(session)
```

**Supported button types for drag:** `MouseButton.LEFT`, `MouseButton.RIGHT`, `MouseButton.MIDDLE`

### Scroll Operations

Scroll the mouse wheel at specific coordinates using the `ScrollDirection` enum:

```python
from agentbay.computer import ScrollDirection

session_params = CreateSessionParams(image_id="windows_latest")
session = agent_bay.create(session_params).session

# Scroll up
result = session.computer.scroll(x=500, y=500, direction=ScrollDirection.UP, amount=3)
if result.success:
    print("Scrolled up successfully")
# Output: Scrolled up successfully

# Scroll down
result = session.computer.scroll(x=500, y=500, direction=ScrollDirection.DOWN, amount=5)
if result.success:
    print("Scrolled down successfully")
# Output: Scrolled down successfully

agent_bay.delete(session)
```

**Supported directions:** `ScrollDirection.UP`, `ScrollDirection.DOWN`, `ScrollDirection.LEFT`, `ScrollDirection.RIGHT`

### Get Cursor Position

Retrieve the current mouse cursor position:

```python
import json

session_params = CreateSessionParams(image_id="windows_latest")
session = agent_bay.create(session_params).session

result = session.computer.get_cursor_position()
if result.success:
    cursor_data = json.loads(result.data)
    print(f"Cursor at x={cursor_data['x']}, y={cursor_data['y']}")
# Output: Cursor at x=512, y=384

agent_bay.delete(session)
```

<a id="keyboard-operations"></a>
## ⌨️ Keyboard Operations

### Text Input

Type text into the active window or field:

```python
session_params = CreateSessionParams(image_id="windows_latest")
session = agent_bay.create(session_params).session

result = session.computer.input_text("Hello AgentBay!")
if result.success:
    print("Text input successful")
# Output: Text input successful

agent_bay.delete(session)
```

### Press Keys

Press key combinations (supports modifier keys):

```python
session_params = CreateSessionParams(image_id="windows_latest")
session = agent_bay.create(session_params).session

# Press Ctrl+A to select all
result = session.computer.press_keys(keys=["Ctrl", "a"])
if result.success:
    print("Keys pressed successfully")
# Output: Keys pressed successfully

# Press Ctrl+C to copy
result = session.computer.press_keys(keys=["Ctrl", "c"])
if result.success:
    print("Copy command sent")
# Output: Copy command sent

agent_bay.delete(session)
```

### Release Keys

Release specific keys (useful when keys are held):

```python
session_params = CreateSessionParams(image_id="windows_latest")
session = agent_bay.create(session_params).session

# Hold Ctrl key
session.computer.press_keys(keys=["Ctrl"], hold=True)

# ... perform other operations ...

# Release Ctrl key
result = session.computer.release_keys(keys=["Ctrl"])
if result.success:
    print("Keys released successfully")
# Output: Keys released successfully

agent_bay.delete(session)
```

<a id="screen-operations"></a>
## 📸 Screen Operations

### Take Screenshot

Capture a screenshot of the current screen. The screenshot is saved to cloud storage and a download URL is returned:

```python
session_params = CreateSessionParams(image_id="windows_latest")
session = agent_bay.create(session_params).session

result = session.computer.screenshot()
if result.success:
    screenshot_url = result.data
    print(f"Screenshot URL: {screenshot_url}")
# Output: Screenshot URL: https://***.***.aliyuncs.com/***/screenshot_1234567890.png?***

agent_bay.delete(session)
```

### Get Screen Size

Retrieve screen dimensions and DPI scaling factor:

```python
import json

session_params = CreateSessionParams(image_id="windows_latest")
session = agent_bay.create(session_params).session

result = session.computer.get_screen_size()
if result.success:
    screen_data = json.loads(result.data)
    print(f"Screen width: {screen_data['width']}")
    print(f"Screen height: {screen_data['height']}")
    print(f"DPI scaling factor: {screen_data['dpiScalingFactor']}")
# Output: Screen width: 1024
# Output: Screen height: 768
# Output: DPI scaling factor: 1.0

agent_bay.delete(session)
```

<a id="troubleshooting"></a>
## 🆘 Troubleshooting

### Common Issues

1. **"Tool not found" errors**
   - Ensure you're using a computer use image (`windows_latest` or `linux_latest`)

3. **Screenshot URL handling**
   - The screenshot is saved to cloud storage (OSS)
   - `result.data` contains a download URL, not the image data
   - Use the URL to download the screenshot if needed

### Getting Help

For more assistance:
- Review [Session Management Guide](../common-features/basics/session-management.md)

## 📚 Related Guides

- [Session Management Guide](../common-features/basics/session-management.md) - Learn about session lifecycle
- [Computer Application Management](computer-application-management.md) - Manage applications
- [Window Management](window-management.md) - Manage windows
- [Command Execution](../common-features/basics/command-execution.md) - Execute shell commands
- [Mobile UI Automation](../mobile-use/mobile-ui-automation.md) - Mobile device automation
