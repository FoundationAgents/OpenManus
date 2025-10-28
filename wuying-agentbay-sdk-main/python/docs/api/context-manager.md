# ContextManager API Reference

The `ContextManager` class provides functionality for managing contexts within a session. It enables you to interact with the contexts that are synchronized to the session, including reading and writing data, and managing file operations.

## 📖 Related Tutorial

- [Data Persistence Guide](../../../docs/guides/common-features/basics/data-persistence.md) - Detailed tutorial on context management and data persistence

## Overview

The `ContextManager` is accessed through a session instance (`session.context`) and provides functionality for managing contexts within that session.

## Properties

```python
session  # The Session instance that this ContextManager belongs to
```

## Data Types

```python
class ContextStatusData:
    context_id: str     # The ID of the context
    path: str           # The path where the context is mounted
    error_message: str  # Error message if the operation failed
    status: str         # Status of the synchronization task
    start_time: int     # Start time of the task (Unix timestamp)
    finish_time: int    # Finish time of the task (Unix timestamp)
    task_type: str      # Type of the task (e.g., "upload", "download")
```

## Result Types

```python
class ContextInfoResult(ApiResponse):
    request_id: str  # The request ID
    context_status_data: List[ContextStatusData]  # Array of context status data objects
```

```python
class ContextSyncResult(ApiResponse):
    request_id: str  # The request ID
    success: bool    # Indicates whether the synchronization was successful
```

## Methods

### info

Gets information about context synchronization status.

```python
info(context_id: Optional[str] = None, path: Optional[str] = None, task_type: Optional[str] = None) -> ContextInfoResult
```

**Parameters:**
- `context_id` (str, optional): The ID of the context to get information for.
- `path` (str, optional): The path where the context is mounted.
- `task_type` (str, optional): The type of task to get information for (e.g., "upload", "download").

**Returns:**
- `ContextInfoResult`: A result object containing the context status data and request ID.
  - `context_status_data` (List[ContextStatusData]): A list of context status data objects.

**Example:**
```python
from agentbay import AgentBay

# Initialize the SDK
agent_bay = AgentBay(api_key="your_api_key")

# Create a session
result = agent_bay.create()
if result.success:
    session = result.session
    
    try:
        # Get context synchronization information
        info_result = session.context.info()
        print(f"Request ID: {info_result.request_id}")
        print(f"Context status data count: {len(info_result.context_status_data)}")
        
        if info_result.context_status_data:
            for item in info_result.context_status_data:
                print(f"  Context {item.context_id}: Status={item.status}, "
                      f"Path={item.path}, TaskType={item.task_type}")
        else:
            print("No context synchronization tasks found")
    finally:
        session.delete()

# Expected output:
# Request ID: 41FC3D61-4AFB-1D2E-A08E-5737B2313234
# Context status data count: 0
# No context synchronization tasks found
```

### sync

Synchronizes a context with the session. This method is asynchronous and supports two modes:
- **Async mode (default)**: When called with `await`, it waits for the sync operation to complete.
- **Callback mode**: When a callback is provided, it returns immediately and calls the callback when complete.

```python
async sync(
    context_id: Optional[str] = None, 
    path: Optional[str] = None, 
    mode: Optional[str] = None,
    callback: Optional[Callable[[bool], None]] = None,
    max_retries: int = 150,
    retry_interval: int = 1500
) -> ContextSyncResult
```

**Parameters:**
- `context_id` (str, optional): The ID of the context to synchronize.
- `path` (str, optional): The path where the context should be mounted.
- `mode` (str, optional): The synchronization mode (e.g., "upload", "download").
- `callback` (Callable[[bool], None], optional): Optional callback function that receives success status. If provided, the method runs in background and calls callback when complete.
- `max_retries` (int): Maximum number of retries for polling completion status. Default: 150.
- `retry_interval` (int): Milliseconds to wait between retries. Default: 1500.

**Returns:**
- `ContextSyncResult`: A result object containing success status and request ID.
  - `success` (bool): Indicates whether the synchronization was successful.

**Example (Async mode - waits for completion):**
```python
import asyncio
from agentbay import AgentBay

async def sync_context_example():
    # Initialize the SDK
    agent_bay = AgentBay(api_key="your_api_key")

    # Create a session
    result = agent_bay.create()
    if result.success:
        session = result.session
        
        try:
            # Get or create a context
            context_result = agent_bay.context.get('my-context', True)
            if context_result.context:
                # Trigger context synchronization and wait for completion
                sync_result = await session.context.sync(
                    context_id=context_result.context_id,
                    path="/mnt/persistent",
                    mode="upload"
                )
                
                print(f"Sync completed - Success: {sync_result.success}")
                print(f"Request ID: {sync_result.request_id}")
        finally:
            session.delete()

asyncio.run(sync_context_example())

# Expected output:
# Sync completed - Success: True
# Request ID: 39B00280-B9DA-17D1-BCBB-9C577E057F0A
```

**Example (Callback mode - returns immediately):**
```python
import asyncio
from agentbay import AgentBay

async def sync_with_callback_example():
    agent_bay = AgentBay(api_key="your_api_key")
    result = agent_bay.create()
    
    if result.success:
        session = result.session
        
        try:
            context_result = agent_bay.context.get('my-context', True)
            
            # Define a callback function
            def on_sync_complete(success: bool):
                if success:
                    print("Context sync completed successfully")
                else:
                    print("Context sync failed or timed out")
            
            # Trigger sync with callback - returns immediately
            sync_result = await session.context.sync(
                context_id=context_result.context_id,
                path="/mnt/persistent",
                mode="upload",
                callback=on_sync_complete,  # Callback mode
                max_retries=10,
                retry_interval=1000
            )
            
            print(f"Sync triggered - Success: {sync_result.success}")
            print(f"Request ID: {sync_result.request_id}")
            
            # Wait a bit for callback to be called
            await asyncio.sleep(3)
        finally:
            session.delete()

asyncio.run(sync_with_callback_example())

# Expected output:
# Sync triggered - Success: True
# Request ID: 39B00280-B9DA-17D1-BCBB-9C577E057F0A
# Context sync completed successfully  (printed by callback after completion)
```

## Complete Usage Example

```python
import asyncio
from agentbay import AgentBay

async def complete_context_manager_example():
    # Initialize the SDK
    agent_bay = AgentBay(api_key="your_api_key")

    # Create a session
    result = agent_bay.create()
    if not result.success:
        print(f"Failed to create session: {result.error_message}")
        return

    session = result.session
    print(f"Session created: {session.get_session_id()}")

    try:
        # Get or create a context
        context_result = agent_bay.context.get('my-persistent-context', True)
        if not context_result.context:
            print("Failed to get context")
            return

        print(f"Context ID: {context_result.context_id}")

        # Check initial context status
        info_result = session.context.info()
        print(f"\nInitial context status data count: {len(info_result.context_status_data)}")

        # Synchronize context and wait for completion
        sync_result = await session.context.sync(
            context_id=context_result.context_id,
            path="/mnt/persistent",
            mode="upload"
        )

        print(f"\nSync completed - Success: {sync_result.success}")
        print(f"Request ID: {sync_result.request_id}")

        # Check final context status
        final_info = session.context.info(
            context_id=context_result.context_id,
            path="/mnt/persistent"
        )

        print(f"\nFinal context status data count: {len(final_info.context_status_data)}")
        for item in final_info.context_status_data:
            print(f"  Context {item.context_id}: Status={item.status}, TaskType={item.task_type}")

    finally:
        # Cleanup
        session.delete()
        print("\nSession deleted")

asyncio.run(complete_context_manager_example())

# Expected output:
# Session created: session-04bdwfj7u1sew7t4f
# Context ID: SdkCtx-04bdw8o39bq47rv1t
#
# Initial context status data count: 0
#
# Sync completed - Success: True
# Request ID: 39B00280-B9DA-17D1-BCBB-9C577E057F0A
#
# Final context status data count: 0
#
# Session deleted
```

## Notes

- The `ContextManager` is designed to work with contexts synchronized to a session. It is different from the `ContextService` (accessible via `agent_bay.context`) which manages contexts globally.
- `info()` returns information about the current synchronization tasks for contexts in the session.
- `sync()` is an async method. When called without a callback, it waits for synchronization to complete. When called with a callback, it returns immediately and calls the callback when complete.
- Synchronization polling checks the status every `retry_interval` milliseconds for up to `max_retries` attempts.
- Empty `context_status_data` arrays are normal when there are no active sync tasks.
- The `sync()` method must be called with `await` in async context, or the callback parameter can be used for background execution.
