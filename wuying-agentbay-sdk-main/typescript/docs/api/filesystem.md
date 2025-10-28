# FileSystem API Reference (TypeScript)

The FileSystem module provides comprehensive file and directory operations within AgentBay sessions, including real-time directory monitoring capabilities and file transfer functionality.

## 📖 Related Tutorial

- [Complete Guide to File Operations](../../../docs/guides/common-features/basics/file-operations.md) - Detailed tutorial covering all file operation features

## Overview

The FileSystem class enables you to:
- Perform standard file operations (read, write, create, delete)
- Monitor directories for real-time file changes
- Handle file uploads and downloads between local and remote environments
- Manage file permissions and metadata

## Core Types

### FileChangeEvent

Represents a single file change event detected during directory monitoring.

```typescript
export interface FileChangeEvent {
  eventType: string; // "create", "modify", "delete"
  path: string;      // Full path to the changed file/directory
  pathType: string;  // "file" or "directory"
}
```

### FileChangeResult

Contains the result of file change detection operations.

```typescript
export interface FileChangeResult extends ApiResponse {
  events: FileChangeEvent[];
  rawData: string;
}
```

## File Transfer Methods

### uploadFile

Uploads a local file to a remote path using pre-signed URLs.

```typescript
async uploadFile(
  localPath: string,
  remotePath: string,
  options?: {
    contentType?: string;
    wait?: boolean;
    waitTimeout?: number;
    pollInterval?: number;
    progressCb?: (bytesTransferred: number) => void;
  }
): Promise<UploadResult>
```

**Parameters:**
- `localPath` (string): Local file path to upload
- `remotePath` (string): Remote file path to upload to
- `options` (object, optional): Upload options
  - `contentType` (string): Content type of the file
  - `wait` (boolean): Whether to wait for sync completion (default: true)
  - `waitTimeout` (number): Timeout for waiting in seconds (default: 30.0)
  - `pollInterval` (number): Polling interval in seconds (default: 1.5)
  - `progressCb` (function): Progress callback function

**Returns:**
- `Promise<UploadResult>`: Promise resolving to upload result

**Example:**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

async function uploadFileExample() {
  // Initialize AgentBay
  const agentBay = new AgentBay({ apiKey: 'your-api-key' });

  // Create session with context sync for file transfer
  const sessionResult = await agentBay.create({
    imageId: 'code_latest'
  });

  if (!sessionResult.success || !sessionResult.session) {
    throw new Error('Failed to create session');
  }

  const session = sessionResult.session;
  const fileSystem = session.fileSystem();

  try {
    // Upload a file
    const uploadResult = await fileSystem.uploadFile(
      '/local/path/to/file.txt',
      '/remote/path/to/file.txt'
    );

    if (uploadResult.success) {
      console.log(`Upload successful!`);
      console.log(`Bytes sent: ${uploadResult.bytesSent}`);
      console.log(`Request ID (upload URL): ${uploadResult.requestIdUploadUrl}`);
      console.log(`Request ID (sync): ${uploadResult.requestIdSync}`);
    } else {
      console.error(`Upload failed: ${uploadResult.error}`);
    }
  } finally {
    // Clean up session
    await agentBay.delete(session);
  }
}
```

### downloadFile

Downloads a remote file to a local path using pre-signed URLs.

```typescript
async downloadFile(
  remotePath: string,
  localPath: string,
  options?: {
    overwrite?: boolean;
    wait?: boolean;
    waitTimeout?: number;
    pollInterval?: number;
    progressCb?: (bytesReceived: number) => void;
  }
): Promise<DownloadResult>
```

**Parameters:**
- `remotePath` (string): Remote file path to download from
- `localPath` (string): Local file path to download to
- `options` (object, optional): Download options
  - `overwrite` (boolean): Whether to overwrite existing file (default: true)
  - `wait` (boolean): Whether to wait for sync completion (default: true)
  - `waitTimeout` (number): Timeout for waiting in seconds (default: 30.0)
  - `pollInterval` (number): Polling interval in seconds (default: 1.5)
  - `progressCb` (function): Progress callback function

**Returns:**
- `Promise<DownloadResult>`: Promise resolving to download result

**Example:**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

async function downloadFileExample() {
  // Initialize AgentBay
  const agentBay = new AgentBay({ apiKey: 'your-api-key' });

  // Create session
  const sessionResult = await agentBay.create({
    imageId: 'code_latest'
  });

  if (!sessionResult.success || !sessionResult.session) {
    throw new Error('Failed to create session');
  }

  const session = sessionResult.session;
  const fileSystem = session.fileSystem();

  try {
    // Download a file
    const downloadResult = await fileSystem.downloadFile(
      '/remote/path/to/file.txt',
      '/local/path/to/file.txt'
    );

    if (downloadResult.success) {
      console.log(`Download successful!`);
      console.log(`Bytes received: ${downloadResult.bytesReceived}`);
      console.log(`Request ID (download URL): ${downloadResult.requestIdDownloadUrl}`);
      console.log(`Request ID (sync): ${downloadResult.requestIdSync}`);
    } else {
      console.error(`Download failed: ${downloadResult.error}`);
    }
  } finally {
    // Clean up session
    await agentBay.delete(session);
  }
}
```

## Directory Monitoring Methods

### getFileChange

Retrieves file changes that occurred in a directory since the last check.

```typescript
async getFileChange(path: string): Promise<FileChangeResult>
```

**Parameters:**
- `path` (string): Directory path to monitor

**Returns:**
- `Promise<FileChangeResult>`: Promise resolving to result containing detected file changes

**Example:**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

async function checkFileChanges() {
  // Initialize AgentBay
  const agentBay = new AgentBay({ apiKey: 'your-api-key' });

  // Create session
  const sessionResult = await agentBay.create({
    imageId: 'code_latest'
  });

  if (!sessionResult.success || !sessionResult.session) {
    throw new Error('Failed to create session');
  }

  const session = sessionResult.session;
  const fileSystem = session.fileSystem();

  try {
    // Check for file changes
    const result = await fileSystem.getFileChange('/tmp/watch_dir');

    if (FileChangeResultHelper.hasChanges(result)) {
      console.log(`Detected ${result.events.length} changes:`);
      result.events.forEach(event => {
        console.log(`- ${FileChangeEventHelper.toString(event)}`);
      });
    } else {
      console.log('No changes detected');
    }
  } finally {
    // Clean up session
    await agentBay.delete(session);
  }
}
```

### watchDirectory

Continuously monitors a directory for file changes and executes a callback function when changes are detected.

```typescript
async watchDirectory(
  path: string,
  callback: (events: FileChangeEvent[]) => void,
  intervalMs: number = 1000,
  signal?: AbortSignal
): Promise<void>
```

**Parameters:**
- `path` (string): Directory path to monitor
- `callback` (function): Function called when changes are detected
- `intervalMs` (number, optional): Polling interval in milliseconds (default: 1000, minimum: 100)
- `signal` (AbortSignal, optional): Signal to abort the monitoring

**Returns:**
- `Promise<void>`: Promise that resolves when monitoring stops

**Example:**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

async function watchDirectoryExample() {
  // Initialize AgentBay
  const agentBay = new AgentBay({ apiKey: 'your-api-key' });

  // Create session
  const sessionResult = await agentBay.create({
    imageId: 'code_latest'
  });

  if (!sessionResult.success || !sessionResult.session) {
    throw new Error('Failed to create session');
  }

  const session = sessionResult.session;
  const fileSystem = session.fileSystem();

  // Create test directory
  const testDir = '/tmp/agentbay_watch_test';
  await fileSystem.createDirectory(testDir);

  try {
    // Set up callback function
    const callback = (events: FileChangeEvent[]) => {
      console.log(`Detected ${events.length} file changes:`);
      events.forEach(event => {
        console.log(`- ${FileChangeEventHelper.toString(event)}`);
      });
    };

    // Create AbortController for stopping the watch
    const controller = new AbortController();

    // Start monitoring
    const watchPromise = fileSystem.watchDirectory(
      testDir,
      callback,
      1000, // 1 second interval
      controller.signal
    );

    // Simulate file operations after a delay
    setTimeout(async () => {
      // Create a file
      const testFile = `${testDir}/test.txt`;
      await fileSystem.writeFile(testFile, 'Hello, AgentBay!');

      // Modify the file after another delay
      setTimeout(async () => {
        await fileSystem.writeFile(testFile, 'Modified content');

        // Stop monitoring after another delay
        setTimeout(() => {
          controller.abort();
        }, 2000);
      }, 2000);
    }, 2000);

    // Wait for monitoring to complete
    await watchPromise;
    console.log('Monitoring stopped');

  } finally {
    // Clean up
    await agentBay.delete(session);
  }
}
```

## Helper Method Examples

### Using FileChangeEventHelper

```typescript
// Create event from dictionary
const eventData = {
  eventType: 'create',
  path: '/tmp/new_file.txt',
  pathType: 'file'
};
const event = FileChangeEventHelper.fromDict(eventData);

// Convert to string
const eventString = FileChangeEventHelper.toString(event);
console.log(eventString); // "FileChangeEvent(eventType='create', path='/tmp/new_file.txt', pathType='file')"

// Convert to dictionary
const eventDict = FileChangeEventHelper.toDict(event);
console.log(eventDict); // { eventType: 'create', path: '/tmp/new_file.txt', pathType: 'file' }
```

### Using FileChangeResultHelper

```typescript
// Assuming you have a FileChangeResult
const result: FileChangeResult = await fileSystem.getFileChange('/tmp/watch_dir');

// Check if there are changes
if (FileChangeResultHelper.hasChanges(result)) {
  // Get specific types of changes
  const modifiedFiles = FileChangeResultHelper.getModifiedFiles(result);
  const createdFiles = FileChangeResultHelper.getCreatedFiles(result);
  const deletedFiles = FileChangeResultHelper.getDeletedFiles(result);

  console.log('Modified files:', modifiedFiles);
  console.log('Created files:', createdFiles);
  console.log('Deleted files:', deletedFiles);
}
```

## Best Practices

### 1. Polling Interval

Choose an appropriate polling interval based on your needs:

```typescript
// High-frequency monitoring (higher CPU usage)
await fileSystem.watchDirectory(path, callback, 100);

// Normal monitoring (balanced)
await fileSystem.watchDirectory(path, callback, 1000);

// Low-frequency monitoring (lower CPU usage)
await fileSystem.watchDirectory(path, callback, 5000);
```

### 2. Error Handling

Always handle errors and implement proper cleanup:

```typescript
const controller = new AbortController();

try {
  await fileSystem.watchDirectory(path, callback, 1000, controller.signal);
} catch (error) {
  console.error('Watch error:', error);
} finally {
  // Ensure monitoring is stopped
  controller.abort();
}
```

### 3. Callback Function Design

Keep callback functions lightweight and handle errors gracefully:

```typescript
const callback = (events: FileChangeEvent[]) => {
  try {
    events.forEach(event => {
      // Process event
      processFileChange(event);
    });
  } catch (error) {
    console.error('Callback error:', error);
  }
};
```

### 4. Using AbortController

Use AbortController for better control over monitoring lifecycle:

```typescript
const controller = new AbortController();

// Set up automatic timeout
setTimeout(() => {
  controller.abort();
}, 30000); // Stop after 30 seconds

// Start monitoring
await fileSystem.watchDirectory(path, callback, 1000, controller.signal);
```

## Common Use Cases

### 1. Development File Watcher

Monitor source code changes during development:

```typescript
const callback = (events: FileChangeEvent[]) => {
  events.forEach(event => {
    if (event.path.endsWith('.ts') && event.eventType === 'modify') {
      console.log(`TypeScript file modified: ${event.path}`);
      // Trigger rebuild or test
    }
  });
};
```

### 2. Log File Monitor

Monitor log files for new entries:

```typescript
const callback = (events: FileChangeEvent[]) => {
  events.forEach(event => {
    if (event.path.includes('.log') && event.eventType === 'modify') {
      console.log(`Log file updated: ${event.path}`);
      // Process new log entries
    }
  });
};
```

### 3. Configuration File Watcher

Monitor configuration files for changes:

```typescript
const callback = (events: FileChangeEvent[]) => {
  events.forEach(event => {
    if (event.path.endsWith('config.json')) {
      console.log(`Configuration changed: ${event.path}`);
      // Reload configuration
    }
  });
};
```

### 4. Filtered Monitoring

Monitor only specific file types:

```typescript
const callback = (events: FileChangeEvent[]) => {
  const imageEvents = events.filter(event => 
    /\.(jpg|jpeg|png|gif)$/i.test(event.path)
  );
  
  if (imageEvents.length > 0) {
    console.log(`Image files changed: ${imageEvents.length}`);
    imageEvents.forEach(event => {
      console.log(`- ${event.eventType}: ${event.path}`);
    });
  }
};
```

## Advanced Usage

### Multiple Directory Monitoring

Monitor multiple directories with different configurations:

```typescript
async function monitorMultipleDirectories() {
  const directories = [
    { path: '/tmp/src', interval: 500 },
    { path: '/tmp/logs', interval: 2000 },
    { path: '/tmp/config', interval: 5000 }
  ];

  const controllers = directories.map(() => new AbortController());

  try {
    // Start monitoring all directories
    const promises = directories.map((dir, index) => 
      fileSystem.watchDirectory(
        dir.path,
        (events) => console.log(`${dir.path}: ${events.length} changes`),
        dir.interval,
        controllers[index].signal
      )
    );

    // Wait for all monitoring to complete
    await Promise.all(promises);
  } finally {
    // Stop all monitoring
    controllers.forEach(controller => controller.abort());
  }
}
```

### Conditional Monitoring

Start and stop monitoring based on conditions:

```typescript
let isMonitoring = false;
const controller = new AbortController();

async function conditionalMonitoring() {
  if (shouldStartMonitoring() && !isMonitoring) {
    isMonitoring = true;
    
    try {
      await fileSystem.watchDirectory(
        '/tmp/watch_dir',
        (events) => {
          // Check if we should stop monitoring
          if (shouldStopMonitoring()) {
            controller.abort();
          }
          
          // Process events
          processEvents(events);
        },
        1000,
        controller.signal
      );
    } finally {
      isMonitoring = false;
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **High CPU Usage**: Reduce polling frequency by increasing `intervalMs`
2. **Missing Events**: Ensure the directory exists and is accessible
3. **Callback Errors**: Implement proper error handling in callback functions
4. **Memory Leaks**: Always abort controllers and clean up resources

### Performance Considerations

- Use appropriate polling intervals based on your needs
- Filter events in callback functions to reduce processing overhead
- Consider using multiple watchers for different directories with different intervals
- Monitor memory usage when watching large directories with frequent changes

### Error Handling Examples

```typescript
// Handle AbortController errors
try {
  await fileSystem.watchDirectory(path, callback, 1000, controller.signal);
} catch (error) {
  if (error.name === 'AbortError') {
    console.log('Monitoring was aborted');
  } else {
    console.error('Monitoring error:', error);
  }
}

// Handle callback errors
const safeCallback = (events: FileChangeEvent[]) => {
  try {
    processEvents(events);
  } catch (error) {
    console.error('Error processing events:', error);
    // Continue monitoring despite callback errors
  }
};
```

## Limitations

- Polling-based detection (not real-time filesystem events)
- Performance depends on polling interval and directory size
- May miss very rapid file changes that occur between polls
- Requires active session connection to AgentBay service
- AbortController support depends on Node.js version (polyfill may be needed for older versions)
