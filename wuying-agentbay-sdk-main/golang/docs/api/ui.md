# UI Class API Reference

> **⚠️ DEPRECATED**: This API is deprecated. Please use the [Computer API](computer.md) or [Mobile API](mobile.md) instead for UI automation functionality.

The `UI` class provides methods for interacting with UI elements in the AgentBay cloud environment. This includes retrieving UI elements, sending key events, inputting text, performing gestures, and taking screenshots.

## Properties

###

- `KeyCode`: Constants for key codes that can be used with the `send_key` method.
  - `HOME`: Home key (3)
  - `BACK`: Back key (4)
  - `VOLUME_UP`: Volume up key (24)
  - `VOLUME_DOWN`: Volume down key (25)
  - `POWER`: Power key (26)
  - `MENU`: Menu key (82)

## Methods


Retrieves all clickable UI elements within the specified timeout.


```go
GetClickableUIElements(timeoutMs int) (*UIElementsResult, error)
```

**Parameters:**
- `timeoutMs` (int): The timeout in milliseconds. If <= 0, default is 2000ms.

**Returns:**
- `*UIElementsResult`: A result object containing clickable UI elements and RequestID.
- `error`: An error if the operation fails.

**UIElementsResult Structure:**
```go
type UIElementsResult struct {
    RequestID string      // Unique request identifier for debugging
    Elements  []*UIElement // Array of UI elements
}

type UIElement struct {
    Bounds     string       // Bounds of the element
    ClassName  string       // CSS class name
    Text       string       // Text content
    Type       string       // Element type
    ResourceId string       // Resource ID
    Index      int          // Element index
    IsParent   bool         // Whether this element is a parent
    Children   []*UIElement // Child elements
}
```


Retrieves all UI elements within the specified timeout.


```go
GetAllUIElements(timeoutMs int) (*UIElementsResult, error)
```

**Parameters:**
- `timeoutMs` (int): The timeout in milliseconds. If <= 0, default is 2000ms.

**Returns:**
- `*UIElementsResult`: A result object containing all UI elements and RequestID.
- `error`: An error if the operation fails.


Sends a key press event.


```go
SendKey(key int) (*KeyActionResult, error)
```

**Parameters:**
- `key` (int): The key code to send. Use the `KeyCode` constants.

**Returns:**
- `*KeyActionResult`: A result object containing success status and RequestID.
- `error`: An error if the operation fails.

**KeyActionResult Structure:**
```go
type KeyActionResult struct {
    RequestID string // Unique request identifier for debugging
    Success   bool   // Whether the key press was successful
}
```


Inputs text into the active field.


```go
InputText(text string) (*TextInputResult, error)
```

**Parameters:**
- `text` (string): The text to input.

**Returns:**
- `*TextInputResult`: A result object containing the input text and RequestID.
- `error`: An error if the operation fails.

**TextInputResult Structure:**
```go
type TextInputResult struct {
    RequestID string // Unique request identifier for debugging
    Text      string // The text that was input
}
```


Performs a swipe gesture on the screen.


```go
Swipe(startX, startY, endX, endY, durationMs int) (*SwipeResult, error)
```

**Parameters:**
- `startX` (int): The starting X coordinate.
- `startY` (int): The starting Y coordinate.
- `endX` (int): The ending X coordinate.
- `endY` (int): The ending Y coordinate.
- `durationMs` (int): The duration of the swipe in milliseconds.

**Returns:**
- `*SwipeResult`: A result object containing success status and RequestID.
- `error`: An error if the operation fails.

**SwipeResult Structure:**
```go
type SwipeResult struct {
    RequestID string // Unique request identifier for debugging
    Success   bool   // Whether the swipe was successful
}
```


Clicks on the screen at the specified coordinates.


```go
Click(x, y int, button string) (*UIResult, error)
```

**Parameters:**
- `x` (int): The X coordinate.
- `y` (int): The Y coordinate.
- `button` (string): The mouse button to use. If empty, default is 'left'.

**Returns:**
- `*UIResult`: A result object containing success status and RequestID.
- `error`: An error if the operation fails.

**UIResult Structure:**
```go
type UIResult struct {
    RequestID  string // Unique request identifier for debugging
    ComponentID string // Component ID (if applicable)
    Success    bool   // Whether the operation was successful
}
```


Takes a screenshot of the current screen.


```go
Screenshot() (*UIResult, error)
```

**Returns:**
- `*UIResult`: A result object containing success status and RequestID.
- `error`: An error if the operation fails.

## UI Element Structure

UI elements returned by `GetClickableUIElements` and `GetAllUIElements` have the following structure:

```go
type UIElement struct {
    Bounds      string      `json:"bounds"`
    ClassName   string      `json:"className"`
    Text        string      `json:"text"`
    Type        string      `json:"type"`
    ResourceID  string      `json:"resourceId"`
    Index       int         `json:"index"`
    IsParent    bool        `json:"isParent"`
    Children    []UIElement `json:"children"`
}
```

## Usage Examples

### UI Interactions

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

    // Take a screenshot
    screenshotResult, err := session.UI.Screenshot()
    if err != nil {
        log.Printf("Error taking screenshot: %v", err)
    } else {
        fmt.Printf("Screenshot taken successfully: %t\n", screenshotResult.Success)
    }

    // Get all UI elements
    elementsResult, err := session.UI.GetAllUIElements(2000)
    if err != nil {
        log.Printf("Error getting UI elements: %v", err)
    } else {
        fmt.Printf("Retrieved %d UI elements\n", len(elementsResult.Elements))
    }

    // Get clickable UI elements
    clickableResult, err := session.UI.GetClickableUIElements(2000)
    if err != nil {
        log.Printf("Error getting clickable elements: %v", err)
    } else {
        fmt.Printf("Retrieved %d clickable UI elements\n", len(clickableResult.Elements))
    }

    // Send a key press
    keyResult, err := session.UI.SendKey(3) // HOME key
    if err != nil {
        log.Printf("Error sending key: %v", err)
    } else {
        fmt.Printf("Key sent successfully: %t\n", keyResult.Success)
    }

    // Input text
    inputResult, err := session.UI.InputText("Hello, world!")
    if err != nil {
        log.Printf("Error inputting text: %v", err)
    } else {
        fmt.Printf("Text input successfully: %t\n", inputResult.Success)
    }

    // Perform a swipe gesture
    swipeResult, err := session.UI.Swipe(100, 500, 100, 100, 500)
    if err != nil {
        log.Printf("Error performing swipe: %v", err)
    } else {
        fmt.Printf("Swipe performed successfully: %t\n", swipeResult.Success)
    }

    // Click on the screen
    clickResult, err := session.UI.Click(200, 300, "left")
    if err != nil {
        log.Printf("Error clicking: %v", err)
    } else {
        fmt.Printf("Click performed successfully: %t\n", clickResult.Success)
    }
}
```

## Related Resources

- [Session Class](session.md): The Session class that provides access to the UI class.