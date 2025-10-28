# Complete Guide to File Operations

This guide provides a complete introduction to file operations in the AgentBay SDK, including basic file operations, directory management, batch operations, permission management, and performance optimization.

## 📋 Table of Contents

- [Basic Concepts](#basic-concepts)
- [API Quick Reference](#api-quick-reference)
- [Basic File Operations](#basic-file-operations)
- [Directory Management](#directory-management)
- [Batch Operations](#batch-operations)
- [File Editing Operations](#file-editing-operations)  
- [File Permissions and Attributes](#file-permissions-and-attributes)
- [File Transfer Operations](#file-transfer-operations)
- [Error Handling](#error-handling)

<a id="basic-concepts"></a>
## 🎯 Basic Concepts

### File System Structure

AgentBay sessions provide complete file system access, supporting different operating systems. Each system image provides a fully functional environment with standard directory structures:

#### Linux Environment (`linux_latest`)
```
/
├── bin -> usr/bin          # Essential command binaries (symlink)
├── boot/                   # Boot loader files
├── dev/                    # Device files
├── etc/                    # System configuration files
├── home/                   # User home directories
│   └── wuying/            # Default user directory
├── lib -> usr/lib         # Essential libraries (symlink)
├── media/                  # Removable media mount points
├── mnt/                    # Mount points (for context synchronization)
├── opt/                    # Optional application packages
├── proc/                   # Process information filesystem
├── root/                   # Root user home directory
├── run/                    # Runtime variable data
├── snap/                   # Snap packages
├── srv/                    # Service data
├── sys/                    # System information filesystem
├── tmp/                    # Temporary files (recommended for testing)
├── usr/                    # User programs and libraries
└── var/                    # Variable data files

Working Directory: /home/wuying
User: wuying
```

#### Windows Environment (`windows_latest`)
```
C:\
├── LogtailData\           # Logging service data
├── PerfLogs\              # Performance monitoring logs
├── Program Files\         # 64-bit application programs
├── Program Files (x86)\   # 32-bit application programs
├── temp\                  # Temporary files (for AgentBay operations)
├── Users\                 # User profile directories
│   └── Administrator\     # Default administrator account
└── Windows\               # Windows system files

Working Directory: C:\Users\Administrator
User: Administrator
```

#### Mobile/Android Environment (`mobile_latest`)
```
/
├── acct/                  # Process accounting
├── apex/                  # Android package extensions
├── bin -> /system/bin     # Binary executables (symlink)
├── cache/                 # System cache
├── config/                # Configuration files
├── data/                  # Application and user data
├── dev/                   # Device files
├── etc -> /system/etc     # System configuration (symlink)
├── metadata/              # Filesystem metadata
├── mnt/                   # Mount points
├── proc/                  # Process information
├── storage/               # External storage access
├── sys/                   # System information
├── system/                # Core Android system
└── vendor/                # Vendor-specific files

Working Directory: /
User: root
```

### Path Conventions

- **Linux/Android**: Use forward slash `/tmp/file.txt`
- **Windows**: Use backslash `C:\temp\file.txt` or forward slash `C:/temp/file.txt`
- **Recommendation**: Prefer absolute paths to avoid ambiguity

<a id="api-quick-reference"></a>
## 🚀 API Quick Reference

### Python
```python
# Create session
session = agent_bay.create().session
 #Create Directory
session.file_system.create_directory("/path/to")
print("✅ Directory created successfully")


# Write text file (UTF-8 text only)
result = session.file_system.write_file("/path/to/file.txt", "Hello, World!")
if result.success:
    print("Text file written successfully")

# Read text file (UTF-8 text only)
result = session.file_system.read_file("/path/to/file.txt")
if result.success:
    content = result.content  # String content
    print(f"File content: {content}")

# List directory
result = session.file_system.list_directory("/path/to")
if result.success:
    entries = result.entries
    for entry in entries:
        print(f"Name: {entry['name']}")

# Get file info
result = session.file_system.get_file_info("/path/to/file.txt")

if result.success:
    info = result.file_info
    print(f"File info: {info}")
agent_bay.delete(session)
```


<a id="basic-file-operations"></a>
## 📝 Basic File Operations

**⚠️ Important: Text Files Only**: The `read_file()` and `write_file()` methods are designed specifically for **text files** (UTF-8 encoded). They cannot handle binary files such as images, executables, archives, or other non-text formats. For binary file operations, use command-line tools through the `session.command` interface or context synchronization features.

**File Size Support**: Both `read_file()` and `write_file()` methods support text files of any size through automatic chunked transfer. You don't need to worry about file size limitations - the SDK handles large text files transparently.

**Supported File Types**:
- ✅ Text files: `.txt`, `.json`, `.py`, `.html`, etc.
- ❌ Binary files: `.jpg`, `.pdf`, `.exe`, `.zip`, etc.

### Reading Files

```python
from agentbay import AgentBay

agent_bay = AgentBay()
session = agent_bay.create().session

# Read text file
result = session.file_system.read_file("/tmp/sample.txt")
if result.success:
    content = result.content
    print(f"File content: {content}")
else:
    print(f"Failed to read file: {result.error_message}")
    
agent_bay.delete(session)
```


### Writing Files

```python
from agentbay import AgentBay

agent_bay = AgentBay()
session = agent_bay.create().session

# Write plain text file
content = "Hello, AgentBay!\nThis is a multi-line text file."
result = session.file_system.write_file("/tmp/hello.txt", content)
if result.success:
    print("Text file written successfully")
else:
    print(f"Failed to write file: {result.error_message}")

# Append to file
result = session.file_system.write_file("/tmp/hello.txt", "\nNew log entry", mode="append")
if result.success:
    print("File appended successfully")
    
agent_bay.delete(session)
```

### Handling Binary Files

Since `read_file()` and `write_file()` only support text files, **use `upload_file()` and `download_file()` APIs for binary file operations**.

For detailed examples and usage, see [File Transfer Operations](#file-transfer-operations) section.


<a id="directory-management"></a>
## 📁 Directory Management

### Creating and moving Directories

```python
from agentbay import AgentBay

agent_bay = AgentBay()
session = agent_bay.create().session

# Create directory
result = session.file_system.create_directory("/tmp/data/my_project")
if result.success:
    print("Directory created successfully")
else:
    print(f"Failed to create directory: {result.error_message}")

# Remove directory with parent directories
result = session.file_system.move_file("/tmp/data", "/tmp/test/")
if result.success:
    print("Directory moved successfully")
#List direction
result = session.file_system.list_directory("/tmp/")
if result.success:
    entries = result.entries
    for entry in entries:
        print(f"Name: {entry['name']}")
agent_bay.delete(session)
```

### Listing Directory Contents

```python
from agentbay import AgentBay

agent_bay = AgentBay()
session = agent_bay.create().session

# List directory contents
result = session.file_system.list_directory("/tmp")
if result.success:
    entries = result.entries
    for entry in entries:
        print(f"Name: {entry['name']}")
        print(f"Is Directory: {entry['isDirectory']}")
        print("---")
else:
    print(f"Failed to list directory: {result.error_message}")
```

### Directory Monitoring

Monitor directories for file changes in real-time:

```python
import os
import time
import threading
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

# Initialize AgentBay
api_key = os.getenv("AGENTBAY_API_KEY")
agentbay = AgentBay(api_key=api_key)

# Create session
session_params = CreateSessionParams(image_id="linux_latest")
session_result = agentbay.create(session_params)
session = session_result.session

# Define callback function
def on_file_change(events):
    for event in events:
        print(f"{event.event_type}: {event.path} ({event.path_type})")

# Start monitoring
monitor_thread = session.file_system.watch_directory(
    path="/tmp/my_directory",
    callback=on_file_change,
    interval=1.0  # Check every second
)
monitor_thread.start()

# Do your work...
time.sleep(10)

# Stop monitoring
monitor_thread.stop_event.set()
monitor_thread.join()

# Clean up
agentbay.delete(session)
```

#### Event Filtering

```python
def on_file_change(events):
    # Only process file modifications
    for event in events:
        if event.event_type == "modify" and event.path_type == "file":
            print(f"File modified: {event.path}")
        elif event.event_type == "create":
            print(f"File created: {event.path}")
        elif event.event_type == "delete":
            print(f"File deleted: {event.path}")
```

<a id="batch-operations"></a>
## 📦 Batch Operations

### Batch File Operations

```python
from agentbay import AgentBay

agent_bay = AgentBay()
session = agent_bay.create().session

# Batch write files
files_to_write = [
    ("/tmp/file1.txt", "Content of file 1"),
    ("/tmp/file2.txt", "Content of file 2"),
    ("/tmp/file3.txt", "Content of file 3")
]

results = []
for file_path, content in files_to_write:
    result = session.file_system.write_file(file_path, content)
    results.append((file_path, result))

# Check results
for file_path, result in results:
    if result.success:
        print(f"✅ {file_path} written successfully")
    else:
        print(f"❌ {file_path} failed: {result.error_message}")

# Batch read files using read_multiple_files
files_to_read = ["/tmp/file1.txt", "/tmp/file2.txt", "/tmp/file3.txt"]
result = session.file_system.read_multiple_files(files_to_read)

if result.success:
    for file_path, content in result.contents.items():
        print(f"✅ {file_path}: {content[:50]}...")  # First 50 chars
else:
    print(f"❌ Failed to read multiple files: {result.error_message}")
```

### File Search Operations

```python
from agentbay import AgentBay

session = agent_bay.create().session

# Search for files with pattern (partial name matching, NOT wildcards)
result = session.file_system.search_files("/tmp", "systemd")
if result.success:
    print(f"Found {len(result.matches)} files containing 'test':")
    for match in result.matches:
        print(f"  - {match}")
else:
    print(f"Search failed: {result.error_message}")

# Search with exclusion patterns
result = session.file_system.search_files(
    "/tmp",
    "systemd",
    exclude_patterns=["geoclue"]
)
if result.success:
    print(f"Found {len(result.matches)} files containing 'config' (excluding 'backup' and 'temp'):")
    for match in result.matches:
        print(f"  - {match}")
```

#### ⚠️ Important: Search Rules and Limitations

**Pattern Matching Rules:**
- **NOT wildcard-based**: Patterns like `*.txt` or `test*` are NOT supported
- **Partial name matching**: The pattern matches any part of the file/directory name
- **Recursive search**: Searches through all subdirectories from the starting path
- **Case sensitivity**:
  - **Windows**: Case-insensitive matching
  - **Linux/Unix**: Case-sensitive matching

**Examples of Pattern Matching:**

```python
# ✅ CORRECT: Partial name matching
session.file_system.search_files("/tmp", "test")
# Matches: test.txt, my_test_file.py, testing.log, etc.

session.file_system.search_files("/tmp", "config")
# Matches: config.json, app_config.xml, configuration.ini, etc.

# ❌ INCORRECT: Wildcard patterns (NOT supported)
session.file_system.search_files("/tmp", "*.txt")     # Won't work as expected
session.file_system.search_files("/tmp", "test*")     # Won't work as expected
session.file_system.search_files("/tmp", "?.log")     # Won't work as expected
```

**Platform-Specific Behavior:**

```python
# On Windows (case-insensitive)
result = session.file_system.search_files("/tmp", "TEST")
# Matches: TEST.txt, TEST.log, TEST.config, MyTEST.py

# On Linux/Unix (case-sensitive)
result = session.file_system.search_files("/tmp", "TEST")
# Matches only: TEST.config, MyTEST.py (exact case match)
result = session.file_system.search_files("/tmp", "test")
# Matches only: test.txt, my_test.py (exact case match)
```



<a id="file-editing-operations"></a>
## ✏️ File Editing Operations

### Text Find and Replace

```python
from agentbay import AgentBay

agent_bay = AgentBay()
session = agent_bay.create().session

# Create a test file
initial_content = "This is old1 text with old2 content.\nAnother line with old1 data."
result = session.file_system.write_file("/tmp/edit_test.txt", initial_content)

# Edit file with multiple find-replace operations
edits = [
    {"oldText": "old1", "newText": "new1"},
    {"oldText": "old2", "newText": "new2"}
]

result = session.file_system.edit_file("/tmp/edit_test.txt", edits, dry_run=False)
if result.success:
    print("File edited successfully")

    # Verify changes
    read_result = session.file_system.read_file("/tmp/edit_test.txt")
    if read_result.success:
        print(f"Updated content: {read_result.content}")
else:
    print(f"Edit failed: {result.error_message}")
```
### Global Character Replacement
**Note**: Each call to the `edit_file` method will only modify the first matched instance. If you need to globally replace the same string, there are two methods:
```python

from agentbay import AgentBay

agent_bay = AgentBay()
session = agent_bay.create().session

# Create a test file
initial_content = "This is old1 text with old2 content.\nAnother line with old1 data."
result = session.file_system.write_file("/tmp/edit_test.txt", initial_content)

# Method One: Single Call to `edit_file` for Global Replacement
edits = [
    {"oldText": "old1", "newText": "new1"},
    {"oldText": "old1", "newText": "new1"}
]

result = session.file_system.edit_file("/tmp/edit_test.txt", edits, dry_run=False)
if result.success:
    print("File edited successfully")

    # Verify changes
    read_result = session.file_system.read_file("/tmp/edit_test.txt")
    if read_result.success:
        print(f"Updated content: {read_result.content}")
else:
    print(f"Edit failed: {result.error_message}")
# Method Two:Multiple Calls to edit_file for Global Replacement
# Create a test file
result = session.file_system.write_file("/tmp/edit_test.txt", initial_content)

# Edit file with multiple find-replace operations
edits = [
    {"oldText": "old1", "newText": "new1"},
]

result1 = session.file_system.edit_file("/tmp/edit_test.txt", edits, dry_run=False)
result2 = session.file_system.edit_file("/tmp/edit_test.txt", edits, dry_run=False)
if result.success and result2.success:
    print("File edited successfully")

    # Verify changes
    read_result = session.file_system.read_file("/tmp/edit_test.txt")
    if read_result.success:
        print(f"Updated content: {read_result.content}")
else:
    print(f"Edit failed: {result.error_message}")

```

### Dry Run Mode

```python
from agentbay import AgentBay

agent_bay = AgentBay()
session = agent_bay.create().session
    # Create a test file
initial_content = "This is oldText text with newText content.\nAnother line with newText data."
result = session.file_system.write_file("/tmp/test.txt", initial_content)

# Preview changes without applying them
edits = [
    {"oldText": "newText", "newText": "modified"}
]

# Use dry_run=True to preview changes
result = session.file_system.edit_file("/tmp/test.txt", edits, dry_run=True)
if result.success:
    print("Dry run completed - changes would be applied")
    result = session.file_system.read_file("/tmp/test.txt")
    if result.success:
        print(f"Preview content: {result.content}")

    # Apply changes if preview looks good
    actual_result = session.file_system.edit_file("/tmp/test.txt", edits, dry_run=False)
    if actual_result.success:
        print("Changes applied successfully")
        result = session.file_system.read_file("/tmp/test.txt")
        if result.success:
            print(f"updated content: {result.content}")
else:
    print(f"Dry run failed: {result.error_message}")
```

<a id="file-permissions-and-attributes"></a>
## 🔐 File Permissions and Attributes

### Getting File Permissions Info

```python
from agentbay import AgentBay

agent_bay = AgentBay()
session = agent_bay.create().session

# Get file info
result = session.file_system.get_file_info("/tmp/example.txt")
if result.success:
    info = result.file_info
    print(f"Size: {info.get('size', 'N/A')} bytes")
    print(f"Created: {info.get('created', 'N/A')}")
    print(f"Modified: {info.get('modified', 'N/A')}")
    print(f"Is Directory: {info.get('isDirectory', 'N/A')}")
```

<a id="file-transfer-operations"></a>
## 📤📥 File Transfer Operations

AgentBay provides dedicated `upload_file()` and `download_file()` methods for transferring files between your local machine and the cloud environment. These methods support both text and binary files, making them ideal for handling any file type.

### Key Features
- **Universal file support**: Works with both text and binary files
- **Automatic synchronization**: Handles cloud storage synchronization automatically  
- **Progress tracking**: Optional progress callbacks for monitoring large transfers
- **Robust error handling**: Comprehensive error reporting and retry capabilities
- **Flexible timeouts**: Configurable wait times for different use cases

### File Upload

Upload files from your local machine to the cloud environment:

```python
from agentbay import AgentBay

agent_bay = AgentBay()
session = agent_bay.create().session

# Basic file upload
upload_result = session.file_system.upload_file(
    local_path="/path/to/local/file.txt",
    remote_path="/tmp/uploaded_file.txt"
)

if upload_result.success:
    print(f"✅ Upload successful!")
    print(f"   Bytes sent: {upload_result.bytes_sent}")
    print(f"   HTTP status: {upload_result.http_status}")
    print(f"   Remote path: {upload_result.path}")
else:
    print(f"❌ Upload failed: {upload_result.error}")

agent_bay.delete(session)
```

### File Download

Download files from the cloud environment to your local machine:

```python
from agentbay import AgentBay

agent_bay = AgentBay()
session = agent_bay.create().session

# Basic file download
download_result = session.file_system.download_file(
    remote_path="/tmp/cloud_file.txt",
    local_path="/path/to/local/downloaded_file.txt"
)

if download_result.success:
    print(f"✅ Download successful!")
    print(f"   Bytes received: {download_result.bytes_received}")
    print(f"   HTTP status: {download_result.http_status}")
    print(f"   Local path: {download_result.local_path}")
else:
    print(f"❌ Download failed: {download_result.error}")

agent_bay.delete(session)
```

### Binary File Transfer

Unlike `read_file()` and `write_file()`, the transfer methods work seamlessly with binary files:

```python
from agentbay import AgentBay
import os

agent_bay = AgentBay()
session = agent_bay.create().session

# Upload binary files (images, archives, executables, etc.)
binary_files = [
    ("/path/to/image.jpg", "/tmp/uploaded_image.jpg"),
    ("/path/to/data.zip", "/tmp/uploaded_archive.zip")
]

for local_path, remote_path in binary_files:
    if os.path.exists(local_path):
        upload_result = session.file_system.upload_file(
            local_path=local_path,
            remote_path=remote_path
        )
        
        if upload_result.success:
            print(f"✅ {os.path.basename(local_path)}: {upload_result.bytes_sent} bytes")
        else:
            print(f"❌ {os.path.basename(local_path)}: {upload_result.error}")

agent_bay.delete(session)
```

### File Transfer vs. Read/Write Methods

| Feature | `upload_file()` / `download_file()` | `read_file()` / `write_file()` |
|---------|-----------------------------------|------------------------------|
| **File Types** | ✅ Text and Binary | ❌ Text only (UTF-8) |
| **Use Case** | Local ↔ Cloud transfer | Cloud-side text processing |
| **Size Limit** | ✅ No practical limit | ✅ No limit (chunked) |
| **Progress Tracking** | ✅ Available | ❌ Not available |
| **Binary Support** | ✅ Full support | ❌ Not supported |

### When to Use Each Method

**Use `upload_file()` / `download_file()` for:**
- Transferring files between local machine and cloud
- Working with binary files (images, archives, executables)
- Large file transfers with progress monitoring
- Moving files into/out of the cloud environment

**Use `read_file()` / `write_file()` for:**
- Processing text content within the cloud environment
- Reading configuration files for analysis
- Generating reports and logs
- Text manipulation and editing tasks




<a id="error-handling"></a>
## ❌ Error Handling

### Binary File Error Handling

When attempting to read or write binary files with text methods, you'll encounter specific errors. Here are the actual error messages and how to handle them:

```python
from agentbay import AgentBay
import base64

agent_bay = AgentBay()
session = agent_bay.create().session

# ❌ Binary data write will fail with JSON serialization error
try:
    binary_data = b'\x89PNG\r\n\x1a\n'  # PNG header example
    result = session.file_system.write_file("/tmp/image.png", binary_data)
    if not result.success:
        # Actual error: "Failed to call MCP tool write_file: Object of type bytes is not JSON serializable"
        print(f"Binary data write error: {result.error_message}")
        
        # ✅ Use alternative method: base64 encoding
        base64_content = base64.b64encode(binary_data).decode('utf-8')
        session.file_system.write_file("/tmp/binary_b64.txt", base64_content)
        result = session.command.execute_command("base64 -d /tmp/binary_b64.txt > /tmp/image.png")
        if result.success:
            print("✅ Binary file created successfully using base64")
            
except Exception as e:
    print(f"Exception during binary write: {e}")

# ⚠️ Note: Binary file reads may unexpectedly succeed
# Some binary files might be read as text, but the content will be corrupted
try:
    result = session.file_system.read_file("/bin/ls")  # Binary executable
    if result.success:
        print("⚠️ Binary file read succeeded, but content may be corrupted")
        print(f"Content preview: {repr(result.content[:50])}...")
        
        # ✅ Use command-line tools for proper binary handling
        cmd_result = session.command.execute_command("file /bin/ls")
        if cmd_result.success:
            print(f"File type: {cmd_result.output}")
            
except Exception as e:
    print(f"Exception reading binary file: {e}")

# 📁 File not found errors
try:
    result = session.file_system.read_file("/tmp/nonexistent_file.txt")
    if not result.success:
        # Actual error: "Error in response: Execution failed. Error code:-32602 Error message: Failed to get file status: /tmp/nonexistent_file.txt, error: No such file or directory"
        print(f"File not found error: {result.error_message}")
        
except Exception as e:
    print(f"Exception reading non-existent file: {e}")

agent_bay.delete(session)
```

## 📋 API Method Selection Guide

| Use Case | Recommended Method | Notes |
|----------|-------------------|-------|
| Read text file | `read_file()` | **Text files only**, supports any size via chunked transfer |
| Read multiple text files | `read_multiple_files()` | **Text files only**, more efficient than individual reads |
| Write text content | `write_file()` | **Text files only**, supports any size via chunked transfer |
| Upload file (local → cloud) | `upload_file()` | Supports all file types, with progress tracking |
| Download file (cloud → local) | `download_file()` | Supports all file types, with progress tracking |
| Find and replace text | `edit_file()` | **Text files only**, better than read-modify-write |
| Search for files | `search_files()` | Partial name matching, NO wildcards |
| Move/rename files | `move_file()` | Works for both text and binary files |
| Get file metadata | `get_file_info()` | File size, type, timestamps |
| List directory | `list_directory()` | Directory contents |
| Create directories | `create_directory()` | Supports nested creation |
| Monitor directory changes | `watch_directory()` | Real-time file change monitoring with callbacks |

## 📚 Related Resources

- [Session Management Guide](session-management.md)
- [Command Execution Guide](command-execution.md)
- [Data Persistence Guide](data-persistence.md)

## 🆘 Getting Help

If you encounter issues with file operations:

1. Check file paths and permissions
2. Verify available disk space
3. Review error messages for specific details
4. Consult the [Documentation](../README.md) for detailed information
5. Search [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues) for similar problems

Remember: File operations are fundamental to most cloud workflows. Master these concepts to build robust and efficient applications! 🚀
