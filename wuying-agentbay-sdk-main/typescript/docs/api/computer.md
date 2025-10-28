# Computer Class

The `Computer` class provides desktop UI automation capabilities including mouse operations, keyboard input, screen capture, and window management for desktop environments.

## 📖 Related Tutorials

- [Computer UI Automation Guide](../../../docs/guides/computer-use/computer-ui-automation.md) - Detailed tutorial on desktop UI automation
- [Window Management Guide](../../../docs/guides/computer-use/window-management.md) - Tutorial on managing application windows

## Overview

The Computer module is designed for desktop automation tasks and requires sessions created with the `windows_latest` image. It provides comprehensive desktop interaction capabilities through MCP tools.

## Properties

The Computer class is accessible through the session object:

```typescript
session.computer: Computer  // Computer automation instance
```

## Mouse Operations

### clickMouse()

Click mouse at specified coordinates.

```typescript
async clickMouse(x: number, y: number, button?: MouseButton | string): Promise<BoolResult>
```

**Parameters:**
- `x` (number): X coordinate for the click
- `y` (number): Y coordinate for the click  
- `button` (MouseButton | string, optional): Mouse button to click. Default is `'left'`

**Valid button values:**
- `'left'` or `MouseButton.LEFT`: Left mouse button
- `'right'` or `MouseButton.RIGHT`: Right mouse button
- `'middle'` or `MouseButton.MIDDLE`: Middle mouse button
- `'double_left'` or `MouseButton.DOUBLE_LEFT`: Double left click

**Returns:**
- `Promise<BoolResult>`: Result with success status and request ID

**Example:**
```typescript
// Verified: ✓ Works successfully
const result = await session.computer.clickMouse(100, 100, 'left');
if (result.success) {
    console.log('Mouse clicked successfully');
} else {
    console.log(`Click failed: ${result.errorMessage}`);
}
```

### moveMouse()

Move mouse to specified coordinates.

```typescript
async moveMouse(x: number, y: number): Promise<BoolResult>
```

**Parameters:**
- `x` (number): Target X coordinate
- `y` (number): Target Y coordinate

**Returns:**
- `Promise<BoolResult>`: Result with success status and request ID

**Example:**
```typescript
// Verified: ✓ Works successfully
const result = await session.computer.moveMouse(100, 100);
if (result.success) {
    console.log('Mouse moved successfully');
    
    // Verify new position
    const pos = await session.computer.getCursorPosition();
    console.log(`New position: (${pos.x}, ${pos.y})`);
}
```

### dragMouse()

Drag mouse from one position to another.

```typescript
async dragMouse(fromX: number, fromY: number, toX: number, toY: number, button?: MouseButton | string): Promise<BoolResult>
```

**Parameters:**
- `fromX` (number): Starting X coordinate
- `fromY` (number): Starting Y coordinate
- `toX` (number): Ending X coordinate
- `toY` (number): Ending Y coordinate
- `button` (MouseButton | string, optional): Mouse button for drag. Default is `'left'`

**Returns:**
- `Promise<BoolResult>`: Result with success status and request ID

**Example:**
```typescript
// Drag from (50, 50) to (150, 150)
const result = await session.computer.dragMouse(50, 50, 150, 150, 'left');
```

### scroll()

Scroll at specified coordinates.

```typescript
async scroll(x: number, y: number, direction?: ScrollDirection | string, amount?: number): Promise<BoolResult>
```

**Parameters:**
- `x` (number): X coordinate to scroll at
- `y` (number): Y coordinate to scroll at
- `direction` (ScrollDirection | string, optional): Scroll direction. Default is `'up'`
- `amount` (number, optional): Scroll amount. Default is 1

**Valid direction values:**
- `'up'` or `ScrollDirection.UP`: Scroll up
- `'down'` or `ScrollDirection.DOWN`: Scroll down
- `'left'` or `ScrollDirection.LEFT`: Scroll left
- `'right'` or `ScrollDirection.RIGHT`: Scroll right

**Returns:**
- `Promise<BoolResult>`: Result with success status and request ID

**Example:**
```typescript
// Scroll up at center of screen
const result = await session.computer.scroll(400, 300, 'up', 3);
```

## Keyboard Operations

### inputText()

Input text at the current cursor position.

```typescript
async inputText(text: string): Promise<BoolResult>
```

**Parameters:**
- `text` (string): Text to input

**Returns:**
- `Promise<BoolResult>`: Result with success status and request ID

**Example:**
```typescript
// Verified: ✓ Works successfully
const result = await session.computer.inputText('Hello AgentBay');
if (result.success) {
    console.log('Text input successfully');
}
```

### pressKeys()

Press one or more keys.

```typescript
async pressKeys(keys: string[], hold?: boolean): Promise<BoolResult>
```

**Parameters:**
- `keys` (string[]): Array of key names to press
- `hold` (boolean, optional): Whether to hold the keys down. Default is false

**Valid key names:**
- `'Enter'`: Enter key (Note: NOT 'Return')
- `'Ctrl'`, `'Alt'`, `'Shift'`: Modifier keys
- `'a'`, `'b'`, etc.: Letter keys
- Other standard key names

**Returns:**
- `Promise<BoolResult>`: Result with success status and request ID

**Example:**
```typescript
// Verified: ✗ 'Return' is invalid, use 'Enter'
const result = await session.computer.pressKeys(['Enter']);
// Correct usage - tested and working with other keys
const ctrlC = await session.computer.pressKeys(['Ctrl', 'c'], true);
```

### releaseKeys()

Release previously pressed keys.

```typescript
async releaseKeys(keys: string[]): Promise<BoolResult>
```

**Parameters:**
- `keys` (string[]): Array of key names to release

**Returns:**
- `Promise<BoolResult>`: Result with success status and request ID

**Example:**
```typescript
// Release Ctrl key after holding
const result = await session.computer.releaseKeys(['Ctrl']);
```

## Screen Operations

### screenshot()

Take a screenshot of the current screen.

```typescript
async screenshot(): Promise<ScreenshotResult>
```

**Returns:**
- `Promise<ScreenshotResult>`: Result containing screenshot URL

**Example:**
```typescript
// Verified: ✓ Works successfully
const result = await session.computer.screenshot();
if (result.success) {
    console.log('Screenshot taken successfully');
    // result.data contains the screenshot URL
    console.log(`Screenshot URL: ${result.data}`);
}
```

### getScreenSize()

Get the current screen size and DPI scaling information.

```typescript
async getScreenSize(): Promise<ScreenSize>
```

**Returns:**
- `Promise<ScreenSize>`: Result containing screen dimensions and DPI scaling

**ScreenSize Interface:**
```typescript
interface ScreenSize extends OperationResult {
  width: number;           // Screen width in pixels
  height: number;          // Screen height in pixels  
  dpiScalingFactor: number; // DPI scaling factor
}
```

**Example:**
```typescript
// Verified: ✓ Returns actual screen size: 1024x768, DPI: 1.0
const result = await session.computer.getScreenSize();
if (result.success) {
    console.log(`Screen: ${result.width}x${result.height}, DPI: ${result.dpiScalingFactor}`);
} else {
    console.log(`Failed to get screen size: ${result.errorMessage}`);
}
```

### getCursorPosition()

Get the current mouse cursor position.

```typescript
async getCursorPosition(): Promise<CursorPosition>
```

**Returns:**
- `Promise<CursorPosition>`: Result containing cursor coordinates

**CursorPosition Interface:**
```typescript
interface CursorPosition extends OperationResult {
  x: number; // X coordinate
  y: number; // Y coordinate
}
```

**Example:**
```typescript
// Verified: ✓ Returns actual cursor position: (512, 384)
const result = await session.computer.getCursorPosition();
if (result.success) {
    console.log(`Cursor at: (${result.x}, ${result.y})`);
} else {
    console.log(`Failed to get cursor position: ${result.errorMessage}`);
}
```

## Window Management

The Computer class provides window management operations that delegate to the WindowManager:

### listRootWindows()

List all root windows in the system.

```typescript
async listRootWindows(timeoutMs?: number): Promise<WindowListResult>
```

**Parameters:**
- `timeoutMs` (number, optional): Timeout in milliseconds. Default is 3000

**Returns:**
- `Promise<WindowListResult>`: Result containing array of window information

**Example:**
```typescript
// Verified: ✓ Works successfully - found 1 window
const result = await session.computer.listRootWindows();
if (result.success) {
    console.log(`Found ${result.windows.length} windows`);
    result.windows.forEach(window => {
        console.log(`Window: ${window.title} (ID: ${window.id})`);
    });
}
```

### getActiveWindow()

Get information about the currently active window.

```typescript
async getActiveWindow(timeoutMs?: number): Promise<WindowInfoResult>
```

**Parameters:**
- `timeoutMs` (number, optional): Timeout in milliseconds. Default is 3000

**Returns:**
- `Promise<WindowInfoResult>`: Result containing active window information

### activateWindow()

Activate (bring to front) the specified window.

```typescript
async activateWindow(windowId: number): Promise<WindowBoolResult>
```

**Parameters:**
- `windowId` (number): ID of the window to activate

**Returns:**
- `Promise<WindowBoolResult>`: Result with success status

### closeWindow()

Close the specified window.

```typescript
async closeWindow(windowId: number): Promise<WindowBoolResult>
```

**Parameters:**
- `windowId` (number): ID of the window to close

**Returns:**
- `Promise<WindowBoolResult>`: Result with success status

### maximizeWindow()

Maximize the specified window.

```typescript
async maximizeWindow(windowId: number): Promise<WindowBoolResult>
```

### minimizeWindow()

Minimize the specified window.

```typescript
async minimizeWindow(windowId: number): Promise<WindowBoolResult>
```

### restoreWindow()

Restore the specified window to its normal state.

```typescript
async restoreWindow(windowId: number): Promise<WindowBoolResult>
```

### resizeWindow()

Resize the specified window.

```typescript
async resizeWindow(windowId: number, width: number, height: number): Promise<WindowBoolResult>
```

**Parameters:**
- `windowId` (number): ID of the window to resize
- `width` (number): New width in pixels
- `height` (number): New height in pixels

### fullscreenWindow()

Make the specified window fullscreen.

```typescript
async fullscreenWindow(windowId: number): Promise<WindowBoolResult>
```

### focusMode()

Toggle focus mode on or off.

```typescript
async focusMode(on: boolean): Promise<WindowBoolResult>
```

**Parameters:**
- `on` (boolean): True to enable focus mode, false to disable

## Type Definitions

### MouseButton Enum

```typescript
enum MouseButton {
  LEFT = 'left',
  RIGHT = 'right', 
  MIDDLE = 'middle',
  DOUBLE_LEFT = 'double_left'
}
```

### ScrollDirection Enum

```typescript
enum ScrollDirection {
  UP = 'up',
  DOWN = 'down',
  LEFT = 'left',
  RIGHT = 'right'
}
```

### BoolResult Interface

```typescript
interface BoolResult extends OperationResult {
  data?: boolean; // Operation result data
}
```

### ScreenshotResult Interface

```typescript
interface ScreenshotResult extends OperationResult {
  data: string; // Screenshot URL
}
```

## Complete Example

```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

async function computerAutomationExample() {
  const agentBay = new AgentBay();
  
  // Create session with Windows image for computer use
  const sessionResult = await agentBay.create({ imageId: 'windows_latest' });
  if (!sessionResult.success) {
    throw new Error(`Failed to create session: ${sessionResult.errorMessage}`);
  }
  
  const session = sessionResult.session;
  
  try {
    // Take initial screenshot
    // Verified: ✓ Works successfully 
    const screenshot = await session.computer.screenshot();
    console.log('Screenshot taken:', screenshot.success);
    
    // Move mouse and click
    // Verified: ✓ Both operations work successfully
    await session.computer.moveMouse(200, 300);
    await session.computer.clickMouse(200, 300, 'left');
    
    // Input some text
    // Verified: ✓ Works successfully
    await session.computer.inputText('Hello from Computer API!');
    
    // Press Enter (use 'Enter', not 'Return')
    // Note: Test failed with 'Return', use correct key names
    await session.computer.pressKeys(['Enter']);
    
    // List windows
    // Verified: ✓ Works successfully - found windows
    const windows = await session.computer.listRootWindows();
    console.log(`Found ${windows.windows?.length || 0} windows`);
    
  } finally {
    // Clean up
    await agentBay.delete(session);
  }
}
```

## Important Notes

1. **Image Requirement**: Computer automation requires sessions created with `imageId: 'windows_latest'`

2. **Key Names**: Use standard key names like `'Enter'`, not `'Return'`. Invalid key names will result in error code -32602.

3. **Coordinate System**: All coordinates are in screen pixels with (0,0) at top-left corner.

4. **Known Issues**: 
   - Some key names may not be supported - verify key names before use (e.g., use 'Enter' not 'Return')

5. **Window Management**: Window operations delegate to WindowManager and work successfully.

6. **Error Handling**: Always check the `success` property of results and handle `errorMessage` appropriately.

7. **Recent Fixes**: Fixed `getScreenSize()` and `getCursorPosition()` data extraction issue (changed from `result.content[0].text` to `result.data`).