# Window Class

> **⚠️ DEPRECATED**: This API is deprecated. Please use the [Computer API](computer.md) instead for window management functionality.

The Window class provides methods for managing windows in the AgentBay cloud environment, including listing windows, getting the active window, and manipulating window states.

## Overview

The Window class is accessed through a session instance and provides methods for window management in the cloud environment.

## Data Types


Represents a window in the system.


```go
type Window struct {
    WindowID           int      `json:"window_id"`
    Title              string   `json:"title"`
    AbsoluteUpperLeftX int      `json:"absolute_upper_left_x,omitempty"`
    AbsoluteUpperLeftY int      `json:"absolute_upper_left_y,omitempty"`
    Width              int      `json:"width,omitempty"`
    Height             int      `json:"height,omitempty"`
    PID                int      `json:"pid,omitempty"`
    PName              string   `json:"pname,omitempty"`
    ChildWindows       []Window `json:"child_windows,omitempty"`
}
```

## Methods


Lists all root windows in the system.


```go
func (wm *WindowManager) ListRootWindows() (*WindowListResult, error)
```

**Returns:**
- `*WindowListResult`: A result object containing the list of root windows and request ID.
- `error`: An error if the operation fails.


Gets the currently active window.


```go
func (wm *WindowManager) GetActiveWindow() (*WindowDetailResult, error)
```

**Returns:**
- `*WindowDetailResult`: A result object containing the active window and request ID.
- `error`: An error if the operation fails.


Activates (brings to front) a window by ID.


```go
func (wm *WindowManager) ActivateWindow(windowID int) (*WindowResult, error)
```

**Parameters:**
- `windowID` (int): The ID of the window to activate.

**Returns:**
- `*WindowResult`: A result object containing the success status and request ID.
- `error`: An error if the operation fails.


Minimizes a window by ID.


```go
func (wm *WindowManager) MinimizeWindow(windowID int) (*WindowResult, error)
```

**Parameters:**
- `windowID` (int): The ID of the window to minimize.

**Returns:**
- `*WindowResult`: A result object containing the success status and request ID.
- `error`: An error if the operation fails.


Maximizes a window by ID.


```go
func (wm *WindowManager) MaximizeWindow(windowID int) (*WindowResult, error)
```

**Parameters:**
- `windowID` (int): The ID of the window to maximize.

**Returns:**
- `*WindowResult`: A result object containing the success status and request ID.
- `error`: An error if the operation fails.


Restores a window by ID (from minimized or maximized state).


```go
func (wm *WindowManager) RestoreWindow(windowID int) (*WindowResult, error)
```

**Parameters:**
- `windowID` (int): The ID of the window to restore.

**Returns:**
- `*WindowResult`: A result object containing the success status and request ID.
- `error`: An error if the operation fails.


Makes a window fullscreen by ID.


```go
func (wm *WindowManager) FullscreenWindow(windowID int) (*WindowResult, error)
```

**Parameters:**
- `windowID` (int): The ID of the window to make fullscreen.

**Returns:**
- `*WindowResult`: A result object containing the success status and request ID.
- `error`: An error if the operation fails.


Resizes a window by ID to the specified width and height.


```go
func (wm *WindowManager) ResizeWindow(windowID, width, height int) (*WindowResult, error)
```

**Parameters:**
- `windowID` (int): The ID of the window to resize.
- `width` (int): The new width of the window.
- `height` (int): The new height of the window.

**Returns:**
- `*WindowResult`: A result object containing the success status and request ID.
- `error`: An error if the operation fails.


Closes a window by ID.


```go
func (wm *WindowManager) CloseWindow(windowID int) (*WindowResult, error)
```

**Parameters:**
- `windowID` (int): The ID of the window to close.

**Returns:**
- `*WindowResult`: A result object containing the success status and request ID.
- `error`: An error if the operation fails.


Enables or disables focus mode, which prevents window switching.


```go
func (wm *WindowManager) FocusMode(on bool) (*WindowResult, error)
```

**Parameters:**
- `on` (bool): True to enable focus mode, False to disable it.

**Returns:**
- `*WindowResult`: A result object containing the success status and request ID.
- `error`: An error if the operation fails.

## Usage Examples

### Window Management

```go
package main

import (
    "fmt"
    "log"
)

func main() {
    // Create a session
    agentBay := agentbay.NewAgentBay("your-api-key")
    sessionResult, err := agentBay.Create(nil)
    if err != nil {
        log.Fatal(err)
    }
    session := sessionResult.Session

    // List root windows
    windowsResult, err := session.Window.ListRootWindows(3000)
    if err != nil {
        log.Printf("Error listing windows: %v", err)
    } else {
        for _, window := range windowsResult.Windows {
            fmt.Printf("Window: %s (ID: %d, Process: %s, PID: %d)\n", 
                window.Title, window.WindowID, window.PName, window.PID)
        }
    }

    // Get active window
    activeResult, err := session.Window.GetActiveWindow(3000)
    if err != nil {
        log.Printf("Error getting active window: %v", err)
    } else {
        fmt.Printf("Active window: %s (ID: %d)\n", 
            activeResult.Window.Title, activeResult.Window.WindowID)
    }

    // Manipulate windows
    if len(windowsResult.Windows) > 0 {
        windowID := windowsResult.Windows[0].WindowID
        
        // Maximize window
        err = session.Window.MaximizeWindow(windowID)
        if err != nil {
            log.Printf("Error maximizing window: %v", err)
        } else {
            fmt.Println("Window maximized")
        }
        
        // Restore window
        err = session.Window.RestoreWindow(windowID)
        if err != nil {
            log.Printf("Error restoring window: %v", err)
        } else {
            fmt.Println("Window restored")
        }
        
        // Resize window
        err = session.Window.ResizeWindow(windowID, 800, 600)
        if err != nil {
            log.Printf("Error resizing window: %v", err)
        } else {
            fmt.Println("Window resized")
        }
        
        // Activate window
        err = session.Window.ActivateWindow(windowID)
        if err != nil {
            log.Printf("Error activating window: %v", err)
        } else {
            fmt.Println("Window activated")
        }
    }
}
```

## Related Resources

- [Session Class](session.md): The session class that provides access to the Window class.
- [Application Class](application.md): The application class for managing applications in the cloud environment.
- [Applications Concept](../concepts/applications.md): Conceptual information about applications and windows in the AgentBay cloud environment. 