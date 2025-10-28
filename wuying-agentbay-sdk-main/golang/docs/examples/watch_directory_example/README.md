# Watch Directory Example (Go)

This example demonstrates how to use the `watch_directory` functionality in the AgentBay Go SDK to monitor file system changes in real-time.

## Features Demonstrated

- Creating an AgentBay session with `code_latest` ImageId
- Setting up directory monitoring with callback functions
- Detecting file creation, modification, and deletion events
- Using the `GetFileChange` method for one-time change detection
- Proper resource cleanup and session management

## Prerequisites

1. Go 1.18 or later
2. AgentBay API key set as environment variable `AGENTBAY_API_KEY`

## Running the Example

```bash
# Set your API key
export AGENTBAY_API_KEY="your-api-key-here"

# Run the example
go run main.go
```

## What the Example Does

1. **Initializes AgentBay**: Creates a client with your API key
2. **Creates Session**: Sets up a session with `code_latest` ImageId
3. **Sets Up Monitoring**: Starts watching a temporary directory for changes
4. **Demonstrates File Operations**:
   - Creates a new file
   - Modifies the file
   - Creates another file
   - Creates a subdirectory
   - Deletes a file
5. **Shows GetFileChange**: Demonstrates one-time change detection
6. **Cleanup**: Properly stops monitoring and deletes the session

## Expected Output

The example will show real-time detection of file changes with output like:

```
=== AgentBay Watch Directory Example ===
✅ AgentBay client initialized
✅ Session created with ID: sess_xxxxxxxxxx
📁 Created test directory: /tmp/agentbay-watch-example-xxxxxx
👀 Starting to watch directory: /tmp/agentbay-watch-example-xxxxxx
📊 Polling interval: 500ms
⏳ Waiting for monitoring to start...

🎬 Demonstrating file operations...
📝 Creating a new file...

🔍 Detected 1 file changes:
  - FileChangeEvent(eventType='create', path='/tmp/agentbay-watch-example-xxxxxx/example.txt', pathType='file')

✏️  Modifying the file...

🔍 Detected 1 file changes:
  - FileChangeEvent(eventType='modify', path='/tmp/agentbay-watch-example-xxxxxx/example.txt', pathType='file')

📄 Creating another file...
📂 Creating a subdirectory...
🗑️  Deleting a file...

🔍 Demonstrating GetFileChange method...
📊 GetFileChange result:
  - Request ID: req_xxxxxxxxxx
  - Events count: X
  - File change details:
    • Modified files: [...]
    • Created files: [...]
    • Deleted files: [...]

⏹️  Stopping directory monitoring...
✅ Watch directory example completed successfully!
```

## Code Structure

### Key Components

1. **Session Management**:
   ```go
   sessionParams := &agentbay.CreateSessionParams{
       ImageId: "code_latest",
   }
   sessionResult, err := agentBay.Create(sessionParams)
   ```

2. **Directory Monitoring**:
   ```go
   callback := func(events []*filesystem.FileChangeEvent) {
       // Handle detected changes
   }
   
   stopChan := make(chan struct{})
   go func() {
       err := fileSystem.WatchDirectory(testDir, callback, 1000, stopChan)
   }()
   ```

3. **One-time Change Detection**:
   ```go
   result, err := fileSystem.GetFileChange(testDir)
   if err == nil && result.HasChanges() {
       // Process detected changes
   }
   ```

4. **Proper Cleanup**:
   ```go
   defer func() {
       _, err := agentBay.Delete(session)
   }()
   
   close(stopChan) // Stop monitoring
   ```

## Error Handling

The example includes comprehensive error handling for:
- AgentBay client initialization
- Session creation and deletion
- File operations
- Directory monitoring setup

## Performance Considerations

- **Polling Interval**: Set to 1000ms (1 second) for demonstration
- **Resource Management**: Proper cleanup prevents memory leaks
- **Callback Efficiency**: Keep callback functions lightweight

## Customization

You can modify the example to:
- Change the polling interval (minimum 100ms)
- Filter specific file types in the callback
- Monitor multiple directories simultaneously
- Add custom logging or processing logic

## Troubleshooting

### Common Issues

1. **API Key Not Set**: Ensure `AGENTBAY_API_KEY` environment variable is set
2. **Permission Errors**: Make sure the application has write access to `/tmp`
3. **Network Issues**: Check internet connectivity for AgentBay API access

### Debug Tips

- Enable verbose logging by adding debug prints
- Check the session ID in AgentBay dashboard
- Verify file operations are actually creating/modifying files
- Monitor system resources if running for extended periods 