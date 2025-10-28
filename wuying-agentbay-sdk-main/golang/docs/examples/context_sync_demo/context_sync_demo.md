# Context Sync Dual-Mode Example (Go)

This example demonstrates the dual-mode `context.sync()` functionality in the Go SDK, showing both asynchronous callback-based and synchronous wait-based usage patterns.

## Features Demonstrated

- **Context Creation**: Creates persistent contexts for data storage
- **Test Data Generation**: Creates sample files and directories for sync testing
- **Dual-Mode Context Sync**: Shows both callback and wait patterns
- **Session Management**: Proper session creation and cleanup
- **Error Handling**: Comprehensive error handling and cleanup
- **Timing Measurement**: Tracks sync operation duration
- **Concurrent Execution**: Demonstrates running multiple sync operations

## Usage Patterns

### 1. Async Mode with Callback

```go
// Use callback mode - function returns immediately
syncResult, err := session.Context.SyncWithCallback(
    "", "", "", // contextId, path, mode
    func(success bool) {
        if success {
            fmt.Println("✅ Context sync completed successfully")
        } else {
            fmt.Println("❌ Context sync completed with failures")
        }
        // Handle completion in callback
    },
    150, 1500, // maxRetries, retryInterval (milliseconds)
)
```

### 2. Sync Mode with Wait

```go
// Use wait mode - function waits for completion
syncResult, err := session.Context.SyncWithCallback("", "", "", nil, 150, 1500)
if err != nil {
    return fmt.Errorf("context sync failed: %w", err)
}

if syncResult.Success {
    fmt.Println("✅ Context sync completed successfully")
} else {
    fmt.Println("❌ Context sync completed with failures")
}
```

## Configuration

The example uses default configuration values:

- **Max Retries**: 150 attempts
- **Retry Interval**: 1500 milliseconds (1.5 seconds)
- **Context Path**: `/tmp/sync_data`
- **Test Files**: Small, medium, and JSON configuration files

## Running the Example

```bash
# From the golang directory
go run docs/examples/data_persistence/context_sync_demo.go

# Or build and run
go build -o context_sync_demo docs/examples/data_persistence/context_sync_demo.go
./context_sync_demo
```

## Expected Output

```
🔄 AgentBay Context Sync Dual-Mode Example (Go)

============================================================
🔄 Method 1: context_sync_with_callback (Async with callback)
============================================================
🔄 Starting context sync with callback demo...

📦 Creating context for persistent storage...
✅ Context created: sync-callback-demo

📦 Creating session with context sync...
✅ Session created: session-123

💾 Creating test data...
✅ Created file: /tmp/sync_data/test_files/small.txt
✅ Created file: /tmp/sync_data/test_files/medium.txt
✅ Created file: /tmp/sync_data/config.json
📊 Created 3/3 test files

📞 Calling context.sync() with callback...
📤 Sync initiation result: success=true, requestId=req-456
⏳ Waiting for callback to complete...
✅ Context sync completed successfully in 2.1s
🗑️  Deleting session from callback...
✅ Session deleted successfully from callback

⏳ Sleeping 3 seconds before next demo...

============================================================
🔄 Method 2: context_sync (Sync with wait)
============================================================
🔄 Starting context sync demo...

📦 Creating context for persistent storage...
✅ Context created: sync-await-demo

📦 Creating session with context sync...
✅ Session created: session-789

💾 Creating test data...
✅ Created file: /tmp/sync_data/test_files/small.txt
✅ Created file: /tmp/sync_data/test_files/medium.txt
✅ Created file: /tmp/sync_data/config.json
📊 Created 3/3 test files

⏳ Calling context.sync() with wait...
✅ Context sync completed successfully in 1.5s
📤 Sync result: success=true, requestId=req-101
🗑️  Deleting session...
✅ Session deleted successfully

⏳ Waiting for callback demo to complete...

✅ Context sync dual-mode example completed
```

## Key Differences from Python/TypeScript

1. **Goroutines**: Uses `go` keyword for async execution instead of `asyncio` or `Promise`
2. **Callbacks**: Uses Go function types instead of lambda functions
3. **Error Handling**: Uses Go's explicit error handling with `error` return values
4. **Time Measurement**: Uses `time.Since()` for duration calculation
5. **Concurrency**: Uses goroutines and channels for concurrent execution

## API Reference

### ContextManager.SyncWithCallback

```go
func (cm *ContextManager) SyncWithCallback(
    contextId, path, mode string,
    callback SyncCallback,
    maxRetries, retryInterval int
) (*ContextSyncResult, error)
```

**Parameters:**

- `contextId`: Optional context ID to sync
- `path`: Optional path to sync
- `mode`: Optional sync mode (upload/download)
- `callback`: Callback function for async mode (nil for sync mode)
- `maxRetries`: Maximum number of polling attempts (default: 150)
- `retryInterval`: Interval between polls in milliseconds (default: 1500)

**Returns:**

- `*ContextSyncResult`: Contains success status and request ID
- `error`: Any error that occurred during sync initiation

### SyncCallback Type

```go
type SyncCallback func(success bool)
```

**Parameters:**

- `success`: `true` if sync completed successfully, `false` if failed or timed out

## Error Handling

The example includes comprehensive error handling for:

- Context creation failures
- Session creation failures
- File system operations
- Sync operation failures
- Session deletion failures

All errors are logged with appropriate context and the application continues execution where possible.

## Performance Considerations

- **Async Mode**: Returns immediately, allowing for concurrent operations
- **Sync Mode**: Blocks until completion, suitable for sequential workflows
- **Polling**: Configurable retry intervals and maximum attempts
- **Memory**: Efficient goroutine usage for background operations
- **Timeouts**: Built-in timeout protection to prevent infinite polling
