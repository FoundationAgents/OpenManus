# Session Class

The `Session` class represents a session in the AgentBay cloud environment. It provides methods for managing file systems, executing commands, and more.

## 📖 Related Tutorial

- [Session Management Guide](../../../docs/guides/common-features/basics/session-management.md) - Detailed tutorial on session lifecycle and management

## Properties

```python
agent_bay  # The AgentBay instance that created this session
session_id  # The ID of this session
file_system  # The FileSystem instance for this session
command  # The Command instance for this session
code  # The Code instance for this session
oss  # The Oss instance for this session
application  # The ApplicationManager instance for this session
window  # The WindowManager instance for this session
ui  # The UI instance for this session
context  # The ContextManager instance for this session
browser  # The Browser instance for this session
agent  # The Agent instance for this session
is_vpc  # Whether this session uses VPC resources
network_interface_ip  # Network interface IP for VPC sessions
http_port  # HTTP port for VPC sessions
mcp_tools  # MCP tools available for this session
image_id  # The image ID used for this session
extra_configs  # ExtraConfigs used when creating this session
```

## Methods

### delete

Deletes this session.

```python
delete(sync_context: bool = False) -> DeleteResult
```

**Parameters:**
- `sync_context` (bool, optional): If True, the API will trigger a file upload via `self.context.sync` before actually releasing the session. Default is False.

**Returns:**
- `DeleteResult`: A result object containing success status, request ID, and error message if any.

**Behavior:**
- When `sync_context` is True, the API will first call `context.sync` to trigger file upload.
- It will then retrieve ContextStatusData via `context.info` and monitor only upload task items' Status.
- The API waits until all upload tasks show either "Success" or "Failed" status, or until the maximum retry limit (150 times with 2-second intervals) is reached.
- Any "Failed" status upload tasks will have their error messages printed.
- The session deletion only proceeds after context sync status checking for upload tasks completes.

**Example:**
```python
from agentbay import AgentBay

# Initialize the SDK
agent_bay = AgentBay(api_key="your_api_key")

# Create a session
result = agent_bay.create()
if result.success:
    session = result.session
    print(f"Session created with ID: {session.session_id}")
    # Output: Session created with ID: session-04bdwfj7u22a1s30g

    # Use the session...

    # Delete the session with context synchronization
    delete_result = session.delete(sync_context=True)
    if delete_result.success:
        print(f"Session deleted successfully with synchronized context")
        # Output: Session deleted successfully with synchronized context
        print(f"Request ID: {delete_result.request_id}")
        # Output: Request ID: D9E69976-9DE0-107D-8047-EE4B4D63AA5D
    else:
        print(f"Failed to delete session: {delete_result.error_message}")
```

### set_labels

Sets labels for this session.

```python
set_labels(labels: Dict[str, str]) -> OperationResult
```

**Parameters:**
- `labels` (Dict[str, str]): Key-value pairs representing the labels to set.

**Returns:**
- `OperationResult`: A result object containing success status, request ID, and error message if any.

**Raises:**
- `AgentBayError`: If setting labels fails due to API errors or other issues.

**Example:**
```python
# Set session labels
labels = {
    "project": "demo",
    "environment": "testing",
    "version": "1.0.0"
}
result = session.set_labels(labels)
if result.success:
    print("Labels set successfully")
    # Output: Labels set successfully
    print(f"Request ID: {result.request_id}")
    # Output: Request ID: B1F98082-52F0-17F7-A149-7722D6205AD6
else:
    print(f"Failed to set labels: {result.error_message}")
```

### get_labels

Gets the labels for this session.

```python
get_labels() -> OperationResult
```

**Returns:**
- `OperationResult`: A result object containing success status, request ID, and error message if any, and the labels data.

**Raises:**
- `AgentBayError`: If getting labels fails due to API errors or other issues.

**Example:**
```python
# Get session labels
try:
    result = session.get_labels()
    if result.success:
        print(f"Session labels: {result.data}")
        # Output: Session labels: {'environment': 'testing', 'project': 'demo', 'version': '1.0.0'}
    else:
        print(f"Failed to get labels: {result.error_message}")
except AgentBayError as e:
    print(f"Failed to get labels: {e}")
```

### info

Gets information about this session.

```python
info() -> OperationResult
```

**Returns:**
- `OperationResult`: A result object containing success status, request ID, and the session information as data.

**Raises:**
- `AgentBayError`: If getting session information fails due to API errors or other issues.

**Example:**
```python
# Get session information
try:
    result = session.info()
    if result.success:
        info = result.data
        print(f"Session ID: {info.session_id}")
        # Output: Session ID: session-04bdwfj7u22a1s30k
        print(f"Resource URL: {info.resource_url[:80]}...")
        # Output: Resource URL: https://pre-myspace-wuying.aliyun.com/app/InnoArchClub/mcp_container/mcp.html?au...
        print(f"App ID: {info.app_id}")
        # Output: App ID: mcp-server-ubuntu
    else:
        print(f"Failed to get session info: {result.error_message}")
except AgentBayError as e:
    print(f"Failed to get session info: {e}")
```

### get_link

Gets a link for this session.

```python
get_link(protocol_type: Optional[str] = None, port: Optional[int] = None) -> OperationResult
```

**Parameters:**
- `protocol_type` (str, optional): The protocol type for the link.
- `port` (int, optional): The port for the link. Must be an integer in the range [30100, 30199]. If not specified, the default port will be used.

**Returns:**
- `OperationResult`: A result object containing success status, request ID, and the link URL as data.

**Raises:**
- `SessionError`: If the port value is invalid (not an integer or outside the valid range [30100, 30199]).
- `AgentBayError`: If getting the link fails due to API errors or other issues.

**Example:**
```python
# Get link with specific protocol and valid port
# Note: For ComputerUse images, port must be explicitly specified
try:
    result = session.get_link("https", 30150)
    if result.success:
        link = result.data
        print(f"Session link: {link[:80]}...")
        # Output: Session link: https://gw-cn-hangzhou-i-ai-test0-linux.wuyinggw.com:8008/request_ai/00Lw4a5HtJ9...
        print(f"Request ID: {result.request_id}")
        # Output: Request ID: 5CA891B8-1E45-13B0-9975-0258228008CB
    else:
        print(f"Failed to get link: {result.error_message}")

    # Example with invalid port (will raise SessionError)
    try:
        invalid_result = session.get_link(port=8080)  # Invalid: outside [30100, 30199]
    except SessionError as e:
        print(f"Port validation error: {e}")
        # Output: Port validation error: Invalid port value: 8080. Port must be an integer in the range [30100, 30199].

except AgentBayError as e:
    print(f"Failed to get link: {e}")
```

### get_link_async

Asynchronously gets a link for this session.

```python
async get_link_async(protocol_type: Optional[str] = None, port: Optional[int] = None) -> OperationResult
```

**Parameters:**
- `protocol_type` (str, optional): The protocol type for the link.
- `port` (int, optional): The port for the link. Must be an integer in the range [30100, 30199]. If not specified, the default port will be used.

**Returns:**
- `OperationResult`: A result object containing success status, request ID, and the link URL as data.

**Raises:**
- `SessionError`: If the port value is invalid (not an integer or outside the valid range [30100, 30199]).
- `AgentBayError`: If getting the link fails due to API errors or other issues.

**Example:**
```python
import asyncio

async def get_session_link():
    try:
        # Get session link with default settings
        result = await session.get_link_async()
        if result.success:
            link = result.data
            print(f"Session link: {link}")
        else:
            print(f"Failed to get link: {result.error_message}")

        # Get link with specific protocol and valid port
        custom_result = await session.get_link_async("wss", 30199)
        if custom_result.success:
            custom_link = custom_result.data
            print(f"Custom WebSocket link: {custom_link}")
        else:
            print(f"Failed to get custom link: {custom_result.error_message}")

    except SessionError as e:
        print(f"Port validation error: {e}")
    except AgentBayError as e:
        print(f"Failed to get link: {e}")

# Run the async function
asyncio.run(get_session_link())
```

### list_mcp_tools

Lists MCP tools available for this session.

```python
list_mcp_tools(image_id: Optional[str] = None) -> McpToolsResult
```

**Parameters:**
- `image_id` (str, optional): The image ID to list tools for. Defaults to the session's image_id or "linux_latest".

**Returns:**
- `McpToolsResult`: A result object containing success status, request ID, and the list of MCP tools.

**Raises:**
- `AgentBayError`: If listing MCP tools fails due to API errors or other issues.

## Related Resources

- [FileSystem API Reference](filesystem.md)
- [Command API Reference](command.md)
- [UI API Reference](ui.md)
- [Window API Reference](window.md)
- [OSS API Reference](oss.md)
- [Application API Reference](application.md)
- [Context API Reference](context-manager.md)
