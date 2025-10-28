# Complete Data Persistence Guide

This guide covers AgentBay SDK's data persistence features, including context concepts, context management, and data synchronization strategies for maintaining state across sessions.

## 📋 Table of Contents

- [Core Concepts](#core-concepts)
- [Context Management](#context-management)
- [Data Synchronization Strategies](#data-synchronization-strategies)

<a id="core-concepts"></a>
## 🎯 Core Concepts

### Understanding Context - A Simple Example

Before diving into complex features, let's understand what Context and ContextId represent with the simplest possible example:

```python
from agentbay import AgentBay

# Initialize client
agent_bay = AgentBay()

# Create a context - think of it as a "named storage box"
context_result = agent_bay.context.get("my-storage-box", create=True)
context = context_result.context

print(f"Context Name: {context.name}")        # Output: "my-storage-box"
print(f"Context ID: {context.id}")           # Output: "SdkCtx-123abc456def" (unique identifier)
```

**What is a Context?**
- A **Context** is like a persistent storage container that survives beyond individual sessions
- The **Context Name** (like "my-storage-box") is what you use to reference it
- The **Context ID** (like "SdkCtx-123abc456def") is the system's unique identifier for that storage container

**What is a ContextId?**
- Every Context has a unique ID assigned by the system
- You use this ID to mount the context's data into sessions
- Think of it as the "address" where your persistent data lives

### The Persistence Problem

In AgentBay, **sessions are temporary** - when a session ends, all its data disappears:

```python
# Without Context: Data is LOST when session ends
session1 = agent_bay.create().session
session1.file_system.write_file("/tmp/data.txt", "Important data")
agent_bay.delete(session1)
# Session ends -> data.txt is GONE forever!

# With Context: Data is SAVED permanently
from agentbay import ContextSync, CreateSessionParams

context = agent_bay.context.get("my-storage", create=True).context
context_sync = ContextSync.new(context.id, "/tmp/persistent")  # Mount context at /tmp/persistent

session2 = agent_bay.create(CreateSessionParams(context_syncs=[context_sync])).session
session2.file_system.write_file("/tmp/persistent/data.txt", "Important data")
agent_bay.delete(session2, sync_context=True)  # Ensure data syncs before continuing

# Later, in a new session, you can access the same data:
session3 = agent_bay.create(CreateSessionParams(context_syncs=[context_sync])).session
content = session3.file_system.read_file("/tmp/persistent/data.txt")
print(content.content)  # Output: "Important data"
agent_bay.delete(session3)
```

### Implementation Principle - How Context Works Under the Hood

Understanding the technical implementation helps you better use the Context system:

**Context Storage Architecture:**
```
ContextId (e.g., "SdkCtx-123abc456def")
    ↓
OSS Directory (/contexts/SdkCtx-123abc456def/)
    ├── file1.txt
    ├── data/
    │   └── config.json
    └── logs/
        └── app.log
```

**What happens when you create a Context:**
1. **OSS Directory Creation**: AgentBay creates a dedicated OSS (Object Storage Service) directory
2. **Unique Mapping**: Each ContextId maps to a specific OSS path like `/contexts/{SdkCtx-123abc456def}/`
3. **Persistent Storage**: All files in this OSS directory persist beyond session lifecycles

**What happens when you bind Context to Session:**
```python
# This line tells the session: "Download OSS files to /tmp/persistent"
context_sync = ContextSync.new(context.id, "/tmp/persistent")
session = agent_bay.create(CreateSessionParams(context_syncs=[context_sync])).session
```

**Session Lifecycle with Context:**
1. **Session Start**: Downloads all files from OSS directory to `/tmp/persistent`
2. **Session Runtime**: You work with files in `/tmp/persistent` as normal local files  
3. **Session End**: Uploads all changes from `/tmp/persistent` back to OSS directory

**Visual Flow:**
```
OSS Storage          Session Environment          OSS Storage After Upload
┌─────────────┐      ┌──────────────────┐      ┌──────────────────┐
│             │ ───► │ /tmp/persistent/ │ ───► │                  │
│ SdkCtx-123/ │      │   ├── file1      │      │ SdkCtx-123/      │
│ ├── file1   │      │   ├── data       │      │ ├── file1        │
│ └── data    │      │   └── output.log │      │ ├── data         │
└─────────────┘      │   (new file)     │      │ └── output.log   │
   Download          └──────────────────┘      └──────────────────┘
   on Start                                       Upload on End
```

**What this diagram shows:**
- **Left**: Initial OSS directory with existing files (`file1`, `data`) 
- **Middle**: Session workspace with downloaded files + new files you create (`output.log`)
- **Right**: Final OSS directory with ALL changes uploaded back (modified/original files + new files)

**Key Benefits of this Architecture:**
- **Scalability**: OSS handles large files and directories efficiently
- **Reliability**: Cloud storage ensures data durability and availability
- **Performance**: Local file operations during session for fast I/O
- **Sharing**: Multiple sessions can mount the same OSS directory

### Context vs Session

| Feature | Session | Context |
|---------|---------|---------|
| Lifecycle | Temporary, destroyed when session ends | Persistent, destroyed only when manually deleted |
| Data Storage | Not saved | Permanently saved in OSS |
| Sharing | Independent, not shared | Can be shared across multiple sessions |
| Use Case | Execute temporary tasks | Store project data, configurations, etc. |
| Implementation | Local filesystem only | OSS directory + local filesystem sync |

<a id="context-management"></a>
## 📦 Context Management

### Creating and Getting Contexts

```python
from agentbay import AgentBay

# Initialize AgentBay client (requires valid API key)
#api_key from your os env
agent_bay = AgentBay(api_key=api_key)

 # Initialize AgentBay client (requires valid API key)
agent_bay = AgentBay()

# Get or create context
context_result = agent_bay.context.get("my-project", create=True)
if context_result.success:
    context = context_result.context
    print(f"Context ID: {context.id}")
    print(f"Context Name: {context.name}")
    print(f"Created At: {context.created_at}")
else:
    print(f"Context operation failed: {context_result.success}")

# Get existing context only
existing_context_result = agent_bay.context.get("my-project", create=False)
if not existing_context_result.success:
    print("Context does not exist")
else:
context = existing_context_result.context
print(f"Found context: {context.name}")
```


### Listing and Deleting Contexts

```python
# List all contexts
contexts_result = agent_bay.context.list()
if contexts_result.success:
    for context in contexts_result.contexts:
        print(f"Context: {context.name} (ID: {context.id})")
else:
    print(f"Failed to list contexts: {contexts_result.error_message}")

# Delete context
context_to_delete = agent_bay.context.get("my-project", create=False).context
if context_to_delete:
    delete_result = agent_bay.context.delete(context_to_delete)
    if delete_result.success:
        print("Context deleted successfully")
    else:
        print(f"Failed to delete context: {delete_result.error_message}")
```

### Context with Sessions

```python
from agentbay import ContextSync, CreateSessionParams

# Create context
context_result = agent_bay.context.get("my-project", create=True)
if context_result.success:
    context = context_result.context
    print(f"Context ID: {context.id}")

    # Create context sync configuration
    context_sync = ContextSync.new(
        context_id=context.id,
        path="/tmp/data"  # Mount path in session
    )

    # === Session 1: Write data ===
    print("\n--- Session 1: Writing data ---")
    params = CreateSessionParams(context_syncs=[context_sync])
    session1_result = agent_bay.create(params)
    
    if session1_result.success:
        session1 = session1_result.session
        print(f"Session 1 ID: {session1.session_id}")

        # Write files to persistent storage
        session1.file_system.write_file("/tmp/data/config.json", '{"version": "1.0", "app": "demo"}')
        session1.file_system.write_file("/tmp/data/user_data.txt", "User preferences and settings")
        print("Data written to /tmp/data/")
        
        # End session1 and ensure data is fully synced to Context
        agent_bay.delete(session1, sync_context=True)
        print("Session 1 ended - data fully synced to Context")
    else:
        print(f"Failed to create session 1: {session1_result.error_message}")

    # === Session 2: Read persisted data ===
    print("\n--- Session 2: Reading persisted data ---")
    session2_result = agent_bay.create(params)
    
    if session2_result.success:
        session2 = session2_result.session
        print(f"Session 2 ID: {session2.session_id}")

        # Read data that was persisted from session1
        config_result = session2.file_system.read_file("/tmp/data/config.json")
        user_data_result = session2.file_system.read_file("/tmp/data/user_data.txt")
        
        if config_result.success and user_data_result.success:
            print(f"✅ Config data: {config_result.content}")
            print(f"✅ User data: {user_data_result.content}")
            print("🎉 Data successfully persisted across sessions!")
        else:
            print("❌ Failed to read persisted data")
            
        # Clean up
        agent_bay.delete(session2)
        print("Session 2 ended")
    else:
        print(f"Failed to create session 2: {session2_result.error_message}")
else:
    print(f"Failed to create context: {context_result.error_message}")
```

### 🔍 Important: Session Deletion and Sync Timing

**The `sync_context` parameter is crucial for reliable persistence:**

```python
# ❌ Potential race condition - may return before upload completes
agent_bay.delete(session)

# ✅ Guaranteed sync - waits for upload completion  
agent_bay.delete(session, sync_context=True)
```

**Why this matters:**

1. **Asynchronous Upload**: When a session ends, file upload to OSS happens asynchronously
2. **Race Condition**: `delete()` returns immediately, but upload may still be in progress
3. **Data Consistency**: Creating a new session too quickly might not see the latest data

**When to use `sync_context=True`:**
- When you need to immediately create another session to access the data
- In automated workflows where timing is critical
- When data consistency across sessions is essential

**Technical Details:**
- `sync_context=True` triggers upload and polls until completion
- The SDK waits for OSS upload confirmation before returning
- This ensures the next session will definitely see all persisted data

**⚠️ Auto-upload Timeout Limitation:**

Even with auto-upload enabled in the sync policy, the backend enforces a **1-minute timeout** for automatic uploads when a session ends. This can cause issues with:

- **Large file counts**: Many files may not finish uploading within 60 seconds
- **Large file sizes**: Big files may not complete upload before timeout
- **Network latency**: Slow connections may trigger timeout

**Best Practice to Prevent Data Loss:**

```python
# Option 1: Manual sync before session ends (recommended for large datasets)
session.file_system.write_file("/tmp/data/large_file.bin", large_content)
sync_result = session.context.sync()  # Explicit sync with no timeout limit
if sync_result.success:
    print("✅ Data fully synced")
agent_bay.delete(session)  # Safe to delete now

# Option 2: Use sync_context=True on delete (recommended for standard workflows)
session.file_system.write_file("/tmp/data/config.json", config_data)
agent_bay.delete(session, sync_context=True)  # Ensures complete sync before deletion
```

**Key Differences:**

| Method | Timeout Limit | Best For | Notes |
|--------|---------------|----------|-------|
| Auto-upload only | 1 minute | Small files, quick operations | May fail silently for large datasets |
| `session.context.sync()` | None | Large files, many files | Full control, no timeout constraint |
| `delete(sync_context=True)` | None | Standard workflows | Convenient, guaranteed completion |

**Recommendation:** Always use either manual `sync()` or `delete(sync_context=True)` to ensure data persistence, especially when working with large files or multiple files.

<a id="data-synchronization-strategies"></a>
## 🔄 Data Synchronization Strategies

### Sync Policies

#### Default Synchronization Behavior

By default, AgentBay uses **automatic synchronization** when you don't specify a custom policy:

```python
from agentbay import ContextSync, CreateSessionParams

# Default behavior - no policy specified
context_sync = ContextSync.new(context.id, "/tmp/data")  # Uses default policy
session = agent_bay.create(CreateSessionParams(context_syncs=[context_sync])).session

# Equivalent to:
default_policy = SyncPolicy.default()
context_sync = ContextSync.new(context.id, "/tmp/data", default_policy)
```

**Default policy characteristics:**
- **Auto-download**: Context data is automatically downloaded when session starts
- **Auto-upload**: Local changes are automatically uploaded when session ends
- **Service-controlled intervals**: The sync timing is managed by the AgentBay service

#### When to Use Custom Sync Policies

You should consider custom sync policies in these scenarios:

1. **Manual control**: When you need precise control over when data is synced (use manual sync policy)
2. **Unidirectional sync**: When you only need upload or download (use upload-only or download-only policies)
3. **Large datasets**: When working with large files that don't need immediate sync

**Note:** Selective file synchronization based on patterns is currently not supported. Use the default policy to sync all files, or organize files into separate contexts.

#### Available Sync Policy Options

```python
from agentbay import SyncPolicy, UploadPolicy, DownloadPolicy, BWList, WhiteList

# 1. Default policy - syncs all files
default_policy = SyncPolicy(
    upload_policy=UploadPolicy(auto_upload=True),
    download_policy=DownloadPolicy(auto_download=True)
)

# 2. Manual sync - sync only when explicitly requested
manual_policy = SyncPolicy(
    upload_policy=UploadPolicy(auto_upload=False),
    download_policy=DownloadPolicy(auto_download=False)
)

# 3. Upload-only policy (for write-heavy workflows)
upload_only_policy = SyncPolicy(
    upload_policy=UploadPolicy(auto_upload=True),
    download_policy=DownloadPolicy(auto_download=False)
)

# 4. Download-only policy (for read-heavy workflows)
download_only_policy = SyncPolicy(
    upload_policy=UploadPolicy(auto_upload=False),
    download_policy=DownloadPolicy(auto_download=True)
)
```

####  Data Lifecycle Management (RecyclePolicy)

`RecyclePolicy` controls how long your context data is retained in the cloud before automatic cleanup. This is useful for managing storage costs and automatically removing temporary data.

**Key Concepts:**
- **Default Behavior**: Data is kept **FOREVER** (permanently) if no RecyclePolicy is specified
- **Automatic Cleanup**: Data is automatically deleted after the specified duration
- **Path-Specific**: Apply different lifecycles to different directories
- **No Wildcards**: Paths must be exact - wildcard patterns are not supported for safety

**Available Lifecycle Options:**

| Lifecycle | Duration | Use Case |
|-----------|----------|----------|
| `LIFECYCLE_1DAY` | 1 day | Temporary cache, test data |
| `LIFECYCLE_3DAYS` | 3 days | Short-term work files |
| `LIFECYCLE_5DAYS` | 5 days | Weekly data |
| `LIFECYCLE_10DAYS` | 10 days | Sprint data |
| `LIFECYCLE_15DAYS` | 15 days | Bi-weekly data |
| `LIFECYCLE_30DAYS` | 30 days | Monthly archives |
| `LIFECYCLE_90DAYS` | 90 days | Quarterly data |
| `LIFECYCLE_180DAYS` | 180 days | Semi-annual data |
| `LIFECYCLE_360DAYS` | 360 days | Annual archives |
| `LIFECYCLE_FOREVER` | Permanent | Important data (default) |

**Basic Usage:**

```python
from agentbay.context_sync import RecyclePolicy, Lifecycle, SyncPolicy, ContextSync

# Example 1: Keep data for 1 day
recycle_policy = RecyclePolicy(
    lifecycle=Lifecycle.LIFECYCLE_1DAY,
    paths=[""]  # "" means apply to all paths
)

sync_policy = SyncPolicy(recycle_policy=recycle_policy)
context_sync = ContextSync.new(context.id, "/tmp/cache", sync_policy)

# This creates a RecyclePolicy with:
# - lifecycle: Lifecycle_1Day
# - paths: ['']
```

**Path-Specific Cleanup:**

```python
# Example 2: Different lifespans for different directories
recycle_policy = RecyclePolicy(
    lifecycle=Lifecycle.LIFECYCLE_3DAYS,
    paths=["/tmp/cache", "/tmp/logs"]  # Only these paths
)

# Important: Use exact paths, NOT wildcards like "/tmp/*"
sync_policy = SyncPolicy(recycle_policy=recycle_policy)

# This applies the 3-day lifecycle only to /tmp/cache and /tmp/logs
```

**Important Restrictions:**

```python
# ❌ WRONG: Wildcard patterns are NOT supported
recycle_policy = RecyclePolicy(
    lifecycle=Lifecycle.LIFECYCLE_1DAY,
    paths=["/tmp/*", "/var/*.log"]  # Will raise ValueError
)
# Raises: ValueError: Wildcard patterns are not supported in recycle policy paths.
#         Got: /tmp/*. Please use exact directory paths instead.

# ✅ CORRECT: Use exact directory paths
recycle_policy = RecyclePolicy(
    lifecycle=Lifecycle.LIFECYCLE_1DAY,
    paths=["/tmp/cache", "/var/logs"]  # Exact paths only
)
# Successfully creates RecyclePolicy with exact paths
```

**When to Use RecyclePolicy:**

1. **Temporary Data**: Set short lifecycles (1-3 days) for cache, temp files, or test data
2. **Project Data**: Use medium lifecycles (30-90 days) for project files
3. **Archives**: Use long lifecycles (180-360 days) for important archives
4. **Permanent Data**: Use `LIFECYCLE_FOREVER` (default) for critical data

**Complete Example:**

```python
from agentbay import AgentBay, CreateSessionParams
from agentbay.context_sync import (
    ContextSync, SyncPolicy, RecyclePolicy, Lifecycle,
    UploadPolicy, DownloadPolicy, BWList, WhiteList
)

# Create context
context = agent_bay.context.get("my-project", create=True).context

# Create RecyclePolicy with 5 days lifecycle
recycle_policy = RecyclePolicy(
    lifecycle=Lifecycle.LIFECYCLE_5DAYS,  # Note: No LIFECYCLE_7DAYS, use 5 or 10
    paths=[""]  # Apply to all paths
)

# Create comprehensive SyncPolicy
sync_policy = SyncPolicy(
    upload_policy=UploadPolicy.default(),
    download_policy=DownloadPolicy.default(),
    recycle_policy=recycle_policy  # Add lifecycle management
)

# Create session with lifecycle-managed context
context_sync = ContextSync.new(context.id, "/tmp/data", sync_policy)
session = agent_bay.create(CreateSessionParams(context_syncs=[context_sync])).session

# The session is now configured with RecyclePolicy
# Data uploaded to this context will be automatically deleted after 5 days
```

> **Note**: RecyclePolicy applies from the time data is uploaded to the cloud. The timer starts after the session ends and data is synchronized, not when files are created in the session.

#### Selective Directory Sync

Use `bw_list` (blacklist/whitelist) to control which subdirectories within the context mount point are synced:

```python
from agentbay import BWList, WhiteList

# Example: Sync only /src and /config, exclude /src/node_modules
policy = SyncPolicy(
    upload_policy=UploadPolicy(auto_upload=True),
    download_policy=DownloadPolicy(auto_download=True),
    bw_list=BWList(
        white_lists=[
            WhiteList(
                path="/src",  # No wildcards like *.json or /src/*
                exclude_paths=["/node_modules"]  # Exact path, not patterns like *.log
            ),
            WhiteList(path="/config")
        ]
    )
)

# Mount point: use any directory with write permissions
# In linux_latest image, /home/wuying is recommended
# Whitelisted paths are relative to mount point:
# - "/src" → /home/wuying/src  
# - "/config" → /home/wuying/config
# - "/node_modules" in exclude → /home/wuying/src/node_modules
context_sync = ContextSync.new(context.id, "/home/wuying", policy)
```

**Mount Point Selection:**
- Use any directory where you have write permissions
- In `linux_latest` image: `/home/wuying`, `/tmp`, `/var/tmp` are available
- System directories like `/workspace`, `/opt`, `/usr` typically require elevated privileges

**Path Specifications:**
- `path` in WhiteList is **relative to the context mount point**
- `exclude_paths` are **relative to the whitelist path**
- Example: If mounted at `/home/wuying`, then `path="/src"` refers to `/home/wuying/src`
- Wildcard patterns (e.g., `*.json`, `/data/*`) are not supported



### Manual Synchronization

When using manual sync policies, you need to explicitly call `session.context.sync()` to trigger data synchronization:

```python
from agentbay import SyncPolicy, UploadPolicy, DownloadPolicy

agent_bay = AgentBay()
# Create session with manual sync policy
manual_policy = SyncPolicy(
    upload_policy=UploadPolicy(auto_upload=False),
    download_policy=DownloadPolicy(auto_download=False)
)
context = agent_bay.context.get("my-project", create=True).context

context_sync = ContextSync.new(context.id, "/tmp/data", manual_policy)
session_result = agent_bay.create(CreateSessionParams(context_syncs=[context_sync]))

if session_result.success:
    session = session_result.session

    # Write some data
    session.file_system.write_file("/tmp/data/temp.txt", "Temporary data")

    # Manually trigger sync to save data (synchronous call - returns when sync is complete)
    sync_result = session.context.sync()
    if sync_result.success:
        print("Data synchronized successfully")
    else:
        print(f"Sync failed: {sync_result.success}")

    # Data is now persisted even if session ends
else:
    print(f"Failed to create session: {session_result.error_message}")
```


### Bidirectional Sync

By default, `session.context.sync()` triggers file **upload** (mode="upload"). You can explicitly specify the sync direction:

```python
# Default behavior - upload local changes to OSS (mode="upload" is default)
upload_result = session.context.sync()  # Same as sync(mode="upload")
if upload_result.success:
    print("Local changes uploaded to context")
else:
    print(f"Upload failed: {upload_result.error_message}")

# Explicitly download latest data from OSS to session
download_result = session.context.sync(mode="download")
if download_result.success:
    print("Latest data downloaded from context")
else:
    print(f"Download failed: {download_result.error_message}")

# Explicitly upload local changes to OSS
upload_result = session.context.sync(mode="upload")
if upload_result.success:
    print("Local changes uploaded to context")
else:
    print(f"Upload failed: {upload_result.error_message}")
```

<a id="troubleshooting"></a>
## 🔧 Troubleshooting

### Issue 1: Permission Denied When Creating Files

**Error Message:**
```
Permission denied
Failed to create directory: /workspace, error: Permission denied
```

**Cause:** Mount point directory lacks write permissions for the current user.

**Solution:**
```python
# ❌ Wrong: Using directory without write permission
context_sync = ContextSync.new(context.id, "/workspace", policy)
context_sync = ContextSync.new(context.id, "/opt/myapp", policy)

# ✅ Correct: Use directory with write permission
context_sync = ContextSync.new(context.id, "/home/wuying", policy)
context_sync = ContextSync.new(context.id, "/tmp/myapp", policy)
```

**Available directories in `linux_latest` image:** `/home/wuying`, `/tmp`, `/var/tmp`

### Issue 2: Files Not Persisted (WhiteList Path Error)

**Symptom:** Files created in session are not found in the next session, even though sync completed.

**Cause:** WhiteList paths are treated as absolute instead of relative to mount point.

**Example of the error:**
```python
# ❌ Wrong: This looks for /home/wuying/home/wuying/src (doesn't exist)
policy = SyncPolicy(
    bw_list=BWList(
        white_lists=[WhiteList(path="/home/wuying/src")]
    )
)
context_sync = ContextSync.new(context.id, "/home/wuying", policy)
```

**Solution:**
```python
# ✅ Correct: Paths are relative to mount point
policy = SyncPolicy(
    bw_list=BWList(
        white_lists=[WhiteList(path="/src")]  # → /home/wuying/src
    )
)
context_sync = ContextSync.new(context.id, "/home/wuying", policy)
```

### Issue 3: Wildcard Patterns Not Supported

**Symptom:** Files are not persisted even though sync completes successfully. No error is reported.

**Cause:** Using wildcard patterns (`*`, `**`) in WhiteList paths or exclude_paths.

**Example of the error:**
```python
# ❌ Wrong: Wildcards silently fail
policy = SyncPolicy(
    bw_list=BWList(
        white_lists=[
            WhiteList(path="*.json"),           # No files synced
            WhiteList(path="/data/*"),          # No files synced
            WhiteList(path="/logs/**/*.txt"),   # No files synced
            WhiteList(path="/src", exclude_paths=["*.log"])  # No files synced
        ]
    )
)
```

**Solution:**
```python
# ✅ Correct: Use exact directory paths
policy = SyncPolicy(
    bw_list=BWList(
        white_lists=[
            WhiteList(path="/data"),  # Syncs all files in /data
            WhiteList(path="/src", exclude_paths=["/temp"])  # Syncs /src except /src/temp
        ]
    )
)
```

### Issue 4: Data Loss After Session Deletion

**Symptom:** Files written in session are not available in the next session.

**Cause:** Session deleted before sync upload completes.

**Solution:**
```python
# ❌ Wrong: May delete before upload finishes
session.file_system.write_file("/home/wuying/data.txt", "content")
agent_bay.delete(session)

# ✅ Correct: Wait for sync to complete
session.file_system.write_file("/home/wuying/data.txt", "content")
agent_bay.delete(session, sync_context=True)
```

### Issue 5: Understanding RecyclePolicy and Data Retention

**Question:** When will my context data be deleted?

**Answer:**
- **Default**: Data is kept **FOREVER** unless you specify a RecyclePolicy
- **With RecyclePolicy**: Data is automatically deleted after the specified period from upload time
- **Timer Start**: The lifecycle countdown begins when data is uploaded to the cloud (after session ends and sync completes)

**Example:**
```python
# Scenario: Set 1 day lifecycle
recycle_policy = RecyclePolicy(
    lifecycle=Lifecycle.LIFECYCLE_1DAY,
    paths=[""]
)

# Timeline:
# Day 0, 10:00 AM - Session created, files written
# Day 0, 11:00 AM - Session deleted, sync uploads data to cloud
# Day 0, 11:00 AM - Lifecycle timer starts
# Day 1, 11:00 AM - Data automatically deleted (24 hours after upload)
```

**Common Mistakes:**

```python
# ❌ Wrong: Using wildcards in paths
recycle_policy = RecyclePolicy(
    lifecycle=Lifecycle.LIFECYCLE_1DAY,
    paths=["/tmp/*", "/var/*.log"]  # ValueError: wildcards not supported
)

# ✅ Correct: Use exact directory paths
recycle_policy = RecyclePolicy(
    lifecycle=Lifecycle.LIFECYCLE_1DAY,
    paths=["/tmp/cache", "/var/logs"]  # Exact paths only
)
```

**Choosing the Right Lifecycle:**
- **Temporary cache/test data**: `LIFECYCLE_1DAY` or `LIFECYCLE_3DAYS`
- **Development work**: `LIFECYCLE_5DAYS` to `LIFECYCLE_15DAYS`
- **Project archives**: `LIFECYCLE_30DAYS` to `LIFECYCLE_90DAYS`
- **Important data**: `LIFECYCLE_FOREVER` (default)

### Verifying Sync Status

```python
context_info = session.context.info()

if context_info.context_status_data:
    for status in context_info.context_status_data:
        print(f"Context: {status.context_id}")
        print(f"Path: {status.path}")
        print(f"Status: {status.status}")
        if status.error_message:
            print(f"Error: {status.error_message}")
else:
    print("No sync tasks found")
```



## 📚 Related Guides

- [Session Management](session-management.md) - Session lifecycle and configuration
- [File Operations](file-operations.md) - File handling and management
- [OSS Integration](../advanced/oss-integration.md) - Object storage service integration

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../README.md)
