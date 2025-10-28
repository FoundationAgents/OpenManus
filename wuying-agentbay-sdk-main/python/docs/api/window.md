# Window Class

> **⚠️ DEPRECATED**: This API is deprecated. Please use the [Computer API](computer.md) instead for window management functionality.

The Window class provides methods for managing windows in the AgentBay cloud environment, including listing windows, getting the active window, and manipulating window states.

## Class Properties

Represents a window in the system.

```python
class Window:
    window_id: int            # The unique identifier of the window
    title: str                # The title of the window
    absolute_upper_left_x: int # The X coordinate of the upper left corner (optional)
    absolute_upper_left_y: int # The Y coordinate of the upper left corner (optional)
    width: int                # The width of the window (optional)
    height: int               # The height of the window (optional)
    pid: int                  # The process ID of the process that owns the window (optional)
    pname: str                # The name of the process that owns the window (optional)
    child_windows: List[Window] # The child windows of this window (optional)
```

## Data Types


Represents a window in the system.


```python
class Window:
    window_id: int            # The unique identifier of the window
    title: str                # The title of the window
    absolute_upper_left_x: int # The X coordinate of the upper left corner (optional)
    absolute_upper_left_y: int # The Y coordinate of the upper left corner (optional)
    width: int                # The width of the window (optional)
    height: int               # The height of the window (optional)
    pid: int                  # The process ID of the process that owns the window (optional)
    pname: str                # The name of the process that owns the window (optional)
    child_windows: List[Window] # The child windows of this window (optional)
```


```python
def list_root_windows(self) -> WindowListResult:
```

**Returns:**
- `WindowListResult`: Result object containing list of windows and error message if any.

**Note:**
- Check the `success` attribute of the result to determine if the operation was successful.
- Access the list of windows through the `windows` attribute of the result.


```python
def get_active_window(self) -> WindowInfoResult:
```

**Returns:**
- `WindowInfoResult`: Result object containing window information and error message if any.

**Note:**
- Check the `success` attribute of the result to determine if the operation was successful.
- Access the window object through the `window` attribute of the result.


```python
def activate_window(self, window_id: int) -> BoolResult:
```

**Parameters:**
- `window_id` (int): The ID of the window to activate.

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Note:**
- Check the `success` attribute of the result to determine if the operation was successful.


```python
def minimize_window(self, window_id: int) -> BoolResult:
```

**Parameters:**
- `window_id` (int): The ID of the window to minimize.

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Note:**
- Check the `success` attribute of the result to determine if the operation was successful.


```python
def maximize_window(self, window_id: int) -> BoolResult:
```

**Parameters:**
- `window_id` (int): The ID of the window to maximize.

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Note:**
- Check the `success` attribute of the result to determine if the operation was successful.


```python
def restore_window(self, window_id: int) -> BoolResult:
```

**Parameters:**
- `window_id` (int): The ID of the window to restore.

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Note:**
- Check the `success` attribute of the result to determine if the operation was successful.


```python
def fullscreen_window(self, window_id: int) -> BoolResult:
```

**Parameters:**
- `window_id` (int): The ID of the window to make fullscreen.

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Note:**
- Check the `success` attribute of the result to determine if the operation was successful.


```python
def resize_window(self, window_id: int, width: int, height: int) -> BoolResult:
```

**Parameters:**
- `window_id` (int): The ID of the window to resize.
- `width` (int): The new width of the window.
- `height` (int): The new height of the window.

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Note:**
- Check the `success` attribute of the result to determine if the operation was successful.


```python
def close_window(self, window_id: int) -> BoolResult:
```

**Parameters:**
- `window_id` (int): The ID of the window to close.

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Note:**
- Check the `success` attribute of the result to determine if the operation was successful.


```python
def focus_mode(self, on: bool) -> BoolResult:
```

**Parameters:**
- `on` (bool): True to enable focus mode, False to disable it.

**Returns:**
- `BoolResult`: Result object containing success status and error message if any.

**Note:**
- Check the `success` attribute of the result to determine if the operation was successful.
