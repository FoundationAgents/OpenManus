# Extension API Reference

The Extension API provides functionality for managing browser extensions in the AgentBay cloud environment. This enables uploading, managing, and integrating browser extensions with cloud browser sessions for automated testing and development workflows.

## Import

```typescript
import { AgentBay, ExtensionsService, ExtensionOption, Extension } from "wuying-agentbay-sdk";
import { CreateSessionParams, BrowserContext } from "wuying-agentbay-sdk";
```

## Extension Class

The `Extension` class represents a browser extension in the AgentBay cloud environment.

### Properties

```typescript
id: string          // The unique identifier of the extension (auto-generated)
name: string        // The name of the extension (typically filename)
createdAt?: string  // Date and time when the extension was uploaded (optional)
```

### Constructor

```typescript
constructor(id: string, name: string, createdAt?: string)
```

**Parameters:**
- `id` (string): Unique extension identifier
- `name` (string): Extension name
- `createdAt` (string, optional): Creation timestamp

**Example:**
```typescript
const extension = new Extension('ext_123abc', 'my-extension.zip', '2023-01-01T10:00:00Z');
console.log(extension.id); // 'ext_123abc'
console.log(extension.name); // 'my-extension.zip'
```

## ExtensionOption Class

The `ExtensionOption` class encapsulates extension configuration for browser sessions.

### Properties

```typescript
contextId: string     // The context ID where extensions are stored
extensionIds: string[] // List of extension IDs to include in browser sessions
```

### Constructor

```typescript
constructor(contextId: string, extensionIds: string[])
```

**Parameters:**
- `contextId` (string): ID of the extension context
- `extensionIds` (string[]): List of extension IDs to synchronize

**Throws:**
- `Error`: If contextId is empty or extensionIds is empty

### Methods

#### validate

Validates the extension option configuration.

```typescript
validate(): boolean
```

**Returns:**
- `boolean`: True if configuration is valid, false otherwise

**Example:**
```typescript
const extOption = new ExtensionOption("ctx_123", ["ext_1", "ext_2"]);
if (extOption.validate()) {
    console.log("Configuration is valid");
} else {
    console.log("Invalid configuration");
}
```

#### toString

Returns string representation of ExtensionOption.

```typescript
toString(): string
```

**Example:**
```typescript
const option = new ExtensionOption('ctx_123', ['ext_1', 'ext_2']);
console.log(option.toString()); 
// "ExtensionOption(contextId='ctx_123', extensionIds=["ext_1","ext_2"])"
```

#### toDisplayString

Returns human-readable string representation.

```typescript
toDisplayString(): string
```

**Example:**
```typescript
console.log(option.toDisplayString()); 
// "Extension Config: 2 extension(s) in context 'ctx_123'"
```

## ExtensionsService Class

The `ExtensionsService` class provides methods for managing browser extensions in the AgentBay cloud environment.

### Constructor

```typescript
constructor(agentBay: AgentBay, contextId: string = "")
```

**Parameters:**
- `agentBay` (AgentBay): The AgentBay client instance
- `contextId` (string, optional): Context ID or name. If empty, auto-generates a unique name

**Auto-Context Management:**
- If `contextId` is empty → generates `extensions-{timestamp}` automatically
- If `contextId` exists → uses existing context
- If `contextId` doesn't exist → creates new context with the provided name

### Properties

```typescript
contextId: string     // The actual context ID used for extension storage
contextName: string   // The context name (may be auto-generated)
autoCreated: boolean  // Whether the context was auto-created by this service
```

### Methods

#### create

Uploads a new browser extension to the cloud context.

```typescript
create(localPath: string): Promise<Extension>
```

**Parameters:**
- `localPath` (string): Path to the local extension ZIP file

**Returns:**
- `Promise<Extension>`: Extension object with generated ID and metadata

**Throws:**
- `Error`: If the local file doesn't exist or format is not supported (only ZIP files allowed)
- `AgentBayError`: If upload fails

**Example:**
```typescript
import { AgentBay, ExtensionsService } from "wuying-agentbay-sdk";

// Initialize the SDK
const agentBay = new AgentBay({ apiKey: "your_api_key" });

// Create extensions service
const extensionsService = new ExtensionsService(agentBay);

// Upload extension
const extension = await extensionsService.create("/path/to/my-extension.zip");
console.log(`Extension uploaded: ${extension.name} (ID: ${extension.id})`);
```

#### list

Lists all extensions in the current context.

```typescript
list(): Promise<Extension[]>
```

**Returns:**
- `Promise<Extension[]>`: List of all extensions in the context

**Throws:**
- `AgentBayError`: If listing fails

**Example:**
```typescript
// List all extensions
const extensions = await extensionsService.list();
for (const ext of extensions) {
    console.log(`Extension: ${ext.name} (ID: ${ext.id})`);
}
```

#### update

Updates an existing extension with a new file.

```typescript
update(extensionId: string, newLocalPath: string): Promise<Extension>
```

**Parameters:**
- `extensionId` (string): ID of the extension to update
- `newLocalPath` (string): Path to the new extension ZIP file

**Returns:**
- `Promise<Extension>`: Updated extension object

**Throws:**
- `Error`: If the new local file doesn't exist
- `Error`: If the extension ID doesn't exist in the context
- `AgentBayError`: If update fails

**Example:**
```typescript
// Update existing extension
const updatedExt = await extensionsService.update("ext_123", "/path/to/updated-extension.zip");
console.log(`Extension updated: ${updatedExt.name}`);
```

#### delete

Deletes an extension from the context.

```typescript
delete(extensionId: string): Promise<boolean>
```

**Parameters:**
- `extensionId` (string): ID of the extension to delete

**Returns:**
- `Promise<boolean>`: True if deletion was successful, false otherwise

**Example:**
```typescript
// Delete extension
const success = await extensionsService.delete("ext_123");
if (success) {
    console.log("Extension deleted successfully");
} else {
    console.log("Failed to delete extension");
}
```

#### createExtensionOption

**🎯 Recommended Method** - Creates an ExtensionOption without exposing context_id to users.

```typescript
createExtensionOption(extensionIds: string[]): ExtensionOption
```

**Parameters:**
- `extensionIds` (string[]): List of extension IDs to include

**Returns:**
- `ExtensionOption`: Configuration object for browser extension integration

**Throws:**
- `Error`: If extensionIds is empty

**Key Benefits:**
- ✅ **No context_id needed**: Users only provide extension IDs
- ✅ **Automatic context handling**: Context ID is handled internally
- ✅ **Clean API**: Decouples users from internal context management

**Example:**
```typescript
import { CreateSessionParams, BrowserContext } from "wuying-agentbay-sdk";

// Create extensions
const ext1 = await extensionsService.create("/path/to/ext1.zip");
const ext2 = await extensionsService.create("/path/to/ext2.zip");

// Create extension option (no context_id needed!)
const extOption = extensionsService.createExtensionOption([ext1.id, ext2.id]);

// Use with BrowserContext for session creation
const sessionParams = new CreateSessionParams()
    .withBrowserContext(new BrowserContext(
        "browser_session",
        true,
        extOption
    ));

const sessionResult = await agentBay.create(sessionParams.toJSON());
const session = sessionResult.session;
```

#### cleanup

Cleans up auto-created context if it was created by this service.

```typescript
cleanup(): Promise<boolean>
```

**Returns:**
- `Promise<boolean>`: True if cleanup was successful or not needed, false if cleanup failed

**Note:** Only cleans up contexts that were auto-created by this service instance.

**Example:**
```typescript
try {
    // Use extensions service
    const extensionsService = new ExtensionsService(agentBay);
    // ... extension operations
} finally {
    // Always cleanup resources
    await extensionsService.cleanup();
}
```

## BrowserContext Integration

Browser extensions are integrated with sessions through the `BrowserContext` class from the session parameters.

### BrowserContext Constructor

```typescript
new BrowserContext(
    contextId: string, 
    autoUpload: boolean = true, 
    extensionOption?: ExtensionOption
)
```

**Parameters:**
- `contextId` (string): ID of the browser context for the session
- `autoUpload` (boolean): Whether to automatically upload browser data when session ends
- `extensionOption` (ExtensionOption, optional): Extension configuration object

**Auto-Generated Properties:**

When `extensionOption` is provided:
- `extensionContextId` (string): Extracted from ExtensionOption
- `extensionIds` (string[]): Extracted from ExtensionOption
- `extensionContextSyncs` (ContextSync[]): Auto-generated context syncs

When `extensionOption` is undefined:
- `extensionContextId` = undefined
- `extensionIds` = []
- `extensionContextSyncs` = undefined

## Usage Patterns

### Basic Extension Management

```typescript
import { AgentBay, ExtensionsService } from "wuying-agentbay-sdk";

// Initialize service
const agentBay = new AgentBay({ apiKey: "your_api_key" });
const extensionsService = new ExtensionsService(agentBay);

try {
    // Upload extensions
    const ext1 = await extensionsService.create("/path/to/extension1.zip");
    const ext2 = await extensionsService.create("/path/to/extension2.zip");
    
    // List extensions
    const extensions = await extensionsService.list();
    console.log(`Total extensions: ${extensions.length}`);
    
} finally {
    // Clean up when done
    await extensionsService.cleanup();
}
```

### Browser Session with Extensions

```typescript
import { AgentBay, ExtensionsService } from "wuying-agentbay-sdk";
import { CreateSessionParams, BrowserContext } from "wuying-agentbay-sdk";

// Initialize and upload extensions
const agentBay = new AgentBay({ apiKey: "your_api_key" });
const extensionsService = new ExtensionsService(agentBay);

try {
    const ext1 = await extensionsService.create("/path/to/ext1.zip");
    const ext2 = await extensionsService.create("/path/to/ext2.zip");
    
    // Create extension option (simplified - no context_id needed!)
    const extensionOption = extensionsService.createExtensionOption([ext1.id, ext2.id]);
    
    // Create browser session with extensions
    const sessionParams = new CreateSessionParams()
        .withLabels({ purpose: "extension_testing" })
        .withBrowserContext(new BrowserContext(
            "my_browser_session",
            true,
            extensionOption  // All extension config here
        ));
    
    // Create session
    const sessionResult = await agentBay.create(sessionParams.toJSON());
    const session = sessionResult.session;
    
    // Extensions are automatically synchronized to /tmp/extensions/ in the session
    console.log("Session created with extensions!");
    
} finally {
    await extensionsService.cleanup();
}
```

### Error Handling

```typescript
import { AgentBay, ExtensionsService } from "wuying-agentbay-sdk";
import { AgentBayError } from "wuying-agentbay-sdk";
import * as fs from "fs";

try {
    const agentBay = new AgentBay({ apiKey: "your_api_key" });
    const extensionsService = new ExtensionsService(agentBay, "my_extensions");
    
    // Upload extension with validation
    const extensionPath = "/path/to/my-extension.zip";
    if (!fs.existsSync(extensionPath)) {
        throw new Error(`Extension file not found: ${extensionPath}`);
    }
    
    const extension = await extensionsService.create(extensionPath);
    console.log(`✅ Extension uploaded successfully: ${extension.id}`);
    
    // Create extension option
    const extOption = extensionsService.createExtensionOption([extension.id]);
    
    if (!extOption.validate()) {
        throw new Error("Invalid extension configuration");
    }
    
    console.log(`✅ Extension option created: ${extOption}`);
    
} catch (error) {
    if (error instanceof Error) {
        if (error.message.includes("not found")) {
            console.error(`❌ File error: ${error.message}`);
        } else if (error.message.includes("Invalid")) {
            console.error(`❌ Validation error: ${error.message}`);
        } else {
            console.error(`❌ Unexpected error: ${error.message}`);
        }
    } else if (error instanceof AgentBayError) {
        console.error(`❌ AgentBay error: ${error.message}`);
    } else {
        console.error(`❌ Unknown error: ${error}`);
    }
} finally {
    if (extensionsService) {
        await extensionsService.cleanup();
    }
}
```

## Constants

### EXTENSIONS_BASE_PATH

```typescript
const EXTENSIONS_BASE_PATH = "/tmp/extensions";
```

Base path for storing extensions in cloud storage.

## File Location in Sessions

In browser sessions, extensions are automatically synchronized to:
```
/tmp/extensions/{extension_id}/
```

Each extension gets its own directory containing all extension files, including `manifest.json` and other extension assets.

## File Format Requirements

- **Supported Format**: ZIP files (.zip) only
- **File Structure**: Standard browser extension ZIP structure with manifest.json
- **Size Limits**: Determined by cloud storage limits
- **Naming**: Extension IDs are auto-generated with format `ext_{uuid}.zip`

## Context Management

The service automatically handles context lifecycle:

1. **Context Detection**: Checks if context exists
2. **Context Creation**: Creates context if it doesn't exist
3. **Context Usage**: Uses context for all file operations
4. **Context Cleanup**: Optionally cleans up auto-created contexts

## Error Types

- **AgentBayError**: SDK-specific errors for API/cloud operations
- **Error**: Standard errors for validation and file system issues

## Best Practices

1. **Resource Cleanup**: Always call `cleanup()` for auto-created contexts
2. **Error Handling**: Wrap operations in try-catch blocks
3. **Validation**: Validate ExtensionOption before use
4. **File Existence**: Ensure extension files exist before upload
5. **Context Naming**: Use descriptive context names for management
6. **Use Recommended API**: Prefer `createExtensionOption()` over manual ExtensionOption creation

## Related Resources

- [Session API Reference](session.md)
- [Context API Reference](context.md) 
- [AgentBay API Reference](agentbay.md)
- [Extension Examples](../examples/extension-example/README.md) - Practical usage examples
- [Browser Extensions Guide](../../../docs/guides/browser-extensions.md) - Complete tutorial