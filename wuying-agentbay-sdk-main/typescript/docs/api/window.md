# Window Class

> **⚠️ DEPRECATED**: This API is deprecated. Please use the [Computer API](computer.md) instead for window management functionality.

The Window class provides methods for managing windows in the AgentBay cloud environment, including listing windows, getting the active window, and manipulating window states.

## Overview

The Window class is accessed through a session instance and provides methods for window management in the cloud environment.

## Data Types


Represents a window in the system.


```typescript
interface Window {
    window_id: number;         // The unique identifier of the window
    title: string;             // The title of the window
    absolute_upper_left_x?: number; // The X coordinate of the upper left corner (optional)
    absolute_upper_left_y?: number; // The Y coordinate of the upper left corner (optional)
    width?: number;            // The width of the window (optional)
    height?: number;           // The height of the window (optional)
    pid?: number;              // The process ID of the process that owns the window (optional)
    pname?: string;            // The name of the process that owns the window (optional)
    child_windows?: Window[];  // The child windows of this window (optional)
}
```

## Methods

### listRootWindows

```typescript
async listRootWindows(timeoutMs?: number): Promise<WindowListResult>
```

**Parameters:**
- `timeoutMs` (number, optional): The timeout in milliseconds. Default is 3000ms.

**Returns:**
- `Promise<WindowListResult>`: A promise that resolves to a result object containing the list of root windows and request ID.


### getActiveWindow

```typescript
async getActiveWindow(): Promise<WindowInfoResult>
```

**Returns:
- `Promise<WindowInfoResult>`: A promise that resolves to a result object containing the active window and request ID.


### activateWindow

```typescript
async activateWindow(windowId: number): Promise<BoolResult>
```

**Parameters:
- `windowId` (number): The ID of the window to activate.

**Returns:**
- `Promise<BoolResult>`: A promise that resolves to a result object containing the success status and request ID.


### minimizeWindow

```typescript
async minimizeWindow(windowId: number): Promise<BoolResult>
```

**Parameters:
- `windowId` (number): The ID of the window to minimize.

**Returns:**
- `Promise<BoolResult>`: A promise that resolves to a result object containing the success status and request ID.


### maximizeWindow

```typescript
async maximizeWindow(windowId: number): Promise<BoolResult>
```

**Parameters:
- `windowId` (number): The ID of the window to maximize.

**Returns:**
- `Promise<BoolResult>`: A promise that resolves to a result object containing the success status and request ID.


```typescript
async restoreWindow(windowId: number): Promise<BoolResult>
```

**Parameters:**
- `windowId` (number): The ID of the window to restore.

**Returns:**
- `Promise<BoolResult>`: A promise that resolves to a result object containing the success status and request ID.


```typescript
async fullscreenWindow(windowId: number): Promise<BoolResult>
```

**Parameters:**
- `windowId` (number): The ID of the window to make fullscreen.

**Returns:**
- `Promise<BoolResult>`: A promise that resolves to a result object containing the success status and request ID.


```typescript
async resizeWindow(windowId: number, width: number, height: number): Promise<BoolResult>
```

**Parameters:**
- `windowId` (number): The ID of the window to resize.
- `width` (number): The new width of the window.
- `height` (number): The new height of the window.

**Returns:**
- `Promise<BoolResult>`: A promise that resolves to a result object containing the success status and request ID.


```typescript
async closeWindow(windowId: number): Promise<BoolResult>
```

**Parameters:**
- `windowId` (number): The ID of the window to close.

**Returns:**
- `Promise<BoolResult>`: A promise that resolves to a result object containing the success status and request ID.


```typescript
async focusMode(on: boolean): Promise<BoolResult>
```

**Parameters:**
- `on` (boolean): True to enable focus mode, False to disable it.

**Returns:**
- `Promise<BoolResult>`: A promise that resolves to a result object containing the success status and request ID.
