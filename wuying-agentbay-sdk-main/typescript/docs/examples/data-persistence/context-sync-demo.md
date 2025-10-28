# Context Sync Dual-Mode Example (TypeScript)

This example demonstrates the dual-mode `context.sync()` functionality in the TypeScript SDK, showing both asynchronous callback-based and synchronous await-based usage patterns.

## Features Demonstrated

- **Context Creation**: Creates persistent contexts for data storage
- **Test Data Generation**: Creates sample files and directories for sync testing
- **Dual-Mode Context Sync**: Shows both callback and await patterns
- **Session Management**: Proper session creation and cleanup
- **Error Handling**: Comprehensive error handling and cleanup
- **Timing Measurement**: Tracks sync operation duration
- **Concurrent Execution**: Demonstrates running multiple sync operations

## Usage Patterns

### 1. Async Mode with Callback

```typescript
// Immediate return with callback handling
const syncResult = await session.context.sync(
  undefined, // contextId
  undefined, // path
  undefined, // mode
  (success: boolean) => {
    if (success) {
      console.log("✅ Context sync completed successfully");
    } else {
      console.log("❌ Context sync completed with failures");
    }
  }
);
```

### 2. Sync Mode with Await

```typescript
// Wait for completion before returning
const syncResult = await session.context.sync();
if (syncResult.success) {
  console.log("✅ Context sync completed successfully");
} else {
  console.log("❌ Context sync completed with failures");
}
```

## Key Differences from Python Version

- **TypeScript/JavaScript**: Uses `Promise` and `async/await` instead of Python's `asyncio`
- **Callback Pattern**: Uses arrow functions for callbacks
- **Timing**: Uses `Date.now()` for millisecond precision timing
- **Error Handling**: Uses try/catch blocks with Promise-based error handling

## Running the Example

```bash
# From the typescript directory
npm run build
node dist/docs/examples/data-persistence/context-sync-demo.js
```

## Expected Output

```
🔄 AgentBay Context Sync Dual-Mode Example (TypeScript)

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
✅ Context sync completed successfully in 2000ms
🗑️  Deleting session from callback...
✅ Session deleted successfully from callback

⏳ Sleeping 3 seconds before next demo...

============================================================
🔄 Method 2: context_sync (Sync with await)
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

⏳ Calling context.sync() with await...
✅ Context sync completed successfully in 1500ms
📤 Sync result: success=true, requestId=req-101
🗑️  Deleting session...
✅ Session deleted successfully

⏳ Waiting for callback demo to complete...

✅ Context sync dual-mode example completed
```

## Configuration

The example uses default configuration values:

- **Max Retries**: 150 attempts
- **Retry Interval**: 1500ms (1.5 seconds)
- **Timeout**: ~5 minutes (150 × 1.5s)

## Error Handling

The example includes comprehensive error handling:

- Sync operation failures
- Session creation failures
- Session deletion failures
- Automatic cleanup on errors

## Integration with Session Deletion

The example demonstrates how `context.sync()` integrates with session deletion:

- Callback mode: Session deletion happens in the callback
- Await mode: Session deletion happens after sync completion
- Both modes avoid double-syncing by passing `false` to `session.delete()`
