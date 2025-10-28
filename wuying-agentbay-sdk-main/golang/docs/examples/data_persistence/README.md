# AgentBay SDK - Data Persistence Examples

This directory contains examples demonstrating data persistence functionality using the AgentBay SDK for Golang:

## Examples

### 1. `main.go` - Basic Data Persistence

Demonstrates fundamental data persistence features:

- Context creation for persistent storage
- File persistence across multiple sessions
- Context synchronization and file sharing
- Cross-session data verification

### 2. `recycle_policy_example.go` - Data Lifecycle Management

Demonstrates RecyclePolicy for controlling context data lifecycle:

- Using default RecyclePolicy (keeps data forever)
- Setting custom lifecycle durations (1 day, 3 days, etc.)
- Applying RecyclePolicy to specific paths
- Available lifecycle options

## Features Demonstrated

1. **Context Management**: Creating and managing contexts for persistent storage
2. **Multi-Session Persistence**: Writing data in one session and reading it in another
3. **File Operations**: Creating directories, writing JSON configs, logs, and data files
4. **Context Synchronization**: Automatic sync of data between sessions and cloud storage
5. **Error Handling**: Comprehensive error handling throughout the process
6. **Resource Cleanup**: Proper cleanup of sessions and contexts

## What This Example Does

1. **Step 1**: Creates a persistent context for data storage
2. **Step 2**: Creates the first session with context synchronization configured
3. **Step 3**: Writes various types of data (JSON config, logs, text files) in the first session
4. **Step 4**: Deletes the first session (with context sync to preserve data)
5. **Step 5**: Creates a second session with the same context sync configuration
6. **Step 6**: Verifies that all data from the first session is accessible in the second session
7. **Step 7**: Adds new data in the second session
8. **Step 8**: Cleans up all resources

## Expected Output

The example will show:
- Successful context creation
- File creation and writing in the first session
- Session deletion with context synchronization
- New session creation and data verification
- Confirmation that persistent data survives across sessions

## Prerequisites

- Valid AgentBay API key set in environment variable `AGENTBAY_API_KEY`
- Network connectivity to AgentBay services
- Golang environment set up with required dependencies

## Running the Example

```bash
# Set your API key
export AGENTBAY_API_KEY="your-api-key-here"

# Run the example
go run main.go
```

## Key Concepts

- **Context**: A persistent storage space that survives across sessions
- **Context Sync**: Configuration that determines how data is synchronized between sessions and cloud storage
- **Session**: A temporary compute environment that can mount contexts for data access
- **Sync Policy**: Rules governing when and how data is uploaded/downloaded during synchronization

This example is based on the Python data persistence example and demonstrates the same functionality using idiomatic Go patterns and the Golang AgentBay SDK.