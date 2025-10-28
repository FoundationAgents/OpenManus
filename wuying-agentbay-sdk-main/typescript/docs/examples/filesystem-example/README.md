# Filesystem Operations Example

This example demonstrates how to use the AgentBay SDK to perform various filesystem operations within a session.

## Features Demonstrated

- Directory Operations:
  - Creating directories
  - Listing directory contents

- File Operations:
  - Writing files
  - Reading files
  - Getting file information
  - Editing file content
  - Moving/renaming files
  - Searching for files

- File Transfer Operations:
  - Uploading files from local to remote environment
  - Downloading files from remote to local environment
  - Progress tracking during file transfers

## Running the Examples

Make sure you have set your AgentBay API key as an environment variable:

```bash
export AGENTBAY_API_KEY="your-api-key-here"
```

### Basic Filesystem Operations

```bash
cd filesystem-example
npx ts-node filesystem-example.ts
```

### Directory Monitoring

```bash
cd filesystem-example
npx ts-node watch-directory-example.ts
```

### File Transfer Operations

```bash
cd filesystem-example
npx ts-node filesystem-filetransfer-example.ts
```

## Note

The example uses the `/tmp` directory for all operations to ensure it has the necessary permissions. Some operations might not be supported in all session types or environments. The example includes error handling to handle such cases gracefully.

File transfer operations require proper session context configuration for optimal performance. The examples demonstrate best practices for handling file transfers with progress tracking and error handling.