# Mobile Class

The `Mobile` class provides mobile UI automation capabilities including touch operations, text input, app management, and UI element inspection for mobile environments.

## 📖 Related Tutorials

- [Mobile UI Automation Guide](../../../docs/guides/mobile-use/mobile-ui-automation.md) - Detailed tutorial on mobile UI automation
- [Mobile Application Management Guide](../../../docs/guides/mobile-use/mobile-application-management.md) - Tutorial on managing mobile applications

## Overview

The Mobile module is designed for mobile device automation tasks and requires sessions created with the `mobile_latest` image. It provides comprehensive mobile interaction capabilities through MCP tools.

## Properties

The Mobile class is accessible through the session object:

```typescript
session.mobile: Mobile  // Mobile automation instance
```

## Touch Operations

### tap()

Tap at specified coordinates on the mobile screen.

```typescript
async tap(x: number, y: number): Promise<BoolResult>
```

**Parameters:**
- `x` (number): X coordinate for the tap
- `y` (number): Y coordinate for the tap

**Returns:**
- `Promise<BoolResult>`: Result with success status and request ID

**Example:**
```typescript
// Verified: ✓ Works successfully
const result = await session.mobile.tap(100, 100);
if (result.success) {
    console.log('Tap executed successfully');
} else {
    console.log(`Tap failed: ${result.errorMessage}`);
}
```

### swipe()

Swipe from one position to another on the mobile screen.

```typescript
async swipe(startX: number, startY: number, endX: number, endY: number, durationMs?: number): Promise<BoolResult>
```

**Parameters:**
- `startX` (number): Starting X coordinate
- `startY` (number): Starting Y coordinate
- `endX` (number): Ending X coordinate
- `endY` (number): Ending Y coordinate
- `durationMs` (number, optional): Swipe duration in milliseconds. Default is 300

**Returns:**
- `Promise<BoolResult>`: Result with success status and request ID

**Example:**
```typescript
// Verified: ✓ Works successfully - swipe up gesture
const result = await session.mobile.swipe(200, 400, 200, 100, 300);
if (result.success) {
    console.log('Swipe gesture completed successfully');
}
```

## Text Input Operations

### inputText()

Input text at the current focus position.

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
const result = await session.mobile.inputText('Hello Mobile');
if (result.success) {
    console.log('Text input successfully');
}
```

### sendKey()

Send Android key code to the device.

```typescript
async sendKey(key: number): Promise<BoolResult>
```

**Parameters:**
- `key` (number): Android key code to send

**Common Android Key Codes:**
- `4`: KEYCODE_BACK - Back button
- `3`: KEYCODE_HOME - Home button  
- `82`: KEYCODE_MENU - Menu button
- `84`: KEYCODE_SEARCH - Search button
- `66`: KEYCODE_ENTER - Enter key

**Returns:**
- `Promise<BoolResult>`: Result with success status and request ID

**Example:**
```typescript
// Verified: ✗ Timeout occurred - may need longer session warmup
const result = await session.mobile.sendKey(4); // Back button
if (result.success) {
    console.log('Key sent successfully');
} else {
    console.log(`Send key failed: ${result.errorMessage}`);
    // Error seen: "mqtt message response timeout"
}
```

## UI Element Inspection

### getClickableUIElements()

Get all clickable UI elements on the current screen.

```typescript
async getClickableUIElements(timeoutMs?: number): Promise<UIElementsResult>
```

**Parameters:**
- `timeoutMs` (number, optional): Timeout in milliseconds. Default is 5000

**Returns:**
- `Promise<UIElementsResult>`: Result containing array of clickable UI elements

**UIElement Interface:**
```typescript
interface UIElement {
  text: string;        // Element text content
  className: string;   // Element class name
  bounds: {           // Element bounding rectangle
    left: number;
    top: number;
    right: number;
    bottom: number;
  };
}
```

**Example:**
```typescript
// Verified: ✗ Returns "No content in response" - needs investigation
const result = await session.mobile.getClickableUIElements(5000);
if (result.success) {
    console.log(`Found ${result.elements.length} clickable elements`);
    result.elements.forEach(element => {
        console.log(`Element: ${element.text} at (${element.bounds.left}, ${element.bounds.top})`);
    });
} else {
    console.log(`Failed to get clickable elements: ${result.errorMessage}`);
}
```

### getAllUIElements()

Get all UI elements on the current screen.

```typescript
async getAllUIElements(timeoutMs?: number): Promise<UIElementsResult>
```

**Parameters:**
- `timeoutMs` (number, optional): Timeout in milliseconds. Default is 3000

**Returns:**
- `Promise<UIElementsResult>`: Result containing array of all UI elements

**Example:**
```typescript
// Verified: ✗ Returns "No content in response" - needs investigation
const result = await session.mobile.getAllUIElements(3000);
if (result.success) {
    console.log(`Found ${result.elements.length} UI elements`);
} else {
    console.log(`Failed to get UI elements: ${result.errorMessage}`);
}
```

## App Management

### getInstalledApps()

Get list of installed applications on the device.

```typescript
async getInstalledApps(startMenu?: boolean, desktop?: boolean, ignoreSystemApps?: boolean): Promise<InstalledAppsResult>
```

**Parameters:**
- `startMenu` (boolean, optional): Include apps from start menu. Default is false
- `desktop` (boolean, optional): Include apps from desktop. Default is true
- `ignoreSystemApps` (boolean, optional): Exclude system apps. Default is true

**Returns:**
- `Promise<InstalledAppsResult>`: Result containing array of installed applications

**InstalledApp Interface:**
```typescript
interface InstalledApp {
  name: string;          // Application name
  startCmd: string;      // Command to start the app
  workDirectory: string; // Working directory
}
```

**Example:**
```typescript
// Verified: ✗ Returns "No content in response" - needs investigation
const result = await session.mobile.getInstalledApps();
if (result.success) {
    console.log(`Found ${result.apps.length} installed apps`);
    result.apps.forEach(app => {
        console.log(`App: ${app.name} - ${app.startCmd}`);
    });
} else {
    console.log(`Failed to get apps: ${result.errorMessage}`);
}
```

### startApp()

Start an application by its start command.

```typescript
async startApp(startCmd: string, workDirectory?: string, activity?: string): Promise<ProcessResult>
```

**Parameters:**
- `startCmd` (string): Command to start the application
- `workDirectory` (string, optional): Working directory for the app. Default is empty
- `activity` (string, optional): Specific activity to start. Default is empty

**Returns:**
- `Promise<ProcessResult>`: Result containing information about started processes

**Process Interface:**
```typescript
interface Process {
  pid: number;    // Process ID
  pname: string;  // Process name
}
```

**Example:**
```typescript
// Start a specific app
const result = await session.mobile.startApp('com.example.app/.MainActivity');
if (result.success) {
    console.log('App started successfully');
    result.processes.forEach(process => {
        console.log(`Process: ${process.pname} (PID: ${process.pid})`);
    });
}
```

### stopAppByPName()

Stop an application by its process name.

```typescript
async stopAppByPName(pname: string): Promise<BoolResult>
```

**Parameters:**
- `pname` (string): Process name of the application to stop

**Returns:**
- `Promise<BoolResult>`: Result with success status and request ID

**Example:**
```typescript
const result = await session.mobile.stopAppByPName('com.example.app');
if (result.success) {
    console.log('App stopped successfully');
}
```

## Screen Operations

### screenshot()

Take a screenshot of the current mobile screen.

```typescript
async screenshot(): Promise<ScreenshotResult>
```

**Returns:**
- `Promise<ScreenshotResult>`: Result containing screenshot URL

**ScreenshotResult Interface:**
```typescript
interface ScreenshotResult extends OperationResult {
  data: string; // Screenshot URL
}
```

**Example:**
```typescript
// Verified: ✓ Works successfully
const result = await session.mobile.screenshot();
if (result.success) {
    console.log('Screenshot taken successfully');
    // result.data contains the screenshot URL
    console.log(`Screenshot URL available: ${result.data ? 'Yes' : 'No'}`);
}
```

## Type Definitions

### BoolResult Interface

```typescript
interface BoolResult extends OperationResult {
  data?: boolean; // Operation result data
}
```

### UIElementsResult Interface

```typescript
interface UIElementsResult extends OperationResult {
  elements: UIElement[]; // Array of UI elements
}
```

### InstalledAppsResult Interface

```typescript
interface InstalledAppsResult extends OperationResult {
  apps: InstalledApp[]; // Array of installed applications
}
```

### ProcessResult Interface

```typescript
interface ProcessResult extends OperationResult {
  processes: Process[]; // Array of processes
}
```

## Complete Example

```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

async function mobileAutomationExample() {
  const agentBay = new AgentBay();
  
  // Create session with mobile image for mobile use
  const sessionResult = await agentBay.create({ imageId: 'mobile_latest' });
  if (!sessionResult.success) {
    throw new Error(`Failed to create session: ${sessionResult.errorMessage}`);
  }
  
  const session = sessionResult.session;
  
  try {
    // Wait for mobile environment to be ready
    console.log('Waiting for mobile session to be ready...');
    await new Promise(resolve => setTimeout(resolve, 10000));
    
    // Take initial screenshot
    // Verified: ✓ Works successfully
    const screenshot = await session.mobile.screenshot();
    console.log('Screenshot taken:', screenshot.success);
    
    // Perform basic touch operations
    // Verified: ✓ Both operations work successfully
    await session.mobile.tap(150, 200);
    await session.mobile.swipe(200, 400, 200, 100, 300); // Swipe up
    
    // Input some text
    // Verified: ✓ Works successfully
    await session.mobile.inputText('Hello from Mobile API!');
    
    // Try to get installed apps (may need session warmup)
    const apps = await session.mobile.getInstalledApps();
    if (apps.success) {
      console.log(`Found ${apps.apps.length} installed apps`);
    } else {
      console.log('Could not retrieve apps - may need longer warmup time');
    }
    
    // Navigate back (may timeout - needs investigation)
    const backResult = await session.mobile.sendKey(4); // Back key
    if (!backResult.success) {
      console.log('Back key timeout - this is a known issue');
    }
    
  } finally {
    // Clean up
    await agentBay.delete(session);
  }
}
```

## Important Notes

1. **Image Requirement**: Mobile automation requires sessions created with `imageId: 'mobile_latest'`

2. **Session Warmup**: Mobile sessions may need extra time (10+ seconds) to fully initialize before all APIs work properly.

3. **Coordinate System**: All coordinates are in device pixels with (0,0) at top-left corner.

4. **Known Issues**:
   - UI element retrieval (`getClickableUIElements()`, `getAllUIElements()`) returns "No content in response" - needs investigation
   - App management (`getInstalledApps()`) may return "No content in response" - may need longer session warmup
   - Key sending (`sendKey()`) may timeout with "mqtt message response timeout" - needs investigation

5. **Working Features**: 
   - ✓ Screenshot capture works reliably
   - ✓ Touch operations (tap, swipe) work successfully  
   - ✓ Text input works successfully

6. **Timeout Handling**: Mobile operations may take longer than desktop operations. Consider using longer timeouts for complex operations.

7. **Error Handling**: Always check the `success` property of results and handle `errorMessage` appropriately. Some operations may fail during session initialization period.

## Android Key Codes Reference

Common Android key codes for use with `sendKey()`:

| Key Code | Constant Name | Description |
|----------|---------------|-------------|
| 3 | KEYCODE_HOME | Home button |
| 4 | KEYCODE_BACK | Back button |
| 19 | KEYCODE_DPAD_UP | Directional pad up |
| 20 | KEYCODE_DPAD_DOWN | Directional pad down |
| 21 | KEYCODE_DPAD_LEFT | Directional pad left |
| 22 | KEYCODE_DPAD_RIGHT | Directional pad right |
| 23 | KEYCODE_DPAD_CENTER | Directional pad center |
| 66 | KEYCODE_ENTER | Enter key |
| 82 | KEYCODE_MENU | Menu button |
| 84 | KEYCODE_SEARCH | Search button |