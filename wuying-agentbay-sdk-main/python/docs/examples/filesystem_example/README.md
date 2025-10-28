# FileSystem Examples

This directory contains examples demonstrating the FileSystem functionality in the AgentBay SDK for Python.

## Examples

### Watch Directory Example ([watch_directory_example.py](./watch_directory_example.py))

Demonstrates how to monitor file changes in a directory:

- Creating directories for monitoring
- Setting up file change monitoring with callbacks
- Performing file operations to trigger events
- Processing different types of file events (create, modify, delete)
- Proper resource cleanup

### File Transfer Example ([file_transfer_example.py](./file_transfer_example.py))

Demonstrates file upload and download operations:

- Creating contexts and sessions with file transfer capabilities
- Using the simplified FileSystem API for file transfers
- Uploading files from local storage to the cloud
- Downloading files from the cloud to local storage
- Tracking file transfer progress with callbacks
- Verifying file content integrity after transfers
- Proper resource cleanup

## Running the Examples

1. Make sure you have installed the AgentBay SDK:

```bash
pip install wuying-agentbay-sdk
```

2. Set your API key as an environment variable (recommended):

```bash
export AGENTBAY_API_KEY=your_api_key_here
```

3. Run an example:

```bash
python watch_directory_example.py
```

or

```bash
python file_transfer_example.py
```

## Code Explanation

### Watch Directory Example

The watch directory example demonstrates real-time file monitoring capabilities:

1. Initialize the AgentBay client with an API key
2. Create a session with a suitable image
3. Create a test directory to monitor
4. Set up monitoring with a callback function to handle file events
5. Perform various file operations to trigger events
6. Process and display the detected file changes
7. Clean up resources properly

### File Transfer Example

The file transfer example demonstrates uploading and downloading files:

1. Initialize the AgentBay client with an API key
2. Create a context for file operations
3. Create a browser session with context synchronization
4. Create test files for upload
5. Upload files to the cloud using the simplified API
6. Download files from the cloud to local storage
7. Track progress during transfers
8. Verify file content integrity
9. Clean up resources properly

## API Reference

For detailed information about the FileSystem API, see the [FileSystem API Reference](../../api/filesystem.md).
