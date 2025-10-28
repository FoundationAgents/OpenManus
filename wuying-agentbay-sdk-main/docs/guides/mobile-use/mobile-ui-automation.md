# Mobile UI Automation Guide

This guide covers mobile UI automation capabilities in AgentBay SDK for Android mobile environments, including touch operations, text input, UI element detection, and screen operations.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Touch Operations](#touch-operations)
- [Text Input Operations](#text-input-operations)
- [UI Element Detection](#ui-element-detection)
- [Screen Operations](#screen-operations)
- [Best Practices](#best-practices)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)

<a id="overview"></a>
## 🎯 Overview

AgentBay provides powerful mobile UI automation capabilities for interacting with Android mobile environments in the cloud. You can:

1. **Touch Operations** - Tap and swipe gestures for mobile interaction
2. **Text Input** - Input text and send hardware key events
3. **UI Element Detection** - Discover and interact with UI elements
4. **Screen Operations** - Capture screenshots for visual verification

All operations are performed through the `session.mobile` module, which provides a comprehensive API for mobile automation tasks.

<a id="prerequisites"></a>
## ⚙️ Prerequisites

Mobile UI automation requires creating a session with a mobile system image (this example uses `mobile_latest` for verification):

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

agent_bay = AgentBay()
session_params = CreateSessionParams(image_id="mobile_latest")
session = agent_bay.create(session_params).session
# Session created successfully for mobile automation
```

<a id="touch-operations"></a>
## 👆 Touch Operations

### Tap Gesture

Tap on the screen at specific coordinates:

```python
session_params = CreateSessionParams(image_id="mobile_latest")
session = agent_bay.create(session_params).session

# Tap at coordinates
result = session.mobile.tap(x=500, y=300)
if result.success:
    print("Tap successful")  # Output: Tap successful
else:
    print(f"Tap failed: {result.error_message}")

agent_bay.delete(session)
```

### Swipe Gesture

Perform swipe gestures from one point to another:

```python
session_params = CreateSessionParams(image_id="mobile_latest")
session = agent_bay.create(session_params).session

# Swipe up (from bottom to top)
result = session.mobile.swipe(
    start_x=100,
    start_y=500,
    end_x=100,
    end_y=200,
    duration_ms=300
)
if result.success:
    print("Swipe up successful")  # Output: Swipe up successful

# Swipe left (from right to left)
result = session.mobile.swipe(
    start_x=500,
    start_y=300,
    end_x=100,
    end_y=300,
    duration_ms=300
)
if result.success:
    print("Swipe left successful")  # Output: Swipe left successful

agent_bay.delete(session)
```

**Parameters:**
- `start_x`, `start_y`: Starting coordinates
- `end_x`, `end_y`: Ending coordinates
- `duration_ms`: Duration of the swipe in milliseconds (default: 300)

<a id="text-input-operations"></a>
## ⌨️ Text Input Operations

### Input Text

Type text into the active field:

```python
session_params = CreateSessionParams(image_id="mobile_latest")
session = agent_bay.create(session_params).session

result = session.mobile.input_text("Hello AgentBay!")
if result.success:
    print("Text input successful")  # Output: Text input successful

agent_bay.delete(session)
```

### Send Hardware Key Events

Send Android hardware key events using KeyCode constants:

```python
from agentbay.mobile.mobile import KeyCode

session_params = CreateSessionParams(image_id="mobile_latest")
session = agent_bay.create(session_params).session

# Press HOME key
result = session.mobile.send_key(KeyCode.HOME)
if result.success:
    print("HOME key pressed")  # Output: HOME key pressed

# KeyCode values are: HOME=3, BACK=4, VOLUME_UP=24, VOLUME_DOWN=25, POWER=26, MENU=82
print(f"HOME keycode value: {KeyCode.HOME}")  # Output: HOME keycode value: 3

agent_bay.delete(session)
```

**Available KeyCode Constants:**

| KeyCode | Value | Description |
|---------|-------|-------------|
| `KeyCode.HOME` | 3 | Home button |
| `KeyCode.BACK` | 4 | Back button |
| `KeyCode.VOLUME_UP` | 24 | Volume up button |
| `KeyCode.VOLUME_DOWN` | 25 | Volume down button |
| `KeyCode.POWER` | 26 | Power button |
| `KeyCode.MENU` | 82 | Menu button |

**Note:** All hardware keys can be used for mobile device automation. The key press events are sent to the Android system and executed accordingly.

<a id="ui-element-detection"></a>
## 🔍 UI Element Detection

### Get All UI Elements

Retrieve all UI elements in the current screen hierarchy:

```python
session_params = CreateSessionParams(image_id="mobile_latest")
session = agent_bay.create(session_params).session

result = session.mobile.get_all_ui_elements(timeout_ms=2000)
if result.success:
    print(f"Found {len(result.elements)} UI elements")  # Output: Found 2172 UI elements
    for element in result.elements:
        # Element structure varies, inspect element data
        print(f"Element: {element}")
        # Output example: Element data contains UI hierarchy information
else:
    print(f"Failed: {result.error_message}")

agent_bay.delete(session)
```

**Parameters:**
- `timeout_ms`: Timeout in milliseconds to wait for UI elements (default: 2000)

### Get Clickable UI Elements

Retrieve only clickable/interactable UI elements:

```python
session_params = CreateSessionParams(image_id="mobile_latest")
session = agent_bay.create(session_params).session

result = session.mobile.get_clickable_ui_elements(timeout_ms=2000)
if result.success:
    print(f"Found {len(result.elements)} clickable elements")  # Output: Found 3 clickable elements
    for element in result.elements:
        # Process clickable elements
        print(f"Clickable element: {element}")
        # Output example: Clickable element data with interaction capabilities
else:
    print(f"Failed: {result.error_message}")

agent_bay.delete(session)
```

**Parameters:**
- `timeout_ms`: Timeout in milliseconds to wait for UI elements (default: 2000)

<a id="screen-operations"></a>
## 📸 Screen Operations

### Take Screenshot

Capture a screenshot of the current mobile screen:

```python
session_params = CreateSessionParams(image_id="mobile_latest")
session = agent_bay.create(session_params).session

result = session.mobile.screenshot()
if result.success:
    screenshot_url = result.data
    print(f"Screenshot URL: {screenshot_url}")
    # Output: Screenshot URL: https://***.***.aliyuncs.com/***/screenshot_1234567890.png?***
else:
    print(f"Screenshot failed: {result.error_message}")

agent_bay.delete(session)
```

<a id="best-practices"></a>
## 💡 Best Practices

### 1. Always Use Mobile System Images

Mobile UI automation requires a mobile system image (examples below use `mobile_latest`):

```python
# Correct - using mobile system image
session_params = CreateSessionParams(image_id="mobile_latest")
session = agent_bay.create(session_params).session

# Incorrect - will not work for mobile operations
session_params = CreateSessionParams(image_id="windows_latest")
session = agent_bay.create(session_params).session
```

### 4. Handle Screenshot URLs Properly

Screenshots return OSS URLs, not image data:

```python
result = session.mobile.screenshot()
if result.success:
    screenshot_url = result.data
    print(f"Screenshot available at: {screenshot_url}")
    # Output: Screenshot available at: https://***.***.aliyuncs.com/***/screenshot_1234567890.png?***
    # Use the URL to download or display the screenshot as needed
else:
    print(f"Screenshot failed: {result.error_message}")
```

<a id="common-use-cases"></a>
## 🎨 Common Use Cases

### Example 1: App Navigation

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

agent_bay = AgentBay()
session_params = CreateSessionParams(image_id="mobile_latest")
session = agent_bay.create(session_params).session

try:
    # Tap on app icon
    tap_result = session.mobile.tap(x=200, y=400)
    print(f"App tap result: {tap_result.success}")  # Output: App tap result: True
    
    # Wait a moment for app to load
    import time
    time.sleep(2)
    
    # Swipe to navigate
    swipe_result = session.mobile.swipe(
        start_x=400,
        start_y=600,
        end_x=100,
        end_y=600,
        duration_ms=300
    )
    print(f"Navigation swipe result: {swipe_result.success}")  # Output: Navigation swipe result: True
    
    # Tap on a button
    button_result = session.mobile.tap(x=300, y=800)
    print(f"Button tap result: {button_result.success}")  # Output: Button tap result: True
    
finally:
    agent_bay.delete(session)
```

### Example 2: Form Input on Mobile

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

agent_bay = AgentBay()
session_params = CreateSessionParams(image_id="mobile_latest")
session = agent_bay.create(session_params).session

try:
    # Tap on username field
    username_tap = session.mobile.tap(x=300, y=400)
    print(f"Username field focused: {username_tap.success}")  # Output: Username field focused: True
    
    # Enter username
    username_input = session.mobile.input_text("john_doe")
    print(f"Username entered: {username_input.success}")  # Output: Username entered: True
    
    # Tap on password field
    password_tap = session.mobile.tap(x=300, y=500)
    print(f"Password field focused: {password_tap.success}")  # Output: Password field focused: True
    
    # Enter password
    password_input = session.mobile.input_text("secure_password")
    print(f"Password entered: {password_input.success}")  # Output: Password entered: True
    
    # Tap login button
    login_tap = session.mobile.tap(x=300, y=650)
    print(f"Login button pressed: {login_tap.success}")  # Output: Login button pressed: True
    
finally:
    agent_bay.delete(session)
```

### Example 3: UI Element Discovery and Interaction

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

agent_bay = AgentBay()
session_params = CreateSessionParams(image_id="mobile_latest")
session = agent_bay.create(session_params).session

try:
    # Get all clickable elements
    result = session.mobile.get_clickable_ui_elements(timeout_ms=3000)
    
    if result.success:
        print(f"Found {len(result.elements)} clickable elements")  # Output: Found 3 clickable elements
        
        # Analyze elements to find target
        for i, element in enumerate(result.elements):
            print(f"Element {i+1}: {element}")  
            # Output example:
            # Element 1: UI element with interaction capabilities
            # Element 2: UI element with interaction capabilities  
            # Element 3: UI element with interaction capabilities
    
    # Take screenshot for verification
    screenshot = session.mobile.screenshot()
    if screenshot.success:
        screenshot_url = screenshot.data
        print(f"Screenshot URL: {screenshot_url}")
        # Output: Screenshot URL: https://***.***.aliyuncs.com/***/screenshot_1234567890.png?***
    
finally:
    agent_bay.delete(session)
```

### Example 4: Scroll Through Content

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

agent_bay = AgentBay()
session_params = CreateSessionParams(image_id="mobile_latest")
session = agent_bay.create(session_params).session

try:
    # Scroll down multiple times
    for i in range(3):
        scroll_result = session.mobile.swipe(
            start_x=300,
            start_y=800,
            end_x=300,
            end_y=200,
            duration_ms=400
        )
        print(f"Scroll down {i+1}: {scroll_result.success}")  # Output: Scroll down 1: True, etc.
        
        # Brief pause between scrolls
        import time
        time.sleep(1)
    
    # Scroll back up
    up_result = session.mobile.swipe(
        start_x=300,
        start_y=200,
        end_x=300,
        end_y=800,
        duration_ms=400
    )
    print(f"Scroll up result: {up_result.success}")  # Output: Scroll up result: True
    
finally:
    agent_bay.delete(session)
```

<a id="troubleshooting"></a>
## 🆘 Troubleshooting

### Common Issues

1. **"Tool not found" errors**
   - Ensure you're using a mobile system image (e.g., `image_id="mobile_latest"`)
   - Verify the session was created successfully
   - Check that API key and endpoint are configured correctly

2. **Hardware key operations**
   - Hardware key operations send key events to the Android system
   - Check the `result.success` status to verify if the key was sent successfully
   - Example error handling:
     ```python
     result = session.mobile.send_key(KeyCode.HOME)
     if not result.success:
         print(f"Key press failed: {result.error_message}")
     ```

3. **UI element detection returns empty results**
   - Increase the `timeout_ms` parameter
   - Take a screenshot to verify the current UI state
   - Ensure the target screen has fully loaded

4. **Screenshot URL handling**
   - Screenshots return OSS URLs, not image data
   - `result.data` contains a download URL, not the image itself
   - Use the URL to download the screenshot if needed

5. **Swipe gestures not working as expected**
   - Verify coordinates are within screen bounds
   - Adjust `duration_ms` for different gesture speeds
   - Ensure start and end coordinates create meaningful swipe direction

### Getting Help

For more assistance:
- Review [Session Management Guide](../common-features/basics/session-management.md)

## 📚 Related Guides

- [Session Management Guide](../common-features/basics/session-management.md) - Learn about session lifecycle
- [Computer UI Automation](../computer-use/computer-ui-automation.md) - Windows desktop automation
- [Command Execution](../common-features/basics/command-execution.md) - Execute shell commands
- [File Operations](../common-features/basics/file-operations.md) - Upload and download files
