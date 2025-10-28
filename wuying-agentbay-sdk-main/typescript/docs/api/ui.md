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


```typescript
getClickableUIElements(timeoutMs?: number): Promise<UIElementListResult>
```

**Parameters:**
- `timeoutMs` (number, optional): The timeout in milliseconds. Default is 2000ms.

**Returns:**
- `Promise<UIElementListResult>`: A promise that resolves to a result object containing clickable UI elements, success status, and request ID.

**Throws:**
- `APIError`: If the operation fails.


```typescript
getAllUIElements(timeoutMs?: number): Promise<UIElementListResult>
```

**Parameters:**
- `timeoutMs` (number, optional): The timeout in milliseconds. Default is 2000ms.

**Returns:**
- `Promise<UIElementListResult>`: A promise that resolves to a result object containing all UI elements, success status, and request ID.

**Throws:**
- `APIError`: If the operation fails.


```typescript
sendKey(key: number): Promise<BoolResult>
```

**Parameters:**
- `key` (number): The key code to send. Use the `KeyCode` constants.

**Returns:**
- `Promise<BoolResult>`: A promise that resolves to a result object containing success status and request ID.

**Throws:**
- `APIError`: If the operation fails.


```typescript
inputText(text: string): Promise<BoolResult>
```

**Parameters:**
- `text` (string): The text to input.

**Returns:**
- `Promise<BoolResult>`: A promise that resolves to a result object containing success status and request ID.

**Throws:**
- `APIError`: If the operation fails.


```typescript
swipe(startX: number, startY: number, endX: number, endY: number, durationMs?: number): Promise<BoolResult>
```

**Parameters:**
- `startX` (number): The starting X coordinate.
- `startY` (number): The starting Y coordinate.
- `endX` (number): The ending X coordinate.
- `endY` (number): The ending Y coordinate.
- `durationMs` (number, optional): The duration of the swipe in milliseconds. Default is 300ms.

**Returns:**
- `Promise<BoolResult>`: A promise that resolves to a result object containing success status and request ID.

**Throws:**
- `APIError`: If the operation fails.


```typescript
click(x: number, y: number, button?: string): Promise<BoolResult>
```

**Parameters:**
- `x` (number): The X coordinate.
- `y` (number): The Y coordinate.
- `button` (string, optional): The mouse button to use. Default is 'left'.

**Returns:**
- `Promise<BoolResult>`: A promise that resolves to a result object containing success status and request ID.

**Throws:**
- `APIError`: If the operation fails.


```typescript
screenshot(): Promise<OperationResult>
```

**Returns:**
- `Promise<OperationResult>`: A promise that resolves to a result object containing screenshot data, success status, and request ID.

**Throws:**
- `APIError`: If the operation fails.
