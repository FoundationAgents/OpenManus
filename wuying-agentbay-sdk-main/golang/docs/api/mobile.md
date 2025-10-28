# Mobile Module

The Mobile module provides comprehensive mobile UI automation capabilities for Android environments in the AgentBay cloud platform. It enables touch operations, UI element interactions, text input, application management, and screenshot capture.

## 📖 Related Tutorials

- [Mobile UI Automation Guide](../../../docs/guides/mobile-use/mobile-ui-automation.md) - Detailed tutorial on mobile UI automation
- [Mobile Application Management Guide](../../../docs/guides/mobile-use/mobile-application-management.md) - Tutorial on managing mobile applications

## Overview

The Mobile module is designed for automating Android mobile applications. It provides touch gestures, UI element discovery, application lifecycle management, and input control capabilities that are essential for mobile automation tasks.

**Requirements:**
- Session must be created with `mobile_latest` image
- All methods use MCP (Model Context Protocol) tools under the hood

## Data Types

### UIElement

Represents a UI element in the mobile interface.

```go
type UIElement struct {
    Bounds      *UIBounds // Element bounds (position and size)
    ClassName   string    // Element class name
    ContentDesc string    // Content description (accessibility)
    ElementID   string    // Element identifier
    Package     string    // Package name
    ResourceID  string    // Resource identifier
    Text        string    // Element text content
    Type        string    // Element type
}
```

### UIBounds

Represents the bounds (position and size) of a UI element.

```go
type UIBounds struct {
    Bottom int // Bottom coordinate
    Left   int // Left coordinate
    Right  int // Right coordinate
    Top    int // Top coordinate
}
```

### UIElementsResult

Represents the result containing UI elements.

```go
type UIElementsResult struct {
    models.ApiResponse
    Elements     []*UIElement // List of UI elements
    ErrorMessage string       // Error message if operation failed
}
```

### InstalledApp

Represents an installed application.

```go
type InstalledApp struct {
    Name          string // Application name
    StartCmd      string // Command to start the application
    StopCmd       string // Command to stop the application (optional)
    WorkDirectory string // Working directory (optional)
}
```

### Process

Represents a running process.

```go
type Process struct {
    PName   string // Process name
    PID     int    // Process ID
    CmdLine string // Command line (optional)
}
```

### InstalledAppListResult

Wraps installed app list and RequestID.

```go
type InstalledAppListResult struct {
    models.ApiResponse
    Apps         []InstalledApp // List of installed applications
    ErrorMessage string         // Error message if operation failed
}
```

### ProcessListResult

Wraps process list and RequestID.

```go
type ProcessListResult struct {
    models.ApiResponse
    Processes    []Process // List of running processes
    ErrorMessage string    // Error message if operation failed
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

### ScreenshotResult

Represents the result of a screenshot operation.

```go
type ScreenshotResult struct {
    models.ApiResponse
    Data         string // Screenshot URL or base64 data
    ErrorMessage string // Error message if operation failed
}
```

## Methods

### Touch Operations

#### Tap

Taps on the screen at specific coordinates.

```go
func (m *Mobile) Tap(x, y int) *BoolResult
```

**Parameters:**
- `x` (int): X coordinate for the tap
- `y` (int): Y coordinate for the tap

**Returns:**
- `*BoolResult`: Result indicating success or failure

**Example:**
```go
// Tap at coordinates (500, 500)
// Verified: ✓ Successfully taps at specified coordinates
result := session.Mobile.Tap(500, 500)
if result.Success {
    fmt.Println("Tap successful")
}
```

---

#### Swipe

Performs a swipe gesture on the screen.

```go
func (m *Mobile) Swipe(startX, startY, endX, endY, durationMs int) *BoolResult
```

**Parameters:**
- `startX` (int): Starting X coordinate
- `startY` (int): Starting Y coordinate
- `endX` (int): Ending X coordinate
- `endY` (int): Ending Y coordinate
- `durationMs` (int): Duration of the swipe in milliseconds

**Returns:**
- `*BoolResult`: Result indicating success or failure

**Example:**
```go
// Swipe from left to right
// Verified: ✓ Successfully performs swipe gesture
result := session.Mobile.Swipe(100, 500, 900, 500, 300)
if result.Success {
    fmt.Println("Swipe successful")
}

// Swipe up (scroll down)
result = session.Mobile.Swipe(500, 1000, 500, 200, 500)

// Swipe down (scroll up)
result = session.Mobile.Swipe(500, 200, 500, 1000, 500)
```

---

### Input Operations

#### InputText

Inputs text into the currently active field.

```go
func (m *Mobile) InputText(text string) *BoolResult
```

**Parameters:**
- `text` (string): Text to input

**Returns:**
- `*BoolResult`: Result indicating success or failure

**Example:**
```go
// Input text into focused field
// Verified: ✓ Successfully inputs text
result := session.Mobile.InputText("Hello Mobile")
if result.Success {
    fmt.Println("Text input successful")
}
```

---

#### SendKey

Sends a key press event using Android key codes.

```go
func (m *Mobile) SendKey(key int) *BoolResult
```

**Parameters:**
- `key` (int): Android key code (e.g., 4 for BACK, 3 for HOME, 82 for MENU)

**Returns:**
- `*BoolResult`: Result indicating success or failure

**Common Android Key Codes:**
- `3` - HOME
- `4` - BACK
- `24` - VOLUME_UP
- `25` - VOLUME_DOWN
- `26` - POWER
- `82` - MENU
- `84` - SEARCH
- `85` - PLAY_PAUSE

**Example:**
```go
// Press BACK button (key code 4)
result := session.Mobile.SendKey(4)
if result.Success {
    fmt.Println("BACK key sent")
}

// Press HOME button (key code 3)
result = session.Mobile.SendKey(3)
```

---

### UI Element Discovery

#### GetClickableUIElements

Retrieves all clickable UI elements within the specified timeout.

```go
func (m *Mobile) GetClickableUIElements(timeoutMs int) *UIElementsResult
```

**Parameters:**
- `timeoutMs` (int): Timeout in milliseconds to wait for UI elements

**Returns:**
- `*UIElementsResult`: Result containing list of clickable UI elements

**Example:**
```go
// Get all clickable elements with 5 second timeout
// Verified: ✓ Returns list of clickable UI elements (may be empty if no elements)
result := session.Mobile.GetClickableUIElements(5000)
if result.ErrorMessage == "" {
    fmt.Printf("Found %d clickable elements\n", len(result.Elements))
    for _, elem := range result.Elements {
        fmt.Printf("  - Text: %s, ResourceID: %s\n",
            elem.Text, elem.ResourceID)
    }
}
```

---

#### GetAllUIElements

Retrieves all UI elements within the specified timeout.

```go
func (m *Mobile) GetAllUIElements(timeoutMs int) *UIElementsResult
```

**Parameters:**
- `timeoutMs` (int): Timeout in milliseconds to wait for UI elements

**Returns:**
- `*UIElementsResult`: Result containing list of all UI elements

**Example:**
```go
// Get all UI elements with 5 second timeout
// Verified: ✓ Returns list of all UI elements
result := session.Mobile.GetAllUIElements(5000)
if result.ErrorMessage == "" {
    fmt.Printf("Found %d total elements\n", len(result.Elements))
    for _, elem := range result.Elements {
        if elem.Bounds != nil {
            fmt.Printf("  - Element: %s at (%d, %d, %d, %d)\n",
                elem.ClassName,
                elem.Bounds.Left, elem.Bounds.Top,
                elem.Bounds.Right, elem.Bounds.Bottom)
        }
    }
}
```

---

### Application Management

#### GetInstalledApps

Retrieves a list of installed applications.

```go
func (m *Mobile) GetInstalledApps(startMenu, desktop, ignoreSystemApps bool) *InstalledAppListResult
```

**Parameters:**
- `startMenu` (bool): Include apps from start menu
- `desktop` (bool): Include apps from desktop
- `ignoreSystemApps` (bool): Whether to exclude system applications

**Returns:**
- `*InstalledAppListResult`: Result containing list of installed applications

**Example:**
```go
// Get all user-installed apps (excluding system apps)
// Verified: ✓ Returns list of installed applications
result := session.Mobile.GetInstalledApps(true, true, true)
if result.ErrorMessage == "" {
    fmt.Printf("Found %d installed apps\n", len(result.Apps))
    for _, app := range result.Apps {
        fmt.Printf("  - %s: %s\n", app.Name, app.StartCmd)
    }
}

// Get all apps including system apps
result = session.Mobile.GetInstalledApps(true, true, false)
```

---

#### StartApp

Starts a specified application.

```go
func (m *Mobile) StartApp(startCmd, workDirectory, activity string) *ProcessListResult
```

**Parameters:**
- `startCmd` (string): Command to start the application
- `workDirectory` (string): Working directory for the application
- `activity` (string): Android activity to launch (for Android apps)

**Returns:**
- `*ProcessListResult`: Result containing list of processes for the started app

**Example:**
```go
// Start an Android app by package and activity
result := session.Mobile.StartApp(
    "com.example.app",           // Package name
    "",                          // Work directory (empty for default)
    "com.example.app.MainActivity" // Activity name
)
if result.ErrorMessage == "" {
    fmt.Printf("App started with %d processes\n", len(result.Processes))
    for _, proc := range result.Processes {
        fmt.Printf("  - Process: %s (PID: %d)\n", proc.PName, proc.PID)
    }
}
```

---

#### StopAppByPName

Stops an application by its process name.

```go
func (m *Mobile) StopAppByPName(pname string) *BoolResult
```

**Parameters:**
- `pname` (string): Process name of the application to stop

**Returns:**
- `*BoolResult`: Result indicating success or failure

**Example:**
```go
// Stop an app by process name
result := session.Mobile.StopAppByPName("com.example.app")
if result.Success {
    fmt.Println("App stopped successfully")
}
```

---

### Screen Operations

#### Screenshot

Takes a screenshot of the current mobile screen.

```go
func (m *Mobile) Screenshot() *ScreenshotResult
```

**Returns:**
- `*ScreenshotResult`: Screenshot data (typically a URL to the image)

**Example:**
```go
// Capture mobile screenshot
// Verified: ✓ Returns OSS URL to screenshot image (1035 bytes URL)
screenshot := session.Mobile.Screenshot()
if screenshot.ErrorMessage == "" {
    fmt.Printf("Screenshot URL: %s\n", screenshot.Data)
    // screenshot.Data contains a URL to download the image
}
```

---

## Complete Usage Example

This example demonstrates a complete workflow of mobile automation:

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

    // Create mobile session
    // Verified: ✓ Session creates successfully with mobile_latest image
    params := agentbay.NewCreateSessionParams().
        WithImageId("mobile_latest")

    result, err := client.Create(params)
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        os.Exit(1)
    }

    session := result.Session
    fmt.Printf("Session created: %s\n", session.SessionID)

    defer client.Delete(session)

    // Take initial screenshot
    // Verified: ✓ Returns OSS URL
    screenshot := session.Mobile.Screenshot()
    fmt.Println("Screenshot:", screenshot.Data)

    // Tap on screen center
    // Verified: ✓ Successfully taps
    session.Mobile.Tap(500, 500)

    // Swipe left to right
    // Verified: ✓ Successfully swipes
    session.Mobile.Swipe(100, 500, 900, 500, 300)

    // Input text
    // Verified: ✓ Successfully inputs text
    session.Mobile.InputText("Search query")

    // Press BACK button
    session.Mobile.SendKey(4)

    // Get clickable UI elements
    // Verified: ✓ Returns list of elements
    elements := session.Mobile.GetClickableUIElements(5000)
    fmt.Printf("Found %d clickable elements\n", len(elements.Elements))

    // Find and interact with specific element
    for _, elem := range elements.Elements {
        if elem.Text == "Login" {
            // Tap on the element center
            if elem.Bounds != nil {
                centerX := (elem.Bounds.Left + elem.Bounds.Right) / 2
                centerY := (elem.Bounds.Top + elem.Bounds.Bottom) / 2
                session.Mobile.Tap(centerX, centerY)
            }
            break
        }
    }

    // Get all UI elements
    // Verified: ✓ Returns all elements
    allElements := session.Mobile.GetAllUIElements(5000)
    fmt.Printf("Found %d total elements\n", len(allElements.Elements))

    // Get installed apps
    // Verified: ✓ Returns list of apps
    apps := session.Mobile.GetInstalledApps(true, true, true)
    fmt.Printf("Found %d apps\n", len(apps.Apps))
    for _, app := range apps.Apps {
        fmt.Printf("  - %s\n", app.Name)
    }

    // Start an app (example)
    if len(apps.Apps) > 0 {
        app := apps.Apps[0]
        processes := session.Mobile.StartApp(app.StartCmd, app.WorkDirectory, "")
        if processes.ErrorMessage == "" {
            fmt.Printf("Started app with %d processes\n", len(processes.Processes))

            // Stop the app
            if len(processes.Processes) > 0 {
                session.Mobile.StopAppByPName(processes.Processes[0].PName)
            }
        }
    }
}
```

## UI Element Interaction Pattern

A common pattern for interacting with UI elements:

```go
// 1. Get clickable elements
elements := session.Mobile.GetClickableUIElements(5000)

// 2. Find element by various criteria
var targetElement *mobile.UIElement

// Find by text
for _, elem := range elements.Elements {
    if elem.Text == "Submit" {
        targetElement = elem
        break
    }
}

// Find by resource ID
for _, elem := range elements.Elements {
    if elem.ResourceID == "com.example:id/button_login" {
        targetElement = elem
        break
    }
}

// Find by content description
for _, elem := range elements.Elements {
    if elem.ContentDesc == "Login button" {
        targetElement = elem
        break
    }
}

// 3. Tap on element center
if targetElement != nil && targetElement.Bounds != nil {
    centerX := (targetElement.Bounds.Left + targetElement.Bounds.Right) / 2
    centerY := (targetElement.Bounds.Top + targetElement.Bounds.Bottom) / 2
    session.Mobile.Tap(centerX, centerY)
}
```

## Common Mobile Gestures

```go
// Scroll down (swipe up)
session.Mobile.Swipe(500, 1200, 500, 300, 400)

// Scroll up (swipe down)
session.Mobile.Swipe(500, 300, 500, 1200, 400)

// Scroll left (swipe right)
session.Mobile.Swipe(200, 600, 800, 600, 400)

// Scroll right (swipe left)
session.Mobile.Swipe(800, 600, 200, 600, 400)

// Quick tap
session.Mobile.Tap(500, 500)

// Long press (use longer swipe duration at same position)
session.Mobile.Swipe(500, 500, 500, 500, 1000)
```

## Best Practices

1. **Session Image**: Always use `mobile_latest` image for Mobile module operations
2. **Error Checking**: Check `ErrorMessage` field for operation results
3. **Timeout Values**: Use appropriate timeout values for UI element discovery (typically 5000-10000ms)
4. **Element Bounds**: Always check if `Bounds` is not nil before accessing coordinates
5. **Screenshots**: Take screenshots before and after critical operations for debugging
6. **Wait Strategy**: After tapping or swiping, add small delays or wait for UI updates
7. **Key Codes**: Refer to Android KeyEvent documentation for key codes
8. **App Management**: Use `GetInstalledApps()` to discover available applications

## Limitations

- SendKey operation may timeout in some environments (verified in tests)
- UI element discovery returns empty list when no UI is displayed
- Application management is limited to available apps in the mobile environment

## Related Resources

- [Session API Reference](session.md)
- [Computer API Reference](computer.md) - For Windows automation
- [UI API Reference](ui.md)
