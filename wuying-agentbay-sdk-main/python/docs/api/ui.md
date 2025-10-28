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


```python
get_clickable_ui_elements(timeout_ms: int = 2000) -> List[Dict[str, Any]]
```

**Parameters:**
- `timeout_ms` (int, optional): The timeout in milliseconds. Default is 2000ms.

**Returns:**
- `List[Dict[str, Any]]`: A list of clickable UI elements.

**Raises:**
- `AgentBayError`: If the operation fails.


```python
get_all_ui_elements(timeout_ms: int = 2000) -> List[Dict[str, Any]]
```

**Parameters:**
- `timeout_ms` (int, optional): The timeout in milliseconds. Default is 2000ms.

**Returns:**
- `List[Dict[str, Any]]`: A list of all UI elements with parsed details.

**Raises:**
- `AgentBayError`: If the operation fails.


```python
send_key(key: int) -> bool
```

**Parameters:**
- `key` (int): The key code to send. Use the `KeyCode` constants.

**Returns:**
- `bool`: True if the key press was successful.

**Raises:**
- `AgentBayError`: If the operation fails.


```python
input_text(text: str) -> None
```

**Parameters:**
- `text` (string): The text to input.

**Raises:**
- `AgentBayError`: If the operation fails.


```python
swipe(start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> None
```

**Parameters:**
- `start_x` (int): The starting X coordinate.
- `start_y` (int): The starting Y coordinate.
- `end_x` (int): The ending X coordinate.
- `end_y` (int): The ending Y coordinate.
- `duration_ms` (int, optional): The duration of the swipe in milliseconds. Default is 300ms.

**Raises:**
- `AgentBayError`: If the operation fails.


```python
click(x: int, y: int, button: str = "left") -> None
```

**Parameters:**
- `x` (int): The X coordinate.
- `y` (int): The Y coordinate.
- `button` (str, optional): The mouse button to use. Default is 'left'.

**Raises:**
- `AgentBayError`: If the operation fails.


```python
screenshot() -> str
```

**Returns:**
- `str`: The screenshot data.

**Raises:**
- `AgentBayError`: If the operation fails.
