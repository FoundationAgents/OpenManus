# FileSystem API Reference (Go)

The FileSystem module provides comprehensive file and directory operations within AgentBay sessions, including real-time directory monitoring capabilities.

## 📖 Related Tutorial

- [Complete Guide to File Operations](../../../docs/guides/common-features/basics/file-operations.md) - Detailed tutorial covering all file operation features

## Overview

The FileSystem interface enables you to:
- Perform standard file operations (read, write, create, delete)
- Monitor directories for real-time file changes
- Handle file uploads and downloads
- Manage file permissions and metadata

## Core Types

### FileChangeEvent

Represents a single file change event detected during directory monitoring.

```go
type FileChangeEvent struct {
    EventType string `json:"eventType"` // "create", "modify", "delete"
    Path      string `json:"path"`      // Full path to the changed file/directory
    PathType  string `json:"pathType"`  // "file" or "directory"
}
```

#### Methods

- `String() string` - Returns a string representation of the event
- `ToDict() map[string]string` - Converts the event to a dictionary
- `FileChangeEventFromDict(data map[string]interface{}) *FileChangeEvent` - Creates an event from dictionary data

### FileChangeResult

Contains the result of file change detection operations.

```go
type FileChangeResult struct {
    models.ApiResponse
    Events   []*FileChangeEvent
    RawData  string
}
```

#### Methods

- `HasChanges() bool` - Returns true if any changes were detected
- `GetModifiedFiles() []string` - Returns paths of modified files only
- `GetCreatedFiles() []string` - Returns paths of created files only
- `GetDeletedFiles() []string` - Returns paths of deleted files only

## Directory Monitoring Methods

### GetFileChange

Retrieves file changes that occurred in a directory since the last check.

```go
func (fs *FileSystem) GetFileChange(path string) (*FileChangeResult, error)
```

**Parameters:**
- `path` (string): Directory path to monitor

**Returns:**
- `*FileChangeResult`: Result containing detected file changes
- `error`: Error if the operation failed

**Example:**
```go
package main

import (
    "fmt"
    "log"
    "github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
    // Initialize AgentBay
    agentBay, err := agentbay.NewAgentBay("your-api-key")
    if err != nil {
        log.Fatal(err)
    }

    // Create session
    sessionParams := &agentbay.CreateSessionParams{
        ImageId: "code_latest",
    }
    sessionResult, err := agentBay.Create(sessionParams)
    if err != nil {
        log.Fatal(err)
    }

    session := sessionResult.Session
    fileSystem := session.FileSystem

    // Check for file changes
    result, err := fileSystem.GetFileChange("/tmp/watch_dir")
    if err != nil {
        log.Fatal(err)
    }

    if result.HasChanges() {
        fmt.Printf("Detected %d changes:\n", len(result.Events))
        for _, event := range result.Events {
            fmt.Printf("- %s\n", event.String())
        }
    } else {
        fmt.Println("No changes detected")
    }
    // Output: No changes detected
    // RequestID: 478639BF-138A-1D9D-9844-146BF08E6DD9
}
```

### WatchDirectory

Continuously monitors a directory for file changes and executes a callback function when changes are detected.

```go
func (fs *FileSystem) WatchDirectory(
    path string,
    callback func([]*FileChangeEvent),
    interval time.Duration,
    stopChan <-chan struct{},
) *sync.WaitGroup
```

**Parameters:**
- `path` (string): Directory path to monitor
- `callback` (func([]*FileChangeEvent)): Function called when changes are detected
- `interval` (time.Duration): Polling interval as a time.Duration (e.g., 1*time.Second)
- `stopChan` (<-chan struct{}): Channel to signal when to stop monitoring

**Returns:**
- `*sync.WaitGroup`: WaitGroup that can be used to wait for monitoring to stop

**Example:**
```go
package main

import (
    "fmt"
    "log"
    "time"
    "github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
    "github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/filesystem"
)

func main() {
    // Initialize AgentBay
    agentBay, err := agentbay.NewAgentBay("your-api-key")
    if err != nil {
        log.Fatal(err)
    }

    // Create session
    sessionParams := &agentbay.CreateSessionParams{
        ImageId: "code_latest",
    }
    sessionResult, err := agentBay.Create(sessionParams)
    if err != nil {
        log.Fatal(err)
    }

    session := sessionResult.Session
    fileSystem := session.FileSystem

    // Create test directory in cloud environment
    testDir := "/tmp/agentbay_watch_test"
    _, err = fileSystem.CreateDirectory(testDir)
    if err != nil {
        log.Printf("Error creating directory: %v", err)
    }

    // Set up callback function
    callback := func(events []*filesystem.FileChangeEvent) {
        fmt.Printf("Detected %d file changes:\n", len(events))
        for _, event := range events {
            fmt.Printf("- %s\n", event.String())
        }
    }

    // Create stop channel
    stopChan := make(chan struct{})

    // Start monitoring
    wg := fileSystem.WatchDirectory(testDir, callback, 1*time.Second, stopChan)

    // Simulate file operations
    time.Sleep(2 * time.Second)
    
    // Create a file in cloud environment
    testFile := testDir + "/test.txt"
    _, err = fileSystem.WriteFile(testFile, "Hello, AgentBay!", "overwrite")
    if err != nil {
        log.Printf("Error creating file: %v", err)
    }
    // Output: Detected 2 file changes:
    // - FileChangeEvent(eventType='modify', path='/tmp/agentbay_watch_test/test.txt', pathType='file')
    // - FileChangeEvent(eventType='create', path='/tmp/agentbay_watch_test/test.txt', pathType='file')

    // Wait for detection
    time.Sleep(2 * time.Second)

    // Modify the file
    _, err = fileSystem.WriteFile(testFile, "Modified content", "overwrite")
    if err != nil {
        log.Printf("Error modifying file: %v", err)
    }
    // Output: Detected 1 file changes:
    // - FileChangeEvent(eventType='modify', path='/tmp/agentbay_watch_test/test.txt', pathType='file')

    // Wait for detection
    time.Sleep(2 * time.Second)

    // Stop monitoring
    close(stopChan)
    wg.Wait()

    fmt.Println("Monitoring stopped")
}
```

## Helper Functions

### FileChangeEventFromDict

Creates a FileChangeEvent from dictionary data.

```go
func FileChangeEventFromDict(data map[string]interface{}) *FileChangeEvent
```

**Parameters:**
- `data` (map[string]interface{}): Dictionary containing event data

**Returns:**
- `*FileChangeEvent`: New FileChangeEvent instance

## Best Practices

### 1. Polling Interval

Choose an appropriate polling interval based on your needs:
- **High-frequency monitoring**: 100-500ms (higher CPU usage)
- **Normal monitoring**: 1000-2000ms (balanced)
- **Low-frequency monitoring**: 5000ms+ (lower CPU usage)

### 2. Error Handling

Always handle errors and implement proper cleanup:

```go
stopChan := make(chan struct{})
defer close(stopChan)

go func() {
    err := fileSystem.WatchDirectory(path, callback, 1000, stopChan)
    if err != nil {
        log.Printf("Watch error: %v", err)
    }
}()
```

### 3. Callback Function Design

Keep callback functions lightweight and handle errors gracefully:

```go
callback := func(events []*FileChangeEvent) {
    defer func() {
        if r := recover(); r != nil {
            log.Printf("Callback panic recovered: %v", r)
        }
    }()
    
    for _, event := range events {
        // Process event
        processFileChange(event)
    }
}
```

### 4. Resource Management

Always clean up resources and stop monitoring when done:

```go
// Use context for better control
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()

stopChan := make(chan struct{})
go func() {
    select {
    case <-ctx.Done():
        close(stopChan)
    }
}()
```

## Common Use Cases

### 1. Development File Watcher

Monitor source code changes during development:

```go
callback := func(events []*FileChangeEvent) {
    for _, event := range events {
        if filepath.Ext(event.Path) == ".go" && event.EventType == "modify" {
            fmt.Printf("Go file modified: %s\n", event.Path)
            // Trigger rebuild or test
        }
    }
}
```

### 2. Log File Monitor

Monitor log files for new entries:

```go
callback := func(events []*FileChangeEvent) {
    for _, event := range events {
        if strings.Contains(event.Path, ".log") && event.EventType == "modify" {
            fmt.Printf("Log file updated: %s\n", event.Path)
            // Process new log entries
        }
    }
}
```

### 3. Configuration File Watcher

Monitor configuration files for changes:

```go
callback := func(events []*FileChangeEvent) {
    for _, event := range events {
        if strings.HasSuffix(event.Path, "config.json") {
            fmt.Printf("Configuration changed: %s\n", event.Path)
            // Reload configuration
        }
    }
}
```

## Troubleshooting

### Common Issues

1. **High CPU Usage**: Reduce polling frequency by increasing `intervalMs`
2. **Missing Events**: Ensure the directory exists and is accessible
3. **Callback Errors**: Implement proper error handling in callback functions
4. **Memory Leaks**: Always close stop channels and clean up goroutines

### Performance Considerations

- Use appropriate polling intervals
- Filter events in callback functions to reduce processing overhead
- Consider using multiple watchers for different directories with different intervals
- Monitor memory usage when watching large directories with frequent changes

## Limitations

- Polling-based detection (not real-time filesystem events)
- Performance depends on polling interval and directory size
- May miss very rapid file changes that occur between polls
- Requires active session connection to AgentBay service


```go
CreateDirectory(path string) (*FileDirectoryResult, error)
```

**Parameters:**
- `path` (string): The path of the directory to create.

**Returns:**
- `*FileDirectoryResult`: A result object containing success status and RequestID.
- `error`: An error if the directory creation fails.


```go
EditFile(path string, edits []map[string]string, dryRun bool) (*FileWriteResult, error)
```

**Parameters:**
- `path` (string): The path of the file to edit.
- `edits` ([]map[string]string): Array of edit operations, each containing oldText and newText.
- `dryRun` (bool): If true, preview changes without applying them.

**Returns:**
- `*FileWriteResult`: A result object containing success status and RequestID.
- `error`: An error if the file editing fails.


```go
GetFileInfo(path string) (*FileInfoResult, error)
```

**Parameters:**
- `path` (string): The path of the file or directory to inspect.

**Returns:**
- `*FileInfoResult`: A result object containing file information and RequestID.
- `error`: An error if getting the file information fails.


```go
ListDirectory(path string) (*DirectoryListResult, error)
```

**Parameters:**
- `path` (string): The path of the directory to list.

**Returns:**
- `*DirectoryListResult`: A result object containing directory entries and RequestID.
- `error`: An error if listing the directory fails.

**DirectoryListResult Structure:**
```go
type DirectoryListResult struct {
    RequestID string           // Unique request identifier for debugging
    Entries   []*DirectoryEntry // Array of directory entries
}

type DirectoryEntry struct {
    Name        string // Name of the file or directory
    IsDirectory bool   // Whether this entry is a directory
}
```


```go
MoveFile(source, destination string) (*FileWriteResult, error)
```

**Parameters:**
- `source` (string): The path of the source file or directory.
- `destination` (string): The path of the destination file or directory.

**Returns:**
- `*FileWriteResult`: A result object containing success status and RequestID.
- `error`: An error if moving the file fails.

**FileWriteResult Structure:**
```go
type FileWriteResult struct {
    RequestID string // Unique request identifier for debugging
    Success   bool   // Whether the file was written successfully
}
```


```go
ReadFile(path string) (*FileReadResult, error)
```

**Parameters:**
- `path` (string): The path of the file to read.

**Returns:**
- `*FileReadResult`: A result object containing the file content and RequestID.
- `error`: An error if the file reading fails.

**FileReadResult Structure:**
```go
type FileReadResult struct {
    RequestID string // Unique request identifier for debugging
    Content   string // The contents of the file
}
```

**Note:**
This method automatically handles both small and large files. For large files, it uses internal chunking with a default chunk size of 50KB to overcome API size limitations. No manual chunk size configuration is needed.


Reads the contents of multiple files.


```go
ReadMultipleFiles(paths []string) (map[string]string, error)
```

**Parameters:**
- `paths` ([]string): Array of paths to the files to read.

**Returns:**
- `map[string]string`: A map with file paths as keys and their contents as values.
- `error`: An error if reading the files fails.


```go
SearchFiles(path, pattern string, excludePatterns []string) (*SearchFilesResult, error)
```

**Parameters:**
- `path` (string): The path of the directory to start the search.
- `pattern` (string): Pattern to match.
- `excludePatterns` ([]string): Patterns to exclude.

**Returns:**
- `*SearchFilesResult`: A result object containing search results and RequestID.
- `error`: An error if the search fails.

**SearchFilesResult Structure:**
```go
type SearchFilesResult struct {
    RequestID string   // Unique request identifier for debugging
    Results   []string // Array of search results
}
```


```go
WriteFile(path, content string, mode string) (*FileWriteResult, error)
```

**Parameters:**
- `path` (string): The path of the file to write.
- `content` (string): Content to write to the file.
- `mode` (string): "overwrite" (default), "append", or "create_new".

**Returns:**
- `*FileWriteResult`: A result object containing success status and RequestID.
- `error`: An error if writing the file fails.

**FileWriteResult Structure:**
```go
type FileWriteResult struct {
    RequestID string // Unique request identifier for debugging
    Success   bool   // Whether the file was written successfully
}
```

**Note:**
This method automatically handles both small and large content. For large content, it uses internal chunking with a default chunk size of 50KB to overcome API size limitations. No manual chunk size configuration is needed.


**Deprecated Methods:**

The following methods have been removed in favor of the unified `ReadFile` and `WriteFile` methods:
- `ReadLargeFile` - Use `ReadFile` instead (automatic chunking)
- `WriteLargeFile` - Use `WriteFile` instead (automatic chunking)

## Usage Examples

### Basic File Operations

```go
package main

import (
    "fmt"
    "log"
    "github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
    // Create a session
    agentBay, err := agentbay.NewAgentBay("your-api-key")
    if err != nil {
        log.Fatal(err)
    }
    sessionResult, err := agentBay.Create(nil)
    if err != nil {
        log.Fatal(err)
    }
    session := sessionResult.Session
    fileSystem := session.FileSystem

    // Create a directory
    createResult, err := fileSystem.CreateDirectory("/tmp/test")
    if err != nil {
        log.Printf("Error creating directory: %v", err)
    } else {
        fmt.Printf("Directory created: %t\n", createResult.Success)
    }
    // Output: Directory created: true
    // RequestID: 27152FAE-4E31-1578-9B50-A367C4848359

    // Write a file
    writeResult, err := fileSystem.WriteFile("/tmp/test/example.txt", "Hello, world!", "overwrite")
    if err != nil {
        log.Printf("Error writing file: %v", err)
    } else {
        fmt.Printf("File written successfully: %t\n", writeResult.Success)
    }
    // Output: File written successfully: true
    // RequestID: F97C3D43-2601-1654-9FF3-B6573B645844

    // Read a file
    readResult, err := fileSystem.ReadFile("/tmp/test/example.txt")
    if err != nil {
        log.Printf("Error reading file: %v", err)
    } else {
        fmt.Printf("File content: %s\n", readResult.Content)
    }
    // Output: File content: Hello, world!
    // RequestID: 6E4FEF65-BCE0-1898-AC2D-2AA1B12CDCCB

    // Edit a file
    edits := []map[string]string{
        {"oldText": "Hello", "newText": "Hi"},
    }
    editResult, err := fileSystem.EditFile("/tmp/test/example.txt", edits, false)
    if err != nil {
        log.Printf("Error editing file: %v", err)
    } else {
        fmt.Printf("File edited successfully: %t\n", editResult.Success)
    }
    // Output: File edited successfully: true
    // Diff output:
    // --- /tmp/test/example.txt
    // +++ /tmp/test/example.txt
    // - Hello, world!
    // + Hi, world!

    // Get file info
    fileInfoResult, err := fileSystem.GetFileInfo("/tmp/test/example.txt")
    if err != nil {
        log.Printf("Error getting file info: %v", err)
    } else {
        fmt.Printf("File size: %d bytes\n", fileInfoResult.FileInfo.Size)
        fmt.Printf("Is directory: %t\n", fileInfoResult.FileInfo.IsDirectory)
    }
    // Output: File size: 11 bytes
    // Output: Is directory: false

    // List directory
    listResult, err := fileSystem.ListDirectory("/tmp/test")
    if err != nil {
        log.Printf("Error listing directory: %v", err)
    } else {
        for _, entry := range listResult.Entries {
            entryType := "Directory"
            if !entry.IsDirectory {
                entryType = "File"
            }
            fmt.Printf("%s: %s\n", entryType, entry.Name)
        }
    }
    // Output: File: example.txt

    // Move a file
    moveResult, err := fileSystem.MoveFile("/tmp/test/example.txt", "/tmp/test/moved.txt")
    if err != nil {
        log.Printf("Error moving file: %v", err)
    } else {
        fmt.Printf("File moved successfully: %t\n", moveResult.Success)
    }
    // Output: File moved successfully: true
    // RequestID: 232965AD-A027-1D50-8A41-B266B0710937
}
```

## Related Resources

- [Session Class](session.md): The session class that provides access to the FileSystem class.
- [Command Class](command.md): Provides methods for executing commands within a session.