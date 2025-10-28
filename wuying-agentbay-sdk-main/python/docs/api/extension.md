# Extension API Reference

The Extension API provides functionality for managing browser extensions in the AgentBay cloud environment. This enables uploading, managing, and integrating browser extensions with cloud browser sessions for automated testing and development workflows.

## Import

```python
from agentbay import AgentBay
from agentbay.extension import ExtensionsService, ExtensionOption, Extension
from agentbay.session_params import CreateSessionParams, BrowserContext
```

## Extension Class

The `Extension` class represents a browser extension in the AgentBay cloud environment.

### Properties

```python
id          # The unique identifier of the extension (auto-generated)
name        # The name of the extension (typically filename)
created_at  # Date and time when the extension was uploaded (optional)
```

### Constructor

```python
Extension(id: str, name: str, created_at: Optional[str] = None)
```

**Parameters:**
- `id` (str): Unique extension identifier
- `name` (str): Extension name
- `created_at` (str, optional): Creation timestamp

## ExtensionOption Class

The `ExtensionOption` class encapsulates extension configuration for browser sessions.

### Properties

```python
context_id     # The context ID where extensions are stored
extension_ids  # List of extension IDs to include in browser sessions
```

### Constructor

```python
ExtensionOption(context_id: str, extension_ids: List[str])
```

**Parameters:**
- `context_id` (str): ID of the extension context
- `extension_ids` (List[str]): List of extension IDs to synchronize

**Raises:**
- `ValueError`: If context_id is empty or extension_ids is empty

### Methods

#### validate

Validates the extension option configuration.

```python
validate() -> bool
```

**Returns:**
- `bool`: True if configuration is valid, False otherwise

**Example:**
```python
ext_option = ExtensionOption("ctx_123", ["ext_1", "ext_2"])
if ext_option.validate():
    print("Configuration is valid")
else:
    print("Invalid configuration")
```

## ExtensionsService Class

The `ExtensionsService` class provides methods for managing browser extensions in the AgentBay cloud environment.

### Constructor

```python
ExtensionsService(agent_bay: AgentBay, context_id: str = "")
```

**Parameters:**
- `agent_bay` (AgentBay): The AgentBay client instance
- `context_id` (str, optional): Context ID or name. If empty, auto-generates a unique name

**Auto-Context Management:**
- If `context_id` is empty → generates `extensions-{timestamp}` automatically
- If `context_id` exists → uses existing context
- If `context_id` doesn't exist → creates new context with the provided name

### Properties

```python
context_id     # The actual context ID used for extension storage
context_name   # The context name (may be auto-generated)
auto_created   # Whether the context was auto-created by this service
```

### Methods

#### create

Uploads a new browser extension to the cloud context.

```python
create(local_path: str) -> Extension
```

**Parameters:**
- `local_path` (str): Path to the local extension ZIP file

**Returns:**
- `Extension`: Extension object with generated ID and metadata

**Raises:**
- `FileNotFoundError`: If the local file doesn't exist
- `ValueError`: If the file format is not supported (only ZIP files allowed)
- `AgentBayError`: If upload fails

**Example:**
```python
from agentbay import AgentBay
from agentbay.extension import ExtensionsService

# Initialize the SDK
agent_bay = AgentBay(api_key="your_api_key")

# Create extensions service
extensions_service = ExtensionsService(agent_bay)

# Upload extension
extension = extensions_service.create("/path/to/my-extension.zip")
print(f"Extension uploaded: {extension.name} (ID: {extension.id})")
```

#### list

Lists all extensions in the current context.

```python
list() -> List[Extension]
```

**Returns:**
- `List[Extension]`: List of all extensions in the context

**Raises:**
- `AgentBayError`: If listing fails

**Example:**
```python
# List all extensions
extensions = extensions_service.list()
for ext in extensions:
    print(f"Extension: {ext.name} (ID: {ext.id})")
```

#### update

Updates an existing extension with a new file.

```python
update(extension_id: str, new_local_path: str) -> Extension
```

**Parameters:**
- `extension_id` (str): ID of the extension to update
- `new_local_path` (str): Path to the new extension ZIP file

**Returns:**
- `Extension`: Updated extension object

**Raises:**
- `FileNotFoundError`: If the new local file doesn't exist
- `ValueError`: If the extension ID doesn't exist in the context
- `AgentBayError`: If update fails

**Example:**
```python
# Update existing extension
updated_ext = extensions_service.update("ext_123", "/path/to/updated-extension.zip")
print(f"Extension updated: {updated_ext.name}")
```

#### delete

Deletes an extension from the context.

```python
delete(extension_id: str) -> bool
```

**Parameters:**
- `extension_id` (str): ID of the extension to delete

**Returns:**
- `bool`: True if deletion was successful, False otherwise

**Example:**
```python
# Delete extension
success = extensions_service.delete("ext_123")
if success:
    print("Extension deleted successfully")
else:
    print("Failed to delete extension")
```

#### create_extension_option

**🎯 Recommended Method** - Creates an ExtensionOption without exposing context_id to users.

```python
create_extension_option(extension_ids: List[str]) -> ExtensionOption
```

**Parameters:**
- `extension_ids` (List[str]): List of extension IDs to include

**Returns:**
- `ExtensionOption`: Configuration object for browser extension integration

**Raises:**
- `ValueError`: If extension_ids is empty

**Key Benefits:**
- ✅ **No context_id needed**: Users only provide extension IDs
- ✅ **Automatic context handling**: Context ID is handled internally
- ✅ **Clean API**: Decouples users from internal context management

**Example:**
```python
from agentbay.session_params import CreateSessionParams, BrowserContext

# Create extensions
ext1 = extensions_service.create("/path/to/ext1.zip")
ext2 = extensions_service.create("/path/to/ext2.zip")

# Create extension option (no context_id needed!)
ext_option = extensions_service.create_extension_option([ext1.id, ext2.id])

# Use with BrowserContext for session creation
session_params = CreateSessionParams(
    browser_context=BrowserContext(
        context_id="browser_session",
        auto_upload=True,
        extension_option=ext_option
    )
)

session_result = agent_bay.create(session_params)
session = session_result.session
```

#### cleanup

Cleans up auto-created context if it was created by this service.

```python
cleanup() -> bool
```

**Returns:**
- `bool`: True if cleanup was successful or not needed, False if cleanup failed

**Note:** Only cleans up contexts that were auto-created by this service instance.

**Example:**
```python
try:
    # Use extensions service
    extensions_service = ExtensionsService(agent_bay)
    # ... extension operations
finally:
    # Always cleanup resources
    extensions_service.cleanup()
```

## BrowserContext Integration

Browser extensions are integrated with sessions through the `BrowserContext` class from `agentbay.session_params`.

### BrowserContext Constructor

```python
BrowserContext(
    context_id: str, 
    auto_upload: bool = True, 
    extension_option: Optional[ExtensionOption] = None
)
```

**Parameters:**
- `context_id` (str): ID of the browser context for the session
- `auto_upload` (bool): Whether to automatically upload browser data when session ends
- `extension_option` (Optional[ExtensionOption]): Extension configuration object

**Auto-Generated Properties:**

When `extension_option` is provided:
- `extension_context_id` (str): Extracted from ExtensionOption
- `extension_ids` (List[str]): Extracted from ExtensionOption
- `extension_context_syncs` (List[ContextSync]): Auto-generated context syncs

When `extension_option` is None:
- `extension_context_id` = None
- `extension_ids` = []
- `extension_context_syncs` = None

## Usage Patterns

### Basic Extension Management

```python
from agentbay import AgentBay
from agentbay.extension import ExtensionsService

# Initialize service
agent_bay = AgentBay(api_key="your_api_key")
extensions_service = ExtensionsService(agent_bay)

try:
    # Upload extensions
    ext1 = extensions_service.create("/path/to/extension1.zip")
    ext2 = extensions_service.create("/path/to/extension2.zip")
    
    # List extensions
    extensions = extensions_service.list()
    print(f"Total extensions: {len(extensions)}")
    
finally:
    # Clean up when done
    extensions_service.cleanup()
```

### Browser Session with Extensions

```python
from agentbay import AgentBay
from agentbay.extension import ExtensionsService
from agentbay.session_params import CreateSessionParams, BrowserContext

# Initialize and upload extensions
agent_bay = AgentBay(api_key="your_api_key")
extensions_service = ExtensionsService(agent_bay)

try:
    ext1 = extensions_service.create("/path/to/ext1.zip")
    ext2 = extensions_service.create("/path/to/ext2.zip")
    
    # Create extension option (simplified - no context_id needed!)
    extension_option = extensions_service.create_extension_option([ext1.id, ext2.id])
    
    # Create browser session with extensions
    session_params = CreateSessionParams(
        labels={"purpose": "extension_testing"},
        browser_context=BrowserContext(
            context_id="my_browser_session",
            auto_upload=True,
            extension_option=extension_option  # All extension config here
        )
    )
    
    # Create session
    session_result = agent_bay.create(session_params)
    session = session_result.session
    
    # Extensions are automatically synchronized to /tmp/extensions/ in the session
    print("Session created with extensions!")
    
finally:
    extensions_service.cleanup()
```

### Error Handling

```python
from agentbay import AgentBay
from agentbay.extension import ExtensionsService
from agentbay.exceptions import AgentBayError

try:
    agent_bay = AgentBay(api_key="your_api_key")
    extensions_service = ExtensionsService(agent_bay, "my_extensions")
    
    # Upload extension with validation
    extension_path = "/path/to/my-extension.zip"
    if not os.path.exists(extension_path):
        raise FileNotFoundError(f"Extension file not found: {extension_path}")
    
    extension = extensions_service.create(extension_path)
    print(f"✅ Extension uploaded successfully: {extension.id}")
    
    # Create extension option
    ext_option = extensions_service.create_extension_option([extension.id])
    
    if not ext_option.validate():
        raise ValueError("Invalid extension configuration")
    
    print(f"✅ Extension option created: {ext_option}")
    
except FileNotFoundError as e:
    print(f"❌ File error: {e}")
except ValueError as e:
    print(f"❌ Validation error: {e}")
except AgentBayError as e:
    print(f"❌ AgentBay error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
finally:
    if 'extensions_service' in locals():
        extensions_service.cleanup()
```

## File Location in Sessions

In browser sessions, extensions are automatically synchronized to:
```
/tmp/extensions/{extension_id}/
```

Each extension gets its own directory containing all extension files, including `manifest.json` and other extension assets.

## Related Resources

- [Session API Reference](session.md)
- [Context API Reference](context.md) 
- [AgentBay API Reference](agentbay.md)
- [Extension Examples](../examples/extension/README.md) - Practical usage examples
- [Browser Extensions Guide](../../../docs/guides/browser-extensions.md) - Complete tutorial