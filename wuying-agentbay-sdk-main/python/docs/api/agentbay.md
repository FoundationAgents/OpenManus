# AgentBay Class API Reference

The `AgentBay` class is the main entry point for interacting with the AgentBay cloud environment. It provides methods for creating, retrieving, listing, and deleting sessions.

## 📖 Related Tutorials

- [SDK Configuration Guide](../../../docs/guides/common-features/configuration/sdk-configuration.md) - Detailed tutorial on configuring the SDK
- [VPC Sessions Guide](../../../docs/guides/common-features/advanced/vpc-sessions.md) - Tutorial on creating sessions in VPC environments
- [Session Link Access Guide](../../../docs/guides/common-features/advanced/session-link-access.md) - Tutorial on accessing sessions via links

## Constructor

### AgentBay

```python
AgentBay(api_key=None, cfg=None)
```

**Parameters:**
- `api_key` (str, optional): The API key for authentication. If not provided, the SDK will look for the `AGENTBAY_API_KEY` environment variable.
- `cfg` (Config, optional): Configuration object containing endpoint and timeout_ms. If not provided, default configuration is used.

**Raises:**
- `ValueError`: If no API key is provided and `AGENTBAY_API_KEY` environment variable is not set.

## Properties

###

```python
context
```
A `ContextService` instance for managing persistent contexts. See the [Context API Reference](context.md) for more details.

## Methods

Creates a new session in the AgentBay cloud environment.

```python
create(params: Optional[CreateSessionParams] = None) -> SessionResult
```

**Parameters:**
- `params` (CreateSessionParams, optional): Parameters for session creation. If None, default parameters will be used.

**Returns:**
- `SessionResult`: A result object containing the new Session instance, success status, request ID, and error message if any.

**Behavior:**
- When `params` includes valid `persistence_data_list`, after creating the session, the API will internally wait for context synchronization to complete.
- It will retrieve ContextStatusData via `session.context.info` and continuously monitor all data items' Status until all items show either "Success" or "Failed" status, or until the maximum retry limit (150 times with 2-second intervals) is reached.
- Any "Failed" status items will have their error messages printed.
- The create operation only returns after context status checking completes.

**Raises:**
- `AgentBayError`: If the session creation fails due to API errors or other issues.

**Example:**
```python
from agentbay import AgentBay, Config
from agentbay.session_params import CreateSessionParams
from agentbay.context_sync import ContextSync, SyncPolicy

# Initialize the SDK with default configuration
agent_bay = AgentBay(api_key="your_api_key")

# Or initialize with custom configuration
config = Config(
    endpoint="https://agentbay.example.com",
    timeout_ms=30000
)
agent_bay_with_config = AgentBay(api_key="your_api_key", cfg=config)

# Create a session with default parameters
default_result = agent_bay.create()
if default_result.success:
    default_session = default_result.session
    print(f"Created session with ID: {default_session.session_id}")

# Create a session with custom parameters
params = CreateSessionParams(
    image_id="linux_latest",
    labels={"project": "demo", "environment": "testing"},
    enable_browser_replay=True  # Enable browser replay for browser sessions
)
custom_result = agent_bay.create(params)
if custom_result.success:
    custom_session = custom_result.session
    print(f"Created custom session with ID: {custom_session.session_id}")

# Create a session with context synchronization
context_sync = ContextSync.new(
    context_id="your_context_id",
    path="/mnt/persistent",
    policy=SyncPolicy.default()
)
sync_params = CreateSessionParams(
    image_id="linux_latest",
    context_syncs=[context_sync]
)
sync_result = agent_bay.create(sync_params)
if sync_result.success:
    sync_session = sync_result.session
    print(f"Created session with context sync: {sync_session.session_id}")

# Create a browser session with browser replay enabled
browser_params = CreateSessionParams(
    image_id="browser_latest",
    enable_browser_replay=True,  # Enable browser replay
)
browser_result = agent_bay.create(browser_params)
if browser_result.success:
    browser_session = browser_result.session
    print(f"Created browser session with replay: {browser_session.session_id}")
    # Browser replay files are automatically generated for internal processing

# Create a mobile session with whitelist configuration
from agentbay.api.models import ExtraConfigs, MobileExtraConfig, AppManagerRule

app_whitelist_rule = AppManagerRule(
    rule_type="White",
    app_package_name_list=[
        "com.android.settings",
        "com.example.trusted.app",
        "com.system.essential.service"
    ]
)
mobile_config = MobileExtraConfig(
    lock_resolution=True,  # Lock screen resolution for consistent testing
    app_manager_rule=app_whitelist_rule
)
extra_configs = ExtraConfigs(mobile=mobile_config)

mobile_params = CreateSessionParams(
    image_id="mobile_latest",
    labels={"project": "mobile-testing", "config_type": "whitelist"},
    extra_configs=extra_configs
)
mobile_result = agent_bay.create(mobile_params)
if mobile_result.success:
    mobile_session = mobile_result.session
    print(f"Created mobile session with whitelist: {mobile_session.session_id}")

# Create a mobile session with blacklist configuration
app_blacklist_rule = AppManagerRule(
    rule_type="Black",
    app_package_name_list=[
        "com.malware.suspicious",
        "com.unwanted.adware",
        "com.social.distraction"
    ]
)
mobile_security_config = MobileExtraConfig(
    lock_resolution=False,  # Allow adaptive resolution
    app_manager_rule=app_blacklist_rule
)
security_extra_configs = ExtraConfigs(mobile=mobile_security_config)

mobile_security_params = CreateSessionParams(
    image_id="mobile_latest",
    labels={"project": "mobile-security", "config_type": "blacklist", "security": "enabled"},
    extra_configs=security_extra_configs
)
security_result = agent_bay.create(mobile_security_params)
if security_result.success:
    security_session = security_result.session
    print(f"Created secure mobile session with blacklist: {security_session.session_id}")
```

### get

Retrieves a session by its ID.

```python
get(session_id: str) -> SessionResult
```

**Parameters:**
- `session_id` (str): The ID of the session to retrieve.

**Returns:**
- `SessionResult`: A result object containing the Session instance, request ID, success status, and error message if any.

**Example:**
```python
from agentbay import AgentBay

agentbay = AgentBay(api_key="your_api_key")

create_result = agentbay.create()
if not create_result.success:
    print(f"Failed to create session: {create_result.error_message}")
    exit(1)

session_id = create_result.session.session_id
print(f"Created session with ID: {session_id}")
# Output: Created session with ID: session-xxxxxxxxxxxxxx

result = agentbay.get(session_id)
if result.success:
    print(f"Successfully retrieved session: {result.session.session_id}")
    # Output: Successfully retrieved session: session-xxxxxxxxxxxxxx
    print(f"Request ID: {result.request_id}")
    # Output: Request ID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
    
    delete_result = result.session.delete()
    if delete_result.success:
        print(f"Session {session_id} deleted successfully")
        # Output: Session session-xxxxxxxxxxxxxx deleted successfully
else:
    print(f"Failed to get session: {result.error_message}")
```



```python
list_by_labels(params: Optional[Union[ListSessionParams, Dict[str, str]]] = None) -> SessionListResult
```

**Parameters:**
- `params` (ListSessionParams or Dict[str, str], optional): Parameters for filtering sessions by labels. If a dictionary is provided, it will be treated as labels. If None, all sessions will be returned.

**Returns:**
- `SessionListResult`: A result object containing the filtered sessions, pagination information, and request ID.

**Raises:**
- `AgentBayError`: If the session listing fails.

**Example:**
```python
from agentbay import AgentBay
from agentbay.session_params import ListSessionParams

# Initialize the SDK
agent_bay = AgentBay(api_key="your_api_key")

# Create pagination parameters
params = ListSessionParams(
    max_results=10,  # Maximum results per page
    next_token="",   # Token for the next page, empty for the first page
    labels={"environment": "production", "project": "demo"}  # Filter labels
)

# Get the first page of results
result = agent_bay.list_by_labels(params)

# Process the results
if result.success:
    # Print the current page sessions
    for session in result.sessions:
        print(f"Session ID: {session.session_id}")

    # Print pagination information
    print(f"Total count: {result.total_count}")
    print(f"Max results per page: {result.max_results}")
    print(f"Next token: {result.next_token}")

    # If there is a next page, retrieve it
    if result.next_token:
        params.next_token = result.next_token
        next_page_result = agent_bay.list_by_labels(params)
        # Process the next page...
```

### list

Returns paginated list of Sessions filtered by labels.

```python
list(labels: Optional[Dict[str, str]] = None, page: Optional[int] = None, limit: Optional[int] = None) -> SessionListResult
```

**Parameters:**
- `labels` (Optional[Dict[str, str]], optional): Labels to filter Sessions. Defaults to None (empty dict, returns all sessions).
- `page` (Optional[int], optional): Page number for pagination (starting from 1). Defaults to None (returns first page).
- `limit` (Optional[int], optional): Maximum number of items per page. Defaults to None (uses default of 10).

**Returns:**
- `SessionListResult`: Paginated list of session IDs that match the labels, including request_id, success status, and pagination information.

**Key Features:**
- **Simple Interface**: Pass labels directly as a dictionary parameter
- **Pagination Support**: Use `page` and `limit` parameters for easy pagination
- **Request ID**: All responses include a `request_id` for tracking and debugging
- **Flexible Filtering**: Filter by any combination of labels or list all sessions

**Example:**
```python
from agentbay import AgentBay

agent_bay = AgentBay(api_key="your_api_key")

# List all sessions
result = agent_bay.list()

# List sessions with specific labels
result = agent_bay.list(labels={"project": "demo"})

# List sessions with pagination (page 2, 10 items per page)
result = agent_bay.list(labels={"my-label": "my-value"}, page=2, limit=10)

if result.success:
    for session_id in result.session_ids:
        print(f"Session ID: {session_id}")
    print(f"Total count: {result.total_count}")
    print(f"Request ID: {result.request_id}")
else:
    print(f"Error: {result.error_message}")
```

### delete

```python
delete(session: Session, sync_context: bool = False) -> DeleteResult
```

**Parameters:**
- `session` (Session): The session to delete.
- `sync_context` (bool, optional): If True, the API will trigger a file upload via `session.context.sync` before actually releasing the session. Default is False.

**Returns:**
- `DeleteResult`: A result object containing success status, request ID, and error message if any.

**Behavior:**
- When `sync_context` is True, the API will first call `session.context.sync` to trigger file upload.
- It will then check `session.context.info` to retrieve ContextStatusData and monitor all data items' Status.
- The API waits until all items show either "Success" or "Failed" status, or until the maximum retry limit (150 times with 2-second intervals) is reached.
- Any "Failed" status items will have their error messages printed.
- The session deletion only proceeds after context sync status checking completes.

**Raises:**
- `AgentBayError`: If the session deletion fails.

**Example:**
```python
from agentbay import AgentBay

# Initialize the SDK
agent_bay = AgentBay(api_key="your_api_key")

# Create a session
result = agent_bay.create()
if result.success:
    session = result.session
    print(f"Created session with ID: {session.session_id}")

    # Use the session for operations...

    # Delete the session when done
    delete_result = agent_bay.delete(session)
    if delete_result.success:
        print("Session deleted successfully")
    else:
        print(f"Failed to delete session: {delete_result.error_message}")
```

