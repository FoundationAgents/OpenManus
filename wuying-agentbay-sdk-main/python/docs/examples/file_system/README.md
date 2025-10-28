# FileSystem Operations Example

This example demonstrates how to use the FileSystem features of the Wuying AgentBay SDK. It covers a comprehensive set of file system operations, including:

- Basic file reading and writing
- Directory creation and listing
- File information retrieval
- File editing and moving
- File searching
- Multiple file reading
- Large file operations with automatic chunking

This example is particularly useful for understanding how to work with files and directories efficiently in the AgentBay cloud environment.

## Features Demonstrated

### Basic File Operations
- **File Writing**: Create new files with content
- **File Reading**: Read file contents
- **File Appending**: Add content to existing files

### Directory Operations
- **Directory Creation**: Create new directories
- **Directory Listing**: List contents of directories

### File Information
- **File Info Retrieval**: Get detailed information about files (size, permissions, etc.)

### File Manipulation
- **File Editing**: Edit specific parts of file content
- **File Moving**: Move files between directories

### Search Operations
- **File Searching**: Search for files containing specific patterns

### Multiple File Operations
- **Multiple File Reading**: Read multiple files in a single operation

### Large File Operations
- **Large File Writing**: Write files larger than the default API size limits using automatic chunking
- **Large File Reading**: Read large files using automatic chunking
- **Custom Chunk Size**: Specify custom chunk sizes for both reading and writing operations
- **Performance Measurement**: Measure and compare operation times with different chunk sizes

## Prerequisites

- Python 3.10 or later
- Wuying AgentBay SDK installed:
  ```bash
  pip install wuying-agentbay-sdk
  ```

## Running the Example

```bash
cd file_system
python main.py
```

Make sure you have set the `AGENTBAY_API_KEY` environment variable or replace the placeholder in the code with your actual API key.

## How It Works

The example demonstrates the following workflow:

1. **Session Creation**: Creates a new session with the specified image ID
2. **Basic File Operations**: Demonstrates writing, reading, and appending to files
3. **Directory Operations**: Shows how to create directories and list their contents
4. **File Information**: Retrieves and displays detailed file information
5. **File Editing**: Demonstrates how to edit specific parts of a file
6. **File Moving**: Shows how to move files between directories
7. **File Searching**: Searches for files containing specific patterns
8. **Multiple File Reading**: Reads multiple files in a single operation
9. **Large File Operations**: Demonstrates reading and writing large files with both default and custom chunk sizes
10. **Content Verification**: Verifies that file operations maintain content integrity
11. **Performance Comparison**: Measures and reports the time taken for large file operations

Each section of the example is clearly marked and includes verification steps to ensure operations are working correctly.

## API Reference

For more detailed information on the FileSystem API methods, refer to the SDK documentation.