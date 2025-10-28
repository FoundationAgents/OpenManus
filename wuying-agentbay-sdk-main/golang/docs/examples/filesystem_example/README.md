# FileSystem Example

This example demonstrates how to use the AgentBay SDK's FileSystem module to perform various file operations in the cloud environment.

## Features Demonstrated

- Creating directories
- Writing files
- Reading files
- Getting file information
- Listing directory contents
- Editing files
- Searching for files
- Moving/renaming files

## Prerequisites

- Go 1.16 or later
- AgentBay API key (set as `AGENTBAY_API_KEY` environment variable)

## Running the Example

1. Set your API key:
   ```bash
   export AGENTBAY_API_KEY="your-api-key-here"
   ```

2. Run the example:
   ```bash
   go run main.go
   ```

## Expected Output

The example will create a session, perform various file system operations, and clean up afterwards. 
You should see output showing the results of each operation, including:

- Directory creation
- File creation and verification
- File content reading and display
- File information retrieval
- Directory listing
- File editing and content verification
- File search results
- File move/rename operation

## Notes

- All resources are cleaned up when the example completes
- The session is automatically deleted at the end of the example 