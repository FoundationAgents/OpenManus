# Session Management Documentation

This document provides comprehensive guidance on using the session management capabilities of the AgentBay SDK across all supported languages.

## Overview

Sessions are the fundamental unit of interaction with the AgentBay cloud environment. Each session represents an isolated cloud environment where you can execute commands, manipulate files, run applications, and perform automation tasks.

The session management system provides:
1. **Session Creation**: Create isolated cloud environments with customizable image types and parameters
2. **Session Information**: Access session details including direct browser URLs and connection credentials
3. **Label Management**: Organize and categorize sessions using descriptive labels
4. **Session Recovery**: Restore session objects using session IDs for continued operations
5. **Session Deletion**: Clean up sessions to free cloud resources

## Getting Started

### Prerequisites

Before running the example programs in this guide, please ensure you have completed the following setup:

**Required Setup (2 minutes):**
1. **SDK Installation & API Key Configuration**: Follow the [Installation and API Key Setup Guide](../../../quickstart/installation.md) to install the AgentBay SDK and configure your API key
2. **SDK Configuration**: Review the [SDK Configuration Guide](../configuration/sdk-configuration.md) for detailed configuration options including environment variables and API gateway selection
3. **Core Concepts**: Review [Core Concepts Guide](../../../quickstart/basic-concepts.md) to understand AgentBay fundamentals including sessions, images, and data persistence

**Quick Verification:**
After setup, verify everything works with this simple test:
```python
import os
from agentbay import AgentBay

api_key = os.getenv("AGENTBAY_API_KEY")
agent_bay = AgentBay(api_key=api_key)
result = agent_bay.create()
if result.success:
    print("✅ Setup successful - ready to use session management!")
    agent_bay.delete(result.session)
else:
    print(f"❌ Setup issue: {result.error_message}")
```

### Creating a Session

Creating a session is the first step in using the AgentBay SDK:

```python
from agentbay import AgentBay

# Initialize the SDK
agent_bay = AgentBay(api_key=api_key)

# Create a session with default parameters
session_result = agent_bay.create()
if session_result.success:
    session = session_result.session
    print(f"Session created with ID: {session.session_id}")
```

## Creating Sessions with Custom Parameters

You can customize sessions by specifying parameters such as [image ID](../../../quickstart/basic-concepts.md#-image-types---four-main-environments) and [labels](#session-label-management):

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

# Initialize the SDK
agent_bay = AgentBay(api_key="your_api_key")

# Create a session with custom parameters
params = CreateSessionParams(
    image_id="linux_latest",
    labels={"project": "demo", "environment": "testing"}
)
session_result = agent_bay.create(params)
session = session_result.session

if session_result.success:
    session = session_result.session
    print(f"Session created with ID: {session.session_id}")
```



## Session Label Management

Labels help organize and categorize sessions for easier management:

### Setting Session Labels

```python
from agentbay import AgentBay

# Initialize the SDK and create a session
agent_bay = AgentBay(api_key=api_key)
session_result = agent_bay.create()
session = session_result.session

# Set labels
labels = {"project": "demo", "environment": "testing"}
result = session.set_labels(labels)

if result.success:
    print("Labels set successfully")
else:
    print(f"Failed to set labels: {result.error_message}")
```

### Getting Session Labels

```python
from agentbay import AgentBay

# Initialize the SDK and create a session
agent_bay = AgentBay(api_key=api_key)
session_result = agent_bay.create()
session = session_result.session

# Get labels
result = session.get_labels()

if result.success:
    print("Session labels:")
    for key, value in result.data.items():
        print(f"  {key}: {value}")
else:
    print(f"Failed to get labels: {result.error_message}")
```

## Listing Sessions

The `list()` method allows you to query and retrieve session IDs from your AgentBay account. This is useful for managing multiple sessions, monitoring active environments, and organizing your cloud resources.

### Basic Usage

```python
from agentbay import AgentBay

# Initialize the SDK
agent_bay = AgentBay(api_key=api_key)

# List all active sessions
result = agent_bay.list()

if result.success:
    print(f"Found {result.total_count} total sessions")
    print(f"Showing {len(result.session_ids)} session IDs on this page")
    print(f"Request ID: {result.request_id}")

    for session_id in result.session_ids:
        print(f"Session ID: {session_id}")
else:
    print(f"Failed to list sessions: {result.error_message}")

# Output:
# Found 0 total sessions
# Showing 0 session IDs on this page
# Request ID: 6620****-****-****-****-********C2C1
```

### Filtering by Labels

You can filter sessions by labels to find specific environments:

```python
from agentbay import AgentBay

# Initialize the SDK
agent_bay = AgentBay(api_key=api_key)

# List sessions with specific labels
result = agent_bay.list(labels={"project": "demo", "environment": "testing"})

if result.success:
    print(f"Found {len(result.session_ids)} sessions matching the labels")
    for session_id in result.session_ids:
        print(f"Session ID: {session_id}")

# Output (after creating a session with matching labels):
# Found 1 sessions matching the labels
# Session ID: session-**********************sic
```

### Pagination

For accounts with many sessions, use pagination to retrieve results in manageable chunks:

```python
from agentbay import AgentBay

# Initialize the SDK
agent_bay = AgentBay(api_key=api_key)

# Get page 2 with 10 items per page
result = agent_bay.list(labels={"project": "demo"}, page=2, limit=10)

if result.success:
    print(f"Page 2 of results (showing {len(result.session_ids)} sessions)")
    print(f"Total sessions: {result.total_count}")
    print(f"Next page token: {result.next_token}")

# Output (when there are no sessions on page 2):
# Page 2 of results (showing 0 sessions)
# Total sessions: 0
# Next page token: None
```

### Important Notes

**Active Sessions Only:**
- The `list()` method **only returns currently active sessions**
- Sessions that have been deleted or released (either manually via `delete()` or automatically due to timeout) will **not** be included in the results
- To check if a specific session is still active, use the `get()` method or `session.info()` method

**Return Value:**
- The method returns session IDs (strings) rather than full Session objects
- Use `agent_bay.get(session_id)` to retrieve a full Session object if needed

**Key Features:**
- **Flexible Filtering**: List all sessions or filter by any combination of labels
- **Pagination Support**: Use `page` and `limit` parameters for easy pagination
- **Request ID**: All responses include a `request_id` for tracking and debugging
- **Efficient**: Returns only session IDs for better performance

## Getting Session Information

The `info()` method provides detailed information about a session, including direct browser access URLs and SDK integration credentials. This API serves two primary purposes:

1. **Cloud Environment Access**: Get the `resource_url` to directly access the cloud environment in a web browser with real-time video streaming and full mouse/keyboard control
2. **Session Status Validation**: Check if a session is still active and hasn't been released
3. **SDK Integration**: Extract authentication credentials for Web SDK (desktop) and Android SDK (mobile) integration

### Session Information Retrieval

```python
from agentbay import AgentBay

# Initialize the SDK and create a session
agent_bay = AgentBay(api_key=api_key)
session_result = agent_bay.create()
session = session_result.session

# Get session information
info_result = session.info()

if info_result.success:
    info = info_result.data
    print(f"Session ID: {info.session_id}")
    print(f"Resource ID: {info.resource_id}")
    print(f"Resource URL: {info.resource_url}")
    print(f"App ID: {info.app_id}")
    print(f"Resource Type: {info.resource_type}")
    print(f"Request ID: {info_result.request_id}")

    # Authentication info (displayed safely)
    print(f"Auth Code: {info.auth_code[:8]}***{info.auth_code[-8:]}")
    print(f"Connection Properties: {len(info.connection_properties)} chars")
    print(f"Ticket: {info.ticket[:50]}...")

    # The resource_url can be opened in a browser for direct access
    print("\n🌐 Open the resource_url in your browser to access the cloud environment!")
else:
    print(f"Failed to get session info: {info_result.error_message}")
```

### Session Information Field Details

- **session_id**: Unique identifier for the session
- **resource_id**: Cloud resource identifier (e.g., "p-xxxxxxxxx")
- **resource_url**: **Direct browser access URL** - Open this URL in any web browser to access the cloud environment with real-time video stream and full mouse/keyboard control
- **app_id**: Application type identifier
- **resource_type**: Resource classification (typically "AIAgent")
- **auth_code**: Authentication token required for Web SDK and Android SDK integration
- **connection_properties**: JSON configuration for SDK connection settings
- **ticket**: Gateway access ticket containing connection endpoints and tokens for SDK integration

### Session Information Use Cases

For detailed practical examples and use cases of session information, including browser access, Android SDK integration, and session health monitoring, see the [Session Information Use Cases Guide](../use-cases/session-info-use-cases.md).



## Session Release

Sessions consume cloud resources while active. Understanding how sessions are released is crucial for resource management.

### Two Ways to Release Sessions

**1. Manual Release (Recommended)**

Explicitly delete sessions when you're done:

```python
from agentbay import AgentBay

# Initialize the SDK and create a session
agent_bay = AgentBay(api_key=api_key)
session_result = agent_bay.create()
session = session_result.session

# Perform your tasks...

# Release resources immediately
delete_result = agent_bay.delete(session)
if delete_result.success:
    print("Session deleted successfully")
else:
    print(f"Failed to delete session: {delete_result.error_message}")
```

**2. Automatic Timeout Release**

If you don't manually delete a session, it will be automatically released after a configured timeout period:

- **Configuration**: Timeout duration is set in the [AgentBay Console](https://agentbay.console.aliyun.com/)
- **Behavior**: Once the timeout is reached, the session is automatically released
- **Recovery**: After release (manual or automatic), the session cannot be recovered - the session ID becomes invalid

### Important Notes

- Released sessions (either manually or by timeout) will **not** appear in `agent_bay.list()` results
- Once released, all non-persistent data in the session is permanently lost
- Use [Data Persistence](data-persistence.md) to preserve important data across sessions


## Session Recovery

In certain scenarios, you may need to recover a Session object using its session ID. The SDK provides the `get` method to retrieve an existing session.

### Using the get Method

The `get` method is the recommended way to recover a session. It retrieves session information from the cloud and returns a ready-to-use Session object with the API request ID.

```python
from agentbay import AgentBay

# Initialize the SDK
agent_bay = AgentBay(api_key="your_api_key")

# Retrieve session using its ID
session_id = "your_existing_session_id"
get_result = agent_bay.get(session_id)

if get_result.success:
    session = get_result.session
    print(f"Retrieved session: {session.session_id}")
    print(f"Request ID: {get_result.request_id}")
    
    # You can now perform any session operations
    result = session.command.execute_command("echo 'Hello, World!'")
    print(result.output)
else:
    print(f"Failed to get session: {get_result.error_message}")

# Output (when session exists):
# Retrieved session: session-**********************uhi
# Request ID: B27C****-****-****-****-********0366
# Command output: Hello, World!

# Output (when session is deleted or not found):
# Failed to get session: Failed to get session session-**********************uhi: Failed to get session session-**********************uhi: Error: InvalidMcpSession.NotFound code: 400,   Resource [McpSession] is not found. request id: 1C3C****-****-****-****-********AD3F ...
```


### Important Considerations

**Session Recovery Limitations:**

1. **Released Sessions Cannot Be Recovered**: If the session ID corresponds to a cloud environment that has been actually released (either through active deletion via `Session.delete()` or automatic timeout release), it cannot be recovered using the session ID. In such cases, you must:
   - Create a new session
   - Use data persistence (see [Data Persistence Guide](data-persistence.md)) to restore your data

2. **Session Status Validation**: Use the `Session.info()` method to determine if a session has been released. Only active (non-released) sessions can return information through the info interface.

3. **Automatic Release Timeout**: Session automatic release timeout can be configured in the [console page](https://agentbay.console.aliyun.com/).

## Advanced Session Patterns

### Error-Safe Session Creation

Create sessions with comprehensive error handling:

```python
import os
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

def create_session_safely(image_id="linux_latest"):
    agent_bay = AgentBay(api_key=os.getenv("AGENTBAY_API_KEY"))
    
    params = CreateSessionParams(image_id=image_id) if image_id != "linux_latest" else None
    result = agent_bay.create(params)
    
    if result.success:
        print(f"✅ Session created: {result.session.session_id}")
        return result.session, agent_bay
    else:
        print(f"❌ Failed: {result.error_message}")
        return None, None

session, client = create_session_safely("browser_latest")
if session:
    client.delete(session)
```

### Context Manager Pattern

Implement automatic cleanup using Python's context manager protocol:

```python
import os
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

class SessionManager:
    def __init__(self, image_id="linux_latest"):
        self.agent_bay = AgentBay(api_key=os.getenv("AGENTBAY_API_KEY"))
        self.image_id = image_id
        self.session = None
    
    def __enter__(self):
        params = CreateSessionParams(image_id=self.image_id) if self.image_id != "linux_latest" else None
        result = self.agent_bay.create(params)
        if result.success:
            self.session = result.session
            return self.session
        else:
            raise Exception(f"Session creation failed: {result.error_message}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.agent_bay.delete(self.session)
            print("🧹 Session automatically cleaned up")

try:
    with SessionManager("code_latest") as session:
        result = session.command.execute_command("echo 'Automatic cleanup!'")
        print(f"Output: {result.output}")
except Exception as e:
    print(f"Error: {e}")
```

## API Reference

For detailed API documentation, see:
- [Python Session API](../../../../python/docs/api/session.md)
- [TypeScript Session API](../../../../typescript/docs/api/session.md)
- [Golang Session API](../../../../golang/docs/api/session.md)
- [Python AgentBay API](../../../../python/docs/api/agentbay.md)
- [TypeScript AgentBay API](../../../../typescript/docs/api/agentbay.md)
- [Golang AgentBay API](../../../../golang/docs/api/agentbay.md)

## 📚 Related Guides

- [Data Persistence](data-persistence.md) - Persistent data storage across sessions
- [File Operations](file-operations.md) - File handling and management
- [Command Execution](command-execution.md) - Execute shell commands
- [VPC Sessions](../advanced/vpc-sessions.md) - Isolated network environments

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../README.md)
