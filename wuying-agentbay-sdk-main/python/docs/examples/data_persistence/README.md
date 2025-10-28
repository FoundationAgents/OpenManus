# Data Persistence Examples

This directory contains examples demonstrating data persistence functionality in AgentBay SDK.

## Examples

### 1. `main.py` - Basic Data Persistence

Demonstrates the fundamental data persistence features:

- Context creation for persistent storage
- File persistence across multiple sessions
- Context synchronization and file sharing
- Multi-session data verification

### 2. `context_sync_demo.py` - Advanced Sync with Callbacks

Demonstrates the new callback-based context synchronization:

- Async context sync with callback functions
- Timing analysis and performance monitoring
- Status verification using `context.info()`
- Multiple sync operations and error handling
- Backward compatibility with traditional sync

### 3. `recycle_policy_example.py` - Data Lifecycle Management

Demonstrates RecyclePolicy for controlling context data lifecycle:

- Using default RecyclePolicy (keeps data forever)
- Setting custom lifecycle durations (1 day, 3 days, etc.)
- Applying RecyclePolicy to specific paths
- Available lifecycle options
- Error handling (wildcard patterns validation)

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
- **Lifecycle Options**: 1 day to forever (11 options available)
- **Path-Specific Policies**: Apply different lifecycles to different directories
- **Automatic Cleanup**: Data is automatically deleted after specified duration
- **Wildcard Validation**: Ensures path safety by rejecting wildcard patterns

## Usage

### Basic Data Persistence

```bash
cd python/docs/examples/data_persistence
python main.py
```

### Context Sync Callbacks

```bash
cd python/docs/examples/data_persistence
python context_sync_demo.py
```

### RecyclePolicy Example

```bash
cd python/docs/examples/data_persistence
python recycle_policy_example.py
```

## Prerequisites

- AgentBay SDK installed
- Valid API key configured (via environment variable `AGENTBAY_API_KEY` or default configuration)
- Network access to AgentBay services

## Expected Behavior

Both examples will:

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

Both examples provide detailed console output showing:

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
