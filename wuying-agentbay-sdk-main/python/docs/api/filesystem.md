# FileSystem Class API Reference

The `FileSystem` class provides methods for file operations within a session in the AgentBay cloud environment. This includes reading, writing, editing, and searching files, as well as directory operations, real-time directory monitoring, and file transfer capabilities.

## 📖 Related Tutorial

- [Complete Guide to File Operations](../../../docs/guides/common-features/basics/file-operations.md) - Detailed tutorial covering all file operation features

## Methods

### create_directory / createDirectory / CreateDirectory

Creates a new directory at the specified path.


```python
create_directory(path: str) -> BoolResult
```

**Parameters:**
- `path` (str): The path of the directory to create.

**Returns:**
- `BoolResult`: A result object containing success status, boolean data (True if successful), request ID, and error message if any.

**Note:**
The return type has been updated from boolean to a structured `BoolResult` object, which provides more detailed information about the operation result.

### edit_file

Edits a file by replacing occurrences of oldText with newText.


```python
edit_file(path: str, edits: List[Dict[str, str]], dry_run: bool = False) -> BoolResult
```

**Parameters:**
- `path` (str): The path of the file to edit.
- `edits` (List[Dict[str, str]]): List of edit operations, each containing oldText and newText.
- `dry_run` (bool, optional): If true, preview changes without applying them. Default is False.

**Returns:**
- `BoolResult`: A result object containing success status, boolean data (True if successful), request ID, and error message if any.

### get_file_info

Gets information about a file or directory.

```python
get_file_info(path: str) -> FileInfoResult
```

**Parameters:**
- `path` (str): The path of the file or directory to inspect.

**Returns:**
- `FileInfoResult`: A result object containing file information, success status, request ID, and error message if any.

### list_directory

Lists the contents of a directory.

```python
list_directory(path: str) -> DirectoryListResult
```

**Parameters:**
- `path` (str): The path of the directory to list.

**Returns:**
- `DirectoryListResult`: A result object containing a list of directory entries, success status, request ID, and error message if any.

### move_file

Moves a file or directory from source to destination.


```python
move_file(source: str, destination: str) -> BoolResult
```

**Parameters:**
- `source` (str): The path of the source file or directory.
- `destination` (str): The path of the destination file or directory.

**Returns:**
- `BoolResult`: A result object containing success status, boolean data (True if successful), request ID, and error message if any.

### read_file

Reads the contents of a file. Automatically handles large files by chunking.


```python
read_file(path: str) -> FileContentResult
```

**Parameters:**
- `path` (str): The path of the file to read.

**Returns:**
- `FileContentResult`: A result object containing file content, success status, request ID, and error message if any.

**Note:**
This method automatically handles both small and large files. For large files, it uses internal chunking with a default chunk size of 50KB to overcome API size limitations. No manual chunk size configuration is needed.

### read_multiple_files

```python
read_multiple_files(paths: List[str]) -> MultipleFileContentResult
```

**Parameters:**
- `paths` (List[str]): List of file paths to read.

**Returns:**
- `MultipleFileContentResult`: A result object containing a dictionary mapping file paths to their contents, success status, request ID, and error message if any.

### search_files

Searches for files matching a pattern in a directory.


```python
search_files(path: str, pattern: str, exclude_patterns: Optional[List[str]] = None) -> FileSearchResult
```

**Parameters:**
- `path` (str): The path of the directory to start the search.
- `pattern` (str): The pattern to match.
- `exclude_patterns` (List[str], optional): Patterns to exclude. Default is None.

**Returns:**
- `FileSearchResult`: A result object containing search results (in the `matches` attribute), success status, request ID, and error message if any.

### write_file

Writes content to a file. Automatically handles large files by chunking.


```python
write_file(path: str, content: str, mode: str = "overwrite") -> BoolResult
```

**Parameters:**
- `path` (str): The path of the file to write.
- `content` (str): Content to write to the file.
- `mode` (str, optional): "overwrite" (default) or "append".

**Returns:**
- `BoolResult`: A result object containing success status, boolean data (True if successful), request ID, and error message if any.

**Note:**
This method automatically handles both small and large content. For large content, it uses internal chunking with a default chunk size of 50KB to overcome API size limitations. No manual chunk size configuration is needed.

### upload_file

Uploads a file from local storage to the cloud environment.

```python
upload_file(
    local_path: str,
    remote_path: str,
    *,
    content_type: Optional[str] = None,
    wait: bool = True,
    wait_timeout: float = 30.0,
    poll_interval: float = 1.5,
    progress_cb: Optional[Callable[[int], None]] = None
) -> UploadResult
```

**Parameters:**
- `local_path` (str): Path to the local file to upload
- `remote_path` (str): Path where the file should be stored in the cloud
- `content_type` (str, optional): Content-Type header for the upload
- `wait` (bool, optional): Whether to wait for synchronization to complete (default: True)
- `wait_timeout` (float, optional): Maximum time to wait for synchronization (default: 30.0 seconds)
- `poll_interval` (float, optional): Interval between synchronization status checks (default: 1.5 seconds)
- `progress_cb` (Callable, optional): Callback function to track upload progress

**Returns:**
- `UploadResult`: Result object containing upload status and metadata

**Example:**
```python
# Upload a file
upload_result = session.file_system.upload_file(
    local_path="/path/to/local/file.txt",
    remote_path="/remote/path/file.txt"
)

if upload_result.success:
    print(f"Uploaded {upload_result.bytes_sent} bytes")
else:
    print(f"Upload failed: {upload_result.error}")
```

### download_file

Downloads a file from the cloud environment to local storage.

```python
download_file(
    remote_path: str,
    local_path: str,
    *,
    overwrite: bool = True,
    wait: bool = True,
    wait_timeout: float = 300.0,
    poll_interval: float = 1.5,
    progress_cb: Optional[Callable[[int], None]] = None
) -> DownloadResult
```

**Parameters:**
- `remote_path` (str): Path to the file in the cloud environment
- `local_path` (str): Path where the file should be saved locally
- `overwrite` (bool, optional): Whether to overwrite existing local files (default: True)
- `wait` (bool, optional): Whether to wait for synchronization to complete (default: True)
- `wait_timeout` (float, optional): Maximum time to wait for synchronization (default: 300.0 seconds)
- `poll_interval` (float, optional): Interval between synchronization status checks (default: 1.5 seconds)
- `progress_cb` (Callable, optional): Callback function to track download progress

**Returns:**
- `DownloadResult`: Result object containing download status and metadata

**Example:**
```python
# Download a file
download_result = session.file_system.download_file(
    remote_path="/remote/path/file.txt",
    local_path="/path/to/local/file.txt"
)

if download_result.success:
    print(f"Downloaded {download_result.bytes_received} bytes")
else:
    print(f"Download failed: {download_result.error}")
```

## Directory Monitoring

### watch_directory

Watches a directory for file changes and calls a callback function when changes occur.

```python
watch_directory(
    path: str,
    callback: Callable[[List[FileChangeEvent]], None],
    interval: float = 0.5,
    stop_event: Optional[threading.Event] = None
) -> threading.Thread
```

**Parameters:**
- `path` (str): The directory path to monitor for file changes.
- `callback` (Callable): Callback function that will be called with a list of FileChangeEvent objects when changes are detected.
- `interval` (float, optional): Polling interval in seconds. Default is 0.5.
- `stop_event` (threading.Event, optional): Optional threading.Event to stop the monitoring. If not provided, a new Event will be created and attached to the returned thread.

**Returns:**
- `threading.Thread`: The monitoring thread. Call `thread.start()` to begin monitoring. Use `thread.stop_event.set()` to stop monitoring.

**Example:**
```python
import threading
import time

def on_file_change(events):
    for event in events:
        print(f"{event.event_type}: {event.path} ({event.path_type})")

# Start monitoring
monitor_thread = session.file_system.watch_directory(
    path="/tmp/my_directory",
    callback=on_file_change,
    interval=0.5  # Check every 0.5 seconds
)
monitor_thread.start()

# Do some work...
time.sleep(10)

# Stop monitoring
monitor_thread.stop_event.set()
monitor_thread.join()
```

### FileChangeEvent

Represents a single file change event.

**Attributes:**
- `event_type` (str): Type of the file change event ("create", "modify", "delete").
- `path` (str): Path of the file or directory that changed.
- `path_type` (str): Type of the path ("file" or "directory").

**Methods:**
- `to_dict()`: Convert to dictionary representation.
- `from_dict(data)`: Create FileChangeEvent from dictionary (class method).

### FileChangeResult

Result of file change detection operations.

**Attributes:**
- `success` (bool): Whether the operation was successful.
- `events` (List[FileChangeEvent]): List of file change events.
- `raw_data` (str): Raw response data for debugging.
- `error_message` (str): Error message if the operation failed.

**Methods:**
- `has_changes()`: Check if there are any file changes.
- `get_modified_files()`: Get list of modified file paths.
- `get_created_files()`: Get list of created file paths.
- `get_deleted_files()`: Get list of deleted file paths.

## File Transfer Result Classes

### UploadResult

Result structure for file upload operations.

**Properties:**
```python
success: bool                    # Whether the upload was successful
request_id_upload_url: str       # Request ID for the upload URL
request_id_sync: str             # Request ID for the synchronization
http_status: int                 # HTTP status code from the upload
etag: str                        # ETag of the uploaded file
bytes_sent: int                  # Number of bytes sent
path: str                        # Remote path of the file
error: str                       # Error message if upload failed
```

### DownloadResult

Result structure for file download operations.

**Properties:**
```python
success: bool                    # Whether the download was successful
request_id_download_url: str     # Request ID for the download URL
request_id_sync: str             # Request ID for the synchronization
http_status: int                 # HTTP status code from the download
bytes_received: int              # Number of bytes received
path: str                        # Remote path of the file
local_path: str                  # Local path where file was saved
error: str                       # Error message if download failed
```