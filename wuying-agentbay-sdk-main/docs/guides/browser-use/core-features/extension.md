# Browser Extension Management

Browser Extension Management is a core feature of the AgentBay SDK that enables you to upload, manage, and synchronize browser extensions with your browser sessions. This is particularly useful for automated testing of browser extensions, web scraping with custom extensions, and browser automation workflows.

## Overview

The Extension Management feature allows you to:
- Upload browser extensions to the cloud
- Manage multiple extensions in a context
- Automatically synchronize extensions to browser sessions
- Test extension functionality in controlled environments
- Update and maintain extensions across sessions

## Key Concepts

### ExtensionsService

The `ExtensionsService` is the main class for managing browser extensions. It handles:
- Extension storage in cloud contexts
- Extension upload and management
- Extension synchronization to sessions
- Automatic cleanup of resources

### ExtensionOption

The `ExtensionOption` encapsulates extension configuration for browser sessions, including:
- Context ID where extensions are stored
- List of extension IDs to synchronize
- Automatic generation of context sync configurations

### Extension Synchronization

Extensions are automatically synchronized to browser sessions at:
- Path: `/tmp/extensions/{extension_id}/` in each session
- Each extension gets its own directory with all extension files
- Session isolation ensures each session has its own copy

## Python Implementation

### Basic Extension Usage

```python
from agentbay import AgentBay
from agentbay.extention import ExtensionsService
from agentbay.session_params import CreateSessionParams, BrowserContext

# Initialize AgentBay and Extensions Service
agent_bay = AgentBay(api_key="your_api_key")
extensions_service = ExtensionsService(agent_bay)

# Upload your extension
extension = extensions_service.create("/path/to/your-extension.zip")
print(f"Extension uploaded: {extension.name} (ID: {extension.id})")

# Create extension option for browser integration
ext_option = extensions_service.create_extension_option([extension.id])

# Create browser session with extension
session_params = CreateSessionParams(
    labels={"purpose": "extension_testing"},
    browser_context=BrowserContext(
        context_id="extension_test_session",
        extension_option=ext_option
    )
)

# Create session - extension will be automatically synchronized
session_result = agent_bay.create(session_params)
session = session_result.session

# Extensions are now available at /tmp/extensions/ in the session
print("Extension session created successfully!")

# Clean up when done
extensions_service.cleanup()
```

### Working with Multiple Extensions

```python
# Upload multiple extensions
extension_paths = [
    "/path/to/extension1.zip",
    "/path/to/extension2.zip",
    "/path/to/extension3.zip"
]

extension_ids = []
for path in extension_paths:
    ext = extensions_service.create(path)
    extension_ids.append(ext.id)
    print(f"Uploaded: {ext.name}")

# Create session with all extensions
ext_option = extensions_service.create_extension_option(extension_ids)

session_params = CreateSessionParams(
    browser_context=BrowserContext(
        context_id="multi_extension_session",
        extension_option=ext_option
    )
)

session = agent_bay.create(session_params).session

# Extensions are available at /tmp/extensions/{extension_id}/
```

### Extension Development Workflow

```python
class ExtensionDevelopmentWorkflow:
    def __init__(self, api_key: str):
        self.agent_bay = AgentBay(api_key=api_key)
        self.extensions_service = ExtensionsService(self.agent_bay, "dev_extensions")
        self.extension_id = None
    
    def upload_extension(self, extension_path: str) -> str:
        """Upload extension for development testing."""
        extension = self.extensions_service.create(extension_path)
        self.extension_id = extension.id
        print(f"Extension uploaded: {extension.name}")
        return extension.id
    
    def create_test_session(self):
        """Create a browser session for testing."""
        ext_option = self.extensions_service.create_extension_option([self.extension_id])
        
        session_params = CreateSessionParams(
            labels={"purpose": "extension_development"},
            browser_context=BrowserContext(
                context_id="dev_session",
                extension_option=ext_option
            )
        )
        
        return self.agent_bay.create(session_params).session
    
    def update_and_test(self, new_extension_path: str):
        """Update extension and create new test session."""
        # Update existing extension
        updated_ext = self.extensions_service.update(self.extension_id, new_extension_path)
        print(f"Extension updated: {updated_ext.name}")
        
        # Create new test session with updated extension
        return self.create_test_session()
    
    def cleanup(self):
        """Clean up development resources."""
        if self.extension_id:
            self.extensions_service.delete(self.extension_id)
        self.extensions_service.cleanup()

# Usage
workflow = ExtensionDevelopmentWorkflow(api_key="your_api_key")
try:
    # Development cycle
    workflow.upload_extension("/path/to/extension-v1.zip")
    session1 = workflow.create_test_session()
    # Test extension functionality...
    
    # Update and test again
    session2 = workflow.update_and_test("/path/to/extension-v2.zip")
    # Test updated functionality...
    
finally:
    workflow.cleanup()
```

## TypeScript Implementation

### Basic Extension Usage

```typescript
import { AgentBay, ExtensionsService, CreateSessionParams, BrowserContext } from 'wuying-agentbay-sdk';

// Initialize AgentBay and Extensions Service
const agentBay = new AgentBay({ apiKey: "your_api_key" });
const extensionsService = new ExtensionsService(agentBay);

// Upload your extension
const extension = await extensionsService.create("/path/to/your-extension.zip");
console.log(`Extension uploaded: ${extension.name} (ID: ${extension.id})`);

// Create extension option for browser integration
const extOption = extensionsService.createExtensionOption([extension.id]);

// Create browser session with extension
const sessionParams = new CreateSessionParams()
    .withLabels({ purpose: "extension_testing" })
    .withBrowserContext(new BrowserContext(
        "extension_test_session",
        true,
        extOption
    ));

// Create session - extension will be automatically synchronized
const sessionResult = await agentBay.create(sessionParams);
const session = sessionResult.session;

// Extensions are now available at /tmp/extensions/ in the session
console.log("Extension session created successfully!");

// Clean up when done
await extensionsService.cleanup();
```

### Working with Multiple Extensions

```typescript
// Upload multiple extensions
const extensionPaths = [
    "/path/to/extension1.zip",
    "/path/to/extension2.zip",
    "/path/to/extension3.zip"
];

const extensionIds: string[] = [];
for (const path of extensionPaths) {
    const ext = await extensionsService.create(path);
    extensionIds.push(ext.id);
    console.log(`Uploaded: ${ext.name}`);
}

// Create session with all extensions
const extOption = extensionsService.createExtensionOption(extensionIds);

const sessionParams = new CreateSessionParams()
    .withBrowserContext(new BrowserContext(
        "multi_extension_session",
        true,
        extOption
    ));

const session = (await agentBay.create(sessionParams)).session;

// Extensions are available at /tmp/extensions/{extension_id}/
```

## Extension Context Management

The SDK automatically manages extension storage contexts:

### Auto-Generated Contexts

```python
# Auto-generated context (recommended for simple use cases)
extensions_service = ExtensionsService(agent_bay)
# Context name will be automatically generated as "extensions-{timestamp}"
```

### Named Contexts

```python
# Named context (recommended for persistent extension management)
extensions_service = ExtensionsService(agent_bay, "my_project_extensions")
# Context will be created if it doesn't exist
```

## Best Practices

1. **Use Named Contexts**: For persistent extension management, use named contexts instead of auto-generated ones
2. **Clean Up Resources**: Always call `cleanup()` to remove auto-created contexts
3. **Validate Extensions**: Ensure your extensions are properly packaged as ZIP files with manifest.json
4. **Handle Errors**: Implement proper error handling for extension operations
5. **Version Control**: Keep track of extension versions for consistent testing

## Extension Requirements

### File Format
- Extensions must be packaged as ZIP files (.zip)
- Standard browser extension structure with manifest.json
- Manifest V2 or V3 format supported

### File Structure
```
your-extension.zip
├── manifest.json
├── background.js
├── content.js
├── popup.html
├── icons/
│   ├── 16.png
│   ├── 48.png
│   └── 128.png
└── ...
```

### Size Limits
- Check AgentBay documentation for current size limits
- Large extensions may affect session startup time

## Error Handling

Common errors and how to handle them:

```python
try:
    extension = extensions_service.create("/path/to/extension.zip")
except FileNotFoundError:
    print("Extension file not found")
except ValueError as e:
    print(f"Invalid extension format: {e}")
except Exception as e:
    print(f"Failed to upload extension: {e}")
finally:
    extensions_service.cleanup()
```

## Advanced Features

### Extension Updates

```python
# Update an existing extension
updated_extension = extensions_service.update(
    extension_id="ext_1234567890",
    new_local_path="/path/to/updated-extension.zip"
)
```

### Listing Extensions

```python
# List all extensions in the current context
extensions = extensions_service.list()
for ext in extensions:
    print(f"Extension: {ext.name} (ID: {ext.id})")
```

### Deleting Extensions

```python
# Delete a specific extension
success = extensions_service.delete("ext_1234567890")
if success:
    print("Extension deleted successfully")
```

## Integration with Browser Context

Extensions integrate seamlessly with Browser Context for persistent browser environments:

```python
# Create both browser context and extension service
browser_context_result = agent_bay.context.get("persistent-browser", create=True)
browser_context = browser_context_result.context

extensions_service = ExtensionsService(agent_bay, "project-extensions")
extension = extensions_service.create("/path/to/extension.zip")
ext_option = extensions_service.create_extension_option([extension.id])

# Use both in session
session_params = CreateSessionParams(
    browser_context=BrowserContext(
        context_id=browser_context.id,  # Persistent browser state
        auto_upload=True,
        extension_option=ext_option     # Extension integration
    )
)

session = agent_bay.create(session_params).session
# Session has both persistent browser state AND extensions
```

## 📚 Related Guides

- [Browser Context](browser-context.md) - Persistent browser state management
- [Session Management](../../common-features/basics/session-management.md) - Session lifecycle and configuration
- [Browser Use Overview](../README.md) - Complete browser automation features

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../../README.md)