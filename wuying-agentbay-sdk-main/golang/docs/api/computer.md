# Computer Module

The Computer module provides comprehensive desktop UI automation capabilities for Windows environments in the AgentBay cloud platform. It enables mouse operations, keyboard input, screen capture, and window management.

## 📖 Related Tutorials

- [Computer UI Automation Guide](../../../docs/guides/computer-use/computer-ui-automation.md) - Detailed tutorial on desktop UI automation
- [Window Management Guide](../../../docs/guides/computer-use/window-management.md) - Tutorial on managing application windows

## Overview

The Computer module is designed for automating Windows desktop applications. It provides low-level input control, screen operations, and window management capabilities that are essential for desktop automation tasks.

**Requirements:**
- Session must be created with `windows_latest` image
- All methods use MCP (Model Context Protocol) tools under the hood

## Data Types

### MouseButton

Represents mouse button types for click operations.

```go
type MouseButton string

const (
    MouseButtonLeft       MouseButton = "left"       // Left mouse button
    MouseButtonRight      MouseButton = "right"      // Right mouse button
    MouseButtonMiddle     MouseButton = "middle"     // Middle mouse button
    MouseButtonDoubleLeft MouseButton = "double_left" // Double click with left button
)
```

### ScrollDirection

Represents scroll directions for mouse wheel operations.

```go
type ScrollDirection string

const (
    ScrollDirectionUp    ScrollDirection = "up"     // Scroll up
    ScrollDirectionDown  ScrollDirection = "down"   // Scroll down
    ScrollDirectionLeft  ScrollDirection = "left"   // Scroll left
    ScrollDirectionRight ScrollDirection = "right"  // Scroll right
)
```

### CursorPosition

Represents the cursor position on screen.

```go
type CursorPosition struct {
    models.ApiResponse
    X            int    // X coordinate
    Y            int    // Y coordinate
    ErrorMessage string // Error message if operation failed
}
```

### ScreenSize

Represents the screen dimensions.

```go
type ScreenSize struct {
    models.ApiResponse
    Width            int     // Screen width in pixels
    Height           int     // Screen height in pixels
    DpiScalingFactor float64 // DPI scaling factor
    ErrorMessage     string  // Error message if operation failed
}
```

### ScreenshotResult

Represents the result of a screenshot operation.

```go
type ScreenshotResult struct {
    models.ApiResponse
    Data         string // Screenshot URL or base64 data
    ErrorMessage string // Error message if operation failed
}
```

### BoolResult

Represents a boolean operation result.

```go
type BoolResult struct {
    models.ApiResponse
    Success      bool   // Whether the operation succeeded
    ErrorMessage string // Error message if operation failed
}
```

## Methods

### Mouse Operations

#### ClickMouse

Clicks the mouse at the specified coordinates with the given button.

```go
func (c *Computer) ClickMouse(x, y int, button MouseButton) *BoolResult
```

**Parameters:**
- `x` (int): X coordinate for the click
- `y` (int): Y coordinate for the click
- `button` (MouseButton): Mouse button to click (left, right, middle, double_left)

**Returns:**
- `*BoolResult`: Result indicating success or failure

**Validation:**
- Valid buttons: `left`, `right`, `middle`, `double_left`
- Invalid button values will return an error result

**Example:**
```go
// Left click at coordinates (100, 100)
// Verified: ✓ API response: "Mouse clicked at (100, 100) with left button successfully"
result := session.Computer.ClickMouse(100, 100, computer.MouseButtonLeft)
if result.Success {
    fmt.Println("Mouse clicked successfully")
}

// Right click at coordinates (200, 200)
// Verified: ✓ API response: "Mouse clicked at (200, 200) with right button successfully"
result = session.Computer.ClickMouse(200, 200, computer.MouseButtonRight)
```

---

#### MoveMouse

Moves the mouse cursor to specific coordinates.

```go
func (c *Computer) MoveMouse(x, y int) *BoolResult
```

**Parameters:**
- `x` (int): Target X coordinate
- `y` (int): Target Y coordinate

**Returns:**
- `*BoolResult`: Result indicating success or failure

**Example:**
```go
// Move mouse to coordinates (100, 100)
// Verified: ✓ API response: "Mouse moved to (100, 100) successfully"
result := session.Computer.MoveMouse(100, 100)
if result.Success {
    fmt.Println("Mouse moved successfully")
}
```

---

#### DragMouse

Drags the mouse from one point to another while holding a mouse button.

```go
func (c *Computer) DragMouse(fromX, fromY, toX, toY int, button MouseButton) *BoolResult
```

**Parameters:**
- `fromX` (int): Starting X coordinate
- `fromY` (int): Starting Y coordinate
- `toX` (int): Ending X coordinate
- `toY` (int): Ending Y coordinate
- `button` (MouseButton): Mouse button to hold during drag (left, right, middle)

**Returns:**
- `*BoolResult`: Result indicating success or failure

**Validation:**
- Valid buttons for drag: `left`, `right`, `middle` (double_left is not valid for drag)
- Invalid button values will return an error result

**Example:**
```go
// Drag from (100, 100) to (200, 200) with left button
// Verified: ✓ API response: "Mouse dragged from (100, 100) to (200, 200) with left button successfully"
result := session.Computer.DragMouse(100, 100, 200, 200, computer.MouseButtonLeft)
if result.Success {
    fmt.Println("Drag operation completed")
}
```

---

#### Scroll

Scrolls the mouse wheel at specific coordinates.

```go
func (c *Computer) Scroll(x, y int, direction ScrollDirection, amount int) *BoolResult
```

**Parameters:**
- `x` (int): X coordinate where to scroll
- `y` (int): Y coordinate where to scroll
- `direction` (ScrollDirection): Scroll direction (up, down, left, right)
- `amount` (int): Amount to scroll

**Returns:**
- `*BoolResult`: Result indicating success or failure

**Validation:**
- Valid directions: `up`, `down`, `left`, `right`
- Invalid direction values will return an error result

**Example:**
```go
// Scroll down 5 units at coordinates (500, 500)
// Verified: ✓ API response: "Mouse scrolled at (500, 500) direction: down amount: 5 successfully"
result := session.Computer.Scroll(500, 500, computer.ScrollDirectionDown, 5)
if result.Success {
    fmt.Println("Scrolled successfully")
}
```

---

#### GetCursorPosition

Gets the current cursor position on the screen.

```go
func (c *Computer) GetCursorPosition() *CursorPosition
```

**Returns:**
- `*CursorPosition`: Current cursor position with X and Y coordinates

**Example:**
```go
// Get current cursor position
// Verified: ✓ Returns actual coordinates {"x":512,"y":384}
position := session.Computer.GetCursorPosition()
if position.ErrorMessage == "" {
    fmt.Printf("Cursor at: (%d, %d)\n", position.X, position.Y)
}
```

---

### Keyboard Operations

#### InputText

Inputs text into the active field.

```go
func (c *Computer) InputText(text string) *BoolResult
```

**Parameters:**
- `text` (string): Text to input

**Returns:**
- `*BoolResult`: Result indicating success or failure

**Example:**
```go
// Type text into the currently focused field
// Verified: ✓ API response: "Text sent successfully. Characters: 14"
result := session.Computer.InputText("Hello AgentBay")
if result.Success {
    fmt.Println("Text input successfully")
}
```

---

#### PressKeys

Presses multiple keyboard keys simultaneously.

```go
func (c *Computer) PressKeys(keys []string, hold bool) *BoolResult
```

**Parameters:**
- `keys` ([]string): Array of key names to press (e.g., ["Ctrl", "C"])
- `hold` (bool): Whether to hold the keys (true) or press and release (false)

**Returns:**
- `*BoolResult`: Result indicating success or failure

**Important Notes:**
- Key names are **case-sensitive** and must use proper capitalization
- Common keys: `Ctrl`, `Alt`, `Shift`, `Enter`, `Escape`, `Tab`, `Backspace`, `Delete`
- Letter keys: use lowercase like `a`, `b`, `c`
- Function keys: `F1`, `F2`, etc.
- **Incorrect**: `ctrl`, `shift`, `alt` (lowercase will fail)
- **Correct**: `Ctrl`, `Shift`, `Alt` (proper capitalization)

**Example:**
```go
// Press Ctrl+C (copy)
// IMPORTANT: Use "Ctrl" not "ctrl"
// Verified: ✓ API response: "Keys pressed and released successfully"
result := session.Computer.PressKeys([]string{"Ctrl", "c"}, false)
if result.Success {
    fmt.Println("Ctrl+C pressed")
}

// Press Alt+F4 (close window)
result = session.Computer.PressKeys([]string{"Alt", "F4"}, false)

// Hold Shift key
result = session.Computer.PressKeys([]string{"Shift"}, true)
```

---

#### ReleaseKeys

Releases multiple keyboard keys that were previously held.

```go
func (c *Computer) ReleaseKeys(keys []string) *BoolResult
```

**Parameters:**
- `keys` ([]string): Array of key names to release

**Returns:**
- `*BoolResult`: Result indicating success or failure

**Example:**
```go
// Release Shift key after holding
// Verified: ✓ API response: "Keys released successfully"
result := session.Computer.ReleaseKeys([]string{"Shift"})
if result.Success {
    fmt.Println("Keys released")
}
```

---

### Screen Operations

#### GetScreenSize

Gets the size of the primary screen.

```go
func (c *Computer) GetScreenSize() *ScreenSize
```

**Returns:**
- `*ScreenSize`: Screen dimensions including width, height, and DPI scaling factor

**Example:**
```go
// Get screen size information
// Verified: ✓ Returns {"dpiScalingFactor":1.0,"height":768,"width":1024}
size := session.Computer.GetScreenSize()
if size.ErrorMessage == "" {
    fmt.Printf("Screen: %dx%d, DPI: %.2f\n",
        size.Width, size.Height, size.DpiScalingFactor)
}
```

---

#### Screenshot

Takes a screenshot of the current screen.

```go
func (c *Computer) Screenshot() *ScreenshotResult
```

**Returns:**
- `*ScreenshotResult`: Screenshot data (typically a URL to the image)

**Example:**
```go
// Capture screenshot
// Verified: ✓ Returns OSS URL to screenshot image (1035 bytes URL)
// Example: https://wuying-intelligence-service-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/mcp/...
screenshot := session.Computer.Screenshot()
if screenshot.ErrorMessage == "" {
    fmt.Printf("Screenshot URL: %s\n", screenshot.Data)
    // screenshot.Data contains a URL to download the image
}
```

---

### Window Management

The Computer module provides convenient wrapper methods for window operations. These methods internally use the WindowManager.

#### ListRootWindows

Lists all root windows.

```go
func (c *Computer) ListRootWindows(timeoutMs ...int) (*window.WindowListResult, error)
```

**Parameters:**
- `timeoutMs` (int, optional): Timeout in milliseconds

**Returns:**
- `*window.WindowListResult`: List of root windows
- `error`: Error if operation fails

**Example:**
```go
// List all root windows
// Verified: ✓ Returns [{"pid":7488,"pname":"explorer.exe","window_id":65906,"window_title":"Program Manager"}]
result, err := session.Computer.ListRootWindows()
if err == nil {
    for _, win := range result.Windows {
        fmt.Printf("Window: %s (ID: %d, PID: %d)\n",
            win.Title, win.WindowID, win.PID)
    }
}
```

---

#### GetActiveWindow

Gets the currently active window.

```go
func (c *Computer) GetActiveWindow(timeoutMs ...int) (*window.WindowDetailResult, error)
```

**Parameters:**
- `timeoutMs` (int, optional): Timeout in milliseconds

**Returns:**
- `*window.WindowDetailResult`: Details of the active window
- `error`: Error if operation fails

**Example:**
```go
// Get the active window
// Verified: ✓ Returns {"pid":7488,"pname":"explorer.exe","window_id":65906,"window_title":"Program Manager"}
result, err := session.Computer.GetActiveWindow()
if err == nil && result.Window != nil {
    fmt.Printf("Active: %s (ID: %d)\n",
        result.Window.Title, result.Window.WindowID)
}
```

---

#### ActivateWindow

Activates the specified window.

```go
func (c *Computer) ActivateWindow(windowID int) (*window.WindowResult, error)
```

**Parameters:**
- `windowID` (int): ID of the window to activate

**Returns:**
- `*window.WindowResult`: Result of the activation operation
- `error`: Error if operation fails

**Example:**
```go
// Activate window with ID 65906 (from ListRootWindows)
result, err := session.Computer.ActivateWindow(65906)
if err == nil {
    fmt.Println("Window activated")
}
```

---

#### CloseWindow

Closes the specified window.

```go
func (c *Computer) CloseWindow(windowID int) (*window.WindowResult, error)
```

**Parameters:**
- `windowID` (int): ID of the window to close

**Returns:**
- `*window.WindowResult`: Result of the close operation
- `error`: Error if operation fails

**Example:**
```go
// Close window with ID 65906 (from ListRootWindows)
result, err := session.Computer.CloseWindow(65906)
if err == nil {
    fmt.Println("Window closed")
}
```

---

#### MaximizeWindow

Maximizes the specified window.

```go
func (c *Computer) MaximizeWindow(windowID int) (*window.WindowResult, error)
```

**Parameters:**
- `windowID` (int): ID of the window to maximize

**Returns:**
- `*window.WindowResult`: Result of the maximize operation
- `error`: Error if operation fails

---

#### MinimizeWindow

Minimizes the specified window.

```go
func (c *Computer) MinimizeWindow(windowID int) (*window.WindowResult, error)
```

**Parameters:**
- `windowID` (int): ID of the window to minimize

**Returns:**
- `*window.WindowResult`: Result of the minimize operation
- `error`: Error if operation fails

---

#### RestoreWindow

Restores the specified window.

```go
func (c *Computer) RestoreWindow(windowID int) (*window.WindowResult, error)
```

**Parameters:**
- `windowID` (int): ID of the window to restore

**Returns:**
- `*window.WindowResult`: Result of the restore operation
- `error`: Error if operation fails

---

#### ResizeWindow

Resizes the specified window.

```go
func (c *Computer) ResizeWindow(windowID int, width int, height int) (*window.WindowResult, error)
```

**Parameters:**
- `windowID` (int): ID of the window to resize
- `width` (int): New width in pixels
- `height` (int): New height in pixels

**Returns:**
- `*window.WindowResult`: Result of the resize operation
- `error`: Error if operation fails

**Example:**
```go
// Resize window to 800x600 (use window ID from ListRootWindows)
result, err := session.Computer.ResizeWindow(65906, 800, 600)
```

---

#### FullscreenWindow

Makes the specified window fullscreen.

```go
func (c *Computer) FullscreenWindow(windowID int) (*window.WindowResult, error)
```

**Parameters:**
- `windowID` (int): ID of the window to make fullscreen

**Returns:**
- `*window.WindowResult`: Result of the fullscreen operation
- `error`: Error if operation fails

---

#### FocusMode

Toggles focus mode on or off.

```go
func (c *Computer) FocusMode(on bool) (*window.WindowResult, error)
```

**Parameters:**
- `on` (bool): true to enable focus mode, false to disable

**Returns:**
- `*window.WindowResult`: Result of the operation
- `error`: Error if operation fails

---

## Complete Usage Example

This example demonstrates a complete workflow of computer automation:

```go
package main

import (
    "fmt"
    "os"

    "github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
    // Initialize client
    client, err := agentbay.NewAgentBay("", nil)
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        os.Exit(1)
    }

    // Create Windows session
    // Verified: ✓ Session ID example: session-04bdw8o39qewm36xz
    params := agentbay.NewCreateSessionParams().
        WithImageId("windows_latest")

    result, err := client.Create(params)
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        os.Exit(1)
    }

    session := result.Session
    fmt.Printf("Session created: %s\n", session.SessionID)

    defer client.Delete(session)

    // Get screen information
    // Verified: ✓ Returns {"dpiScalingFactor":1.0,"height":768,"width":1024}
    size := session.Computer.GetScreenSize()
    fmt.Printf("Screen: %dx%d, DPI: %.2f\n",
        size.Width, size.Height, size.DpiScalingFactor)

    // Capture initial screenshot
    // Verified: ✓ Returns OSS URL (1035 bytes)
    screenshot := session.Computer.Screenshot()
    if screenshot.ErrorMessage == "" {
        fmt.Println("Screenshot captured:", screenshot.Data)
    }

    // Get cursor position
    // Verified: ✓ Returns {"x":512,"y":384}
    cursor := session.Computer.GetCursorPosition()
    fmt.Printf("Cursor at: (%d, %d)\n", cursor.X, cursor.Y)

    // Move mouse
    // Verified: ✓ API response: "Mouse moved to (100, 100) successfully"
    session.Computer.MoveMouse(100, 100)

    // Click at position
    // Verified: ✓ API response: "Mouse clicked at (100, 100) with left button successfully"
    session.Computer.ClickMouse(100, 100, "left")

    // Input text
    // Verified: ✓ API response: "Text sent successfully. Characters: 14"
    session.Computer.InputText("Hello AgentBay")

    // Press Ctrl+C
    // Verified: ✓ API response: "Keys pressed and released successfully"
    session.Computer.PressKeys([]string{"Ctrl", "c"}, false)

    // List windows
    // Verified: ✓ Returns [{"pid":7488,"pname":"explorer.exe","window_id":65906,"window_title":"Program Manager"}]
    windows, err := session.Computer.ListRootWindows()
    if err == nil {
        fmt.Printf("Found %d windows\n", len(windows.Windows))
        for _, win := range windows.Windows {
            fmt.Printf("  - %s (ID: %d)\n", win.Title, win.WindowID)
        }
    }

    // Get active window
    // Verified: ✓ Returns {"pid":7488,"pname":"explorer.exe","window_id":65906,"window_title":"Program Manager"}
    activeWin, err := session.Computer.GetActiveWindow()
    if err == nil && activeWin.Window != nil {
        fmt.Printf("Active window: %s\n", activeWin.Window.Title)
    }
}
```

## Best Practices

1. **Session Image**: This module has been verified with the `windows_latest` image
2. **Error Checking**: Check `ErrorMessage` field for operation results
3. **Coordinates**: Ensure coordinates are within screen bounds (use `GetScreenSize()` to check)
4. **Key Names**: Use proper capitalization for key names (`Ctrl` not `ctrl`)
5. **Window IDs**: Use `ListRootWindows()` or `GetActiveWindow()` to get valid window IDs
6. **Screenshot Data**: The screenshot data is typically a URL that can be downloaded

## Related Resources

- [Session API Reference](session.md)
- [Window API Reference](window.md)
- [UI API Reference](ui.md)
