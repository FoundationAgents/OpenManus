# Data Persistence Examples

This directory contains examples demonstrating data persistence functionality in AgentBay SDK for TypeScript.

## Examples

### 1. `data-persistence.ts` - Basic Data Persistence

Demonstrates the fundamental data persistence features:

- Context creation for persistent storage
- File persistence across multiple sessions
- Context synchronization and file sharing
- Multi-session data verification

### 2. `context-sync-demo.ts` - Advanced Sync with Callbacks

Demonstrates the callback-based context synchronization:

- Async context sync operations
- Timing analysis and performance monitoring
- Status verification using `context.info()`
- Multiple sync operations and error handling
- Backward compatibility with traditional sync

### 3. `recycle-policy-example.ts` - Data Lifecycle Management

Demonstrates RecyclePolicy for controlling context data lifecycle:

- Using default RecyclePolicy (keeps data forever)
- Setting custom lifecycle durations (1 day, 3 days, etc.)
- Applying RecyclePolicy to specific paths
- Available lifecycle options

## Key Features

### Data Persistence

- **Context Creation**: Create persistent storage contexts
- **Cross-Session Persistence**: Data survives session deletion
- **File Synchronization**: Automatic sync of files to persistent storage
- **Multi-Session Access**: Access data from different sessions

### Context Sync Callbacks

- **Async Operations**: Non-blocking sync operations
- **Real-time Feedback**: Immediate notification on completion
- **Timing Information**: Detailed performance metrics
- **Error Handling**: Graceful handling of failures and timeouts
- **Status Monitoring**: Track sync progress and completion

### Data Lifecycle Management

- **RecyclePolicy**: Control how long context data is retained in the cloud
- **Lifecycle Options**: 1 day to forever (10 options available)
- **Path-Specific Policies**: Apply different lifecycles to different directories
- **Automatic Cleanup**: Data is automatically deleted after specified duration
- **Path Validation**: Ensures path safety (no wildcard patterns)

## Usage

### Basic Data Persistence

```bash
cd typescript/docs/examples/data-persistence
npx ts-node data-persistence.ts
```

### Context Sync Demo

```bash
cd typescript/docs/examples/data-persistence
npx ts-node context-sync-demo.ts
```

### RecyclePolicy Example

```bash
cd typescript/docs/examples/data-persistence
npx ts-node recycle-policy-example.ts
```

## Prerequisites

- AgentBay SDK installed
- Valid API key configured (via environment variable `AGENTBAY_API_KEY`)
- Network access to AgentBay services
- Node.js 16 or later
- TypeScript 4.5 or later

## Expected Behavior

All examples will:

1. Create a persistent context
2. Create a session with context synchronization
3. Write test data to the persistent storage
4. Demonstrate data persistence across sessions
5. Clean up resources

The callback example additionally shows:

- Async sync operations with timing
- Callback notifications
- Status monitoring
- Error handling scenarios

## Output

All examples provide detailed console output showing:

- Step-by-step progress
- Success/failure status for each operation
- Timing information (callback example)
- Data verification results
- Cleanup confirmation

## Notes

- Examples use temporary contexts that are cleaned up after execution
- File paths use `/tmp/` for demonstration purposes
- Timing may vary based on network conditions and file sizes
- The callback example includes timeout handling for robustness

## Related Documentation

- [Data Persistence Guide](../../../../docs/guides/common-features/basics/data-persistence.md) - Comprehensive guide on data persistence
- [Context Management](../context-management/README.md) - Context creation and management
- [File Operations](../filesystem-example/README.md) - File handling and management
