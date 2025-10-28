# Extension Management Example

This example demonstrates comprehensive browser extension management functionality using the Wuying AgentBay SDK for TypeScript.

## Overview

The extension management system allows you to:
- Upload browser extensions (.zip files) to cloud storage
- List and manage existing extensions  
- Create extension configurations for browser sessions
- Integrate extensions with browser automation workflows
- Handle multiple extensions in a single session
- Implement complete development workflows

## File Structure

```
extension-example/
├── extension-example.ts    # Comprehensive extension management examples
└── README.md             # This documentation file
```

## Key Components

### 1. Extension Class
Represents a browser extension with ID, name, and creation timestamp.

```typescript
const extension = new Extension('ext_123', 'my-extension.zip', '2023-01-01');
```

### 2. ExtensionOption Class
Configuration for browser extension integration, encapsulating context ID and extension IDs.

```typescript
const option = new ExtensionOption('context_123', ['ext_1', 'ext_2']);
```

### 3. ExtensionsService Class
Main service for managing extensions with automatic context handling.

```typescript
const service = new ExtensionsService(agentBay, 'my_extensions');
```

## Examples Included

The `extension-example.ts` file contains comprehensive examples demonstrating:

### 1. Basic Extension Management
- Upload a single extension
- Create extension options
- Integrate with browser sessions
- Basic error handling

### 2. Multiple Extensions Handling
- Upload multiple extensions
- Create sessions with multiple extensions
- Batch operations

### 3. Extension Development Workflow
- Complete development lifecycle
- Testing and validation patterns
- Extension updates
- Development context management

### 4. Error Handling and Validation
- Proper validation patterns
- Common error scenarios
- Best practices for error management

## Quick Start

### Prerequisites

1. **API Key**: Set your AgentBay API key
   ```bash
   export AGENTBAY_API_KEY="your-api-key-here"
   ```

2. **Extension Files**: Prepare your browser extension ZIP files
   - Extensions must be in ZIP format
   - Update file paths in the example code

### Running the Example

```bash
# Navigate to the TypeScript directory
cd typescript

# Install dependencies
npm install

# Build the project
npm run build

# Run the extension example
node docs/examples/extension-example/extension-example.js
```

### Code Example

```typescript
import { AgentBay, ExtensionsService } from "wuying-agentbay-sdk";
import { CreateSessionParams, BrowserContext } from "wuying-agentbay-sdk";

// Initialize AgentBay client
const agentBay = new AgentBay({
  apiKey: process.env.AGENTBAY_API_KEY,
});

// Create extensions service
const extensionsService = new ExtensionsService(agentBay, "browser_extensions");

try {
  // Upload extension
  const extension = await extensionsService.create("/path/to/extension.zip");
  
  // Create extension option
  const extOption = extensionsService.createExtensionOption([extension.id]);
  
  // Create browser session with extension
  const sessionParams = new CreateSessionParams()
    .withLabels({ purpose: "extension_demo" })
    .withBrowserContext(new BrowserContext(
      "browser_session",
      true,
      extOption
    ));
  
  const sessionResult = await agentBay.create(sessionParams.toJSON());
  const session = sessionResult.session;
  
  console.log(`Session created with extension: ${session.sessionId}`);
  
} finally {
  // Clean up resources
  await extensionsService.cleanup();
}
```

## Extension Integration

### Browser Context Integration

Extensions are automatically synchronized to `/tmp/extensions/` in browser sessions:

```typescript
// Extension option contains all necessary configuration
const extOption = extensionsService.createExtensionOption(['ext_1', 'ext_2']);

// Use with BrowserContext
const browserContext = new BrowserContext(
  "browser_session",
  true,          // auto-upload
  extOption      // extension configuration
);
```

### Context Management

The service supports two context modes:

1. **Named Context**: Provide a specific context name
   ```typescript
   new ExtensionsService(agentBay, "my_extensions")
   ```

2. **Auto-Generated Context**: Let the service generate a context name
   ```typescript
   new ExtensionsService(agentBay) // Generates: extensions-{timestamp}
   ```

## API Reference

### ExtensionsService Methods

- `create(localPath: string)` - Upload new extension
- `list()` - List all extensions in context
- `update(extensionId: string, newLocalPath: string)` - Update existing extension
- `delete(extensionId: string)` - Delete extension
- `createExtensionOption(extensionIds: string[])` - Create browser integration option
- `cleanup()` - Clean up auto-created contexts

### ExtensionOption Methods

- `validate()` - Validate configuration
- `toString()` - String representation
- `toDisplayString()` - Human-readable description

## Error Handling

The examples demonstrate comprehensive error handling:

```typescript
try {
  const extension = await extensionsService.create(extensionPath);
  // Handle success
} catch (error) {
  if (error.message.includes('File not found')) {
    console.log('Extension file does not exist');
  } else if (error.message.includes('Invalid format')) {
    console.log('Extension must be a ZIP file');
  } else {
    console.log('Upload failed:', error.message);
  }
}
```

## File Requirements

- **Format**: Extensions must be in ZIP format (.zip)
- **Structure**: Standard Chrome extension structure with manifest.json
- **Size**: Check AgentBay documentation for size limits
- **Permissions**: Ensure proper file permissions for reading

## Common Use Cases

1. **Extension Development**: Upload, test, and iterate on extensions
2. **Automated Testing**: Test extensions in cloud browser environments
3. **Batch Operations**: Manage multiple extensions simultaneously
4. **CI/CD Integration**: Automate extension deployment workflows

## Troubleshooting

### Common Issues

1. **File Not Found**: Ensure extension paths are correct
2. **Invalid Format**: Only ZIP files are supported
3. **API Key Missing**: Set AGENTBAY_API_KEY environment variable
4. **Context Conflicts**: Use unique context names for different projects

### Best Practices

1. **Always cleanup**: Use try/finally blocks for resource cleanup
2. **Validate inputs**: Check file existence before upload
3. **Handle errors**: Implement proper error handling for all operations
4. **Use descriptive names**: Name contexts and sessions clearly

## Next Steps

- Explore the complete API documentation at `typescript/docs/api/extension.md`
- Check browser automation examples for integration patterns
- Review the AgentBay SDK documentation for advanced features
- Consider implementing custom validation and testing workflows

## Related Resources

- [Extension API Reference](../../api/extension.md) - Complete API documentation
- [Session API Reference](../../api/session.md) - Browser session management
- [Context API Reference](../../api/context.md) - Context management
- [AgentBay SDK Documentation](../../api/agentbay.md) - Core SDK features