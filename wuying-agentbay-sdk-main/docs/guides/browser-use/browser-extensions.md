# Browser Extension Management Guide

This guide covers how to use browser extensions with the AgentBay SDK for automated testing and browser automation workflows.

## Overview

The AgentBay SDK provides comprehensive browser extension management capabilities, allowing you to:

- Upload and manage browser extensions in the cloud
- Automatically synchronize extensions to browser sessions
- Test extension functionality in controlled environments
- Develop and iterate on extensions with cloud infrastructure

## Prerequisites

- AgentBay Python SDK installed (`pip install wuying-agentbay-sdk`)
- Valid AgentBay API key
- Browser extension packaged as ZIP file
- Basic understanding of browser automation concepts

## Quick Start

### 1. Basic Extension Upload and Usage

```python
from agentbay import AgentBay
from agentbay.extension import ExtensionsService
from agentbay.session_params import CreateSessionParams, BrowserContext

# Initialize AgentBay and Extensions Service
agent_bay = AgentBay(api_key="your_api_key")
extensions_service = ExtensionsService(agent_bay)

# Upload your extension
extension = extensions_service.create("/path/to/your-extension.zip")
print(f"Extension uploaded: {extension.name} (ID: {extension.id})")

# Create browser session with extension
ext_option = extensions_service.create_extension_option([extension.id])

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

### 2. Working with Multiple Extensions

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
    print(f"✅ Uploaded: {ext.name}")

# Create session with all extensions
ext_option = extensions_service.create_extension_option(extension_ids)

session_params = CreateSessionParams(
    browser_context=BrowserContext(
        context_id="multi_extension_session",
        extension_option=ext_option
    )
)

session = agent_bay.create(session_params).session
```

## Core Concepts

### Extension Context Management

The SDK automatically manages extension storage contexts:

- **Auto-creation**: If no context is specified, a unique context is created automatically
- **Context reuse**: Specify a context name to reuse existing extension storage
- **Automatic cleanup**: Contexts created by the service can be automatically cleaned up

```python
# Auto-generated context (recommended for simple use cases)
extensions_service = ExtensionsService(agent_bay)

# Named context (recommended for persistent extension management)
extensions_service = ExtensionsService(agent_bay, "my_project_extensions")

# Context will be created if it doesn't exist
```

### Extension Synchronization

Extensions are automatically synchronized to browser sessions:

- **Automatic sync**: No manual intervention required
- **File location**: Extensions available at `/tmp/extensions/{extension_id}/` in sessions
- **Session isolation**: Each session gets its own copy of extensions

## Common Workflows

### Extension Development and Testing

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
        print(f"✅ Extension uploaded: {extension.name}")
        return extension.id

    def create_test_session(self) -> 'Session':
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
        print(f"✅ Extension updated: {updated_ext.name}")

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

### Automated Extension Testing

```python
def run_extension_tests(extension_paths: List[str]) -> bool:
    """Run automated tests on multiple extensions."""

    agent_bay = AgentBay()
    extensions_service = ExtensionsService(agent_bay)

    try:
        # Upload all test extensions
        extension_ids = []
        for path in extension_paths:
            ext = extensions_service.create(path)
            extension_ids.append(ext.id)
            print(f"📦 Uploaded test extension: {ext.name}")

        # Create test session
        ext_option = extensions_service.create_extension_option(extension_ids)

        session_params = CreateSessionParams(
            labels={"test_type": "automated_extension_testing"},
            browser_context=BrowserContext(
                context_id="auto_test_session",
                extension_option=ext_option
            )
        )

        session = agent_bay.create(session_params).session

        # Wait for extension synchronization
        print("⏳ Waiting for extension synchronization...")

        # Run your extension tests here
        # Extensions are available at /tmp/extensions/ in the session
        test_results = run_test_suite(session)

        return test_results.all_passed

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        extensions_service.cleanup()

# Usage
test_extensions = [
    "/path/to/test-extension-1.zip",
    "/path/to/test-extension-2.zip"
]

success = run_extension_tests(test_extensions)
print(f"Test result: {'✅ PASSED' if success else '❌ FAILED'}")
```

## Best Practices

### 1. Context Management

✅ **Do:**

- Use descriptive context names for persistent projects
- Let the service auto-generate contexts for simple use cases
- Always call `cleanup()` in finally blocks

❌ **Don't:**

- Hardcode context IDs in your application code
- Forget to clean up auto-created contexts
- Mix extensions from different projects in the same context

### 2. Extension File Management

✅ **Do:**

- Use ZIP format for all extension packages
- Validate file existence before upload
- Include proper manifest.json in extensions
- Handle upload errors gracefully

❌ **Don't:**

- Upload uncompressed extension directories
- Skip file validation steps
- Ignore upload error responses

### 3. Session Management

✅ **Do:**

- Use meaningful labels for sessions
- Wait for extension synchronization before testing
- Create one ExtensionOption per session

❌ **Don't:**

- Start testing immediately after session creation
- Reuse ExtensionOption across multiple sessions
- Forget to specify browser_context when using extensions

### 4. Error Handling

```python
from agentbay.exceptions import AgentBayError

def robust_extension_workflow():
    extensions_service = None
    try:
        agent_bay = AgentBay()
        extensions_service = ExtensionsService(agent_bay, "production_extensions")
        # Validate extension file
        extension_path = "/path/to/production-extension.zip"
        if not os.path.exists(extension_path):
            raise FileNotFoundError(f"Extension not found: {extension_path}")

        # Upload with error handling
        extension = extensions_service.create(extension_path)
        print(f"✅ Extension uploaded: {extension.id}")

        # Create session with validation
        ext_option = extensions_service.create_extension_option([extension.id])
        if not ext_option.validate():
            raise ValueError("Invalid extension configuration")
        session_params = CreateSessionParams(
            browser_context=BrowserContext(
                context_id="production_session",
                extension_option=ext_option
            )
        )

        session = agent_bay.create(session_params).session
        return session

    except FileNotFoundError as e:
        print(f"❌ File error: {e}")
        return None
    except AgentBayError as e:
        print(f"❌ AgentBay error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None
    finally:
        if extensions_service:
            extensions_service.cleanup()
```

## Troubleshooting

### Common Issues

**Extension not found in session:**

- Check that extension was uploaded successfully
- Verify session was created with proper ExtensionOption
- Wait for synchronization to complete before accessing files

**Upload failures:**

- Ensure file is in ZIP format
- Check file permissions and accessibility
- Verify API key and network connectivity

**Context errors:**

- Use unique context names to avoid conflicts
- Don't mix extensions from different sources
- Clean up contexts when no longer needed

### Debugging Tips

```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check extension list
extensions = extensions_service.list()
print(f"Available extensions: {[ext.name for ext in extensions]}")

# Validate extension option
ext_option = extensions_service.create_extension_option([extension.id])
print(f"Extension option valid: {ext_option.validate()}")
print(f"Extension option: {ext_option}")

# Check session creation result
session_result = agent_bay.create(session_params)
if not session_result.success:
    print(f"Session creation failed: {session_result.error_message}")
```

## Integration with Browser Automation

Extensions work seamlessly with browser automation tools:

```python
from playwright.sync_api import sync_playwright

# Create session with extensions
session = create_extension_session()

# Get browser endpoint
endpoint_url = session.browser.get_endpoint_url()

# Connect with Playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(endpoint_url)
    page = browser.new_page()

    # Extensions are already loaded and available
    page.goto("https://example.com")

    # Your extension should be active here
    # Test extension functionality...

    browser.close()
```

## 📚 Related Guides

- [Extension Management](core-features/extension.md) - Detailed extension management guide
- [Browser Context](core-features/browser-context.md) - Persistent browser state management
- [Browser Use Overview](README.md) - Complete browser automation features
- [Session Management](../common-features/basics/session-management.md) - Session lifecycle and configuration

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../README.md)
