# Extension Examples

This directory contains Python examples demonstrating browser extension management capabilities of the AgentBay SDK.

## Examples

### 1. basic_extension_usage.py
Demonstrates fundamental extension management and browser session creation:
- Uploading browser extensions to the cloud
- Creating browser sessions with extensions
- Extension synchronization and file access
- Multiple extension handling
- Proper resource cleanup

**Key features demonstrated:**
- ExtensionsService initialization and context management
- Extension upload and validation
- ExtensionOption creation for browser sessions
- Extension file access in sessions at `/tmp/extensions/`

### 2. extension_development_workflow.py
Shows a complete development workflow for browser extensions:
- Extension upload for development testing
- Test session creation with extensions
- Extension updates during development
- Iterative development cycle management
- Development resource cleanup

**Key features demonstrated:**
- ExtensionDevelopmentWorkflow class usage
- Extension versioning and updates
- Development session management
- Extension testing patterns

### 3. extension_testing_automation.py
Advanced example for automated extension testing:
- Automated test suite execution
- Multi-extension testing scenarios
- Test result reporting and analysis
- CI/CD integration patterns
- Comprehensive error handling

**Key features demonstrated:**
- ExtensionTestRunner class for automation
- Test suite configuration and execution
- Automated test reporting
- CI/CD compatible testing workflows

## Running the Examples

1. Install required dependencies:
```bash
pip install wuying-agentbay-sdk
```

2. Set your API key:
```bash
export AGENTBAY_API_KEY=your_api_key_here
```

3. Update extension paths in the examples with your actual extension ZIP files.

4. Run any example:
```bash
python basic_extension_usage.py
python extension_development_workflow.py
python extension_testing_automation.py
```

## Extension Requirements

- Extensions must be packaged as ZIP files
- Extensions must include a valid `manifest.json` file
- Extensions are synchronized to `/tmp/extensions/{extension_id}/` in browser sessions

## Usage Patterns

### Basic Extension Management
```python
from agentbay import AgentBay
from agentbay.extension import ExtensionsService

agent_bay = AgentBay(api_key="your_api_key")
extensions_service = ExtensionsService(agent_bay)

# Upload extension
extension = extensions_service.create("/path/to/extension.zip")

# Create browser session with extension
ext_option = extensions_service.create_extension_option([extension.id])
# ... use with BrowserContext
```

### Development Workflow
```python
from extension_development_workflow import ExtensionDevelopmentWorkflow

workflow = ExtensionDevelopmentWorkflow("your_api_key", "my_project")
workflow.upload_extension("/path/to/extension-v1.zip")
session = workflow.create_test_session()
# Test extension...
workflow.update_extension("/path/to/extension-v2.zip")
# Test updated version...
```

### Automated Testing
```python
from extension_testing_automation import ExtensionTestRunner, TestSuite

test_runner = ExtensionTestRunner("your_api_key")
test_suite = TestSuite(
    name="my_tests",
    extension_paths=["/path/to/test-extension.zip"],
    test_cases=["extension_loaded", "manifest_valid"]
)
results = test_runner.run_test_suite(test_suite)
```

## Best Practices

1. **Context Management**:
   - Use descriptive context names for different projects
   - Always call `cleanup()` when done
   - Let the service auto-generate contexts for simple use cases

2. **File Management**:
   - Use ZIP format for all extension packages
   - Validate file existence before upload
   - Include proper manifest.json in extensions

3. **Session Management**:
   - Use meaningful labels for sessions
   - Wait for extension synchronization before testing
   - Create one ExtensionOption per session

4. **Error Handling**:
   - Implement comprehensive error handling
   - Use try-finally blocks for cleanup
   - Validate extension configurations

## Extension File Structure

Extensions are synchronized to browser sessions at:
```
/tmp/extensions/
├── {extension_id_1}/
│   ├── manifest.json
│   ├── content.js
│   └── ... (other extension files)
├── {extension_id_2}/
│   ├── manifest.json
│   └── ... (other extension files)
└── ...
```

## Related Documentation

- [Extension API Reference](../api/extension.md) - Complete API documentation
- [Browser Extensions Guide](../../../docs/guides/browser-extensions.md) - Tutorial and best practices
- [Browser Examples](../browser/README.md) - Additional browser automation examples

## Troubleshooting

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