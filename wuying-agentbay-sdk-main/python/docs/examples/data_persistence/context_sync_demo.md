# Context Sync Anonymous Callback Example

This example demonstrates the `context.sync()` method with anonymous callback functionality, showing how to use the new asynchronous sync capabilities in AgentBay SDK.

## Overview

The example showcases:

- **Anonymous Callback Functions**: Using lambda functions for callback implementation
- **Async Context Sync**: Using `context.sync()` with callback functions
- **Timing Analysis**: Measuring sync operation duration
- **Session Deletion in Callback**: Deleting session within callback without sync_context
- **Error Handling**: Managing sync failures and timeouts

## Key Features Demonstrated

### 1. Dual-Mode Sync Function

The `context.sync()` function now supports both async and sync calling patterns:

```python
# Pattern 1: Async call - wait for completion
result = await session.context.sync()
if result.success:
    print("✅ Async sync completed successfully")

# Pattern 2: Sync call with callback - immediate return
session.context.sync(callback=lambda success: (
    print(f"✅ Anonymous sync callback: {'SUCCESS' if success else 'FAILED'}") or
    print("🧹 Deleting session after sync completion...") or
    agent_bay.delete(session) or
    print("✅ Session deleted successfully")
))
```

### 2. Timing Analysis

The example includes detailed timing analysis for different file sizes:

- **Small files** (< 1KB): Typically 2-5 seconds
- **Medium files** (1-10KB): Typically 5-15 seconds
- **Large files** (> 10KB): Typically 15-60 seconds

### 3. Session Deletion in Callback

Demonstrates deleting the session within the callback function without sync_context:

```python
# Session deletion happens automatically in the callback
agent_bay.delete(session, sync_context=False)
```

### 4. Automatic Handling

The callback handles everything automatically without needing to wait:

```python
# Callback handles success, failure, and cleanup automatically
# No need for manual waiting or timeout handling
```

## Example Structure

### Step 1: Context Creation

- Creates a persistent context for data storage
- Configures sync policy and context sync settings

### Step 2: Session Setup

- Creates session with context synchronization
- Mounts context to `/tmp/sync_data` path

### Step 3: Test Data Creation

- Creates multiple test files of different sizes
- Sets up directory structure for organized testing

### Step 4: Anonymous Callback Sync Demonstration

- Shows async sync with anonymous callback functionality
- Demonstrates timing measurement and status monitoring
- Includes session deletion within callback (no sync_context)
- Automatic handling without manual waiting
