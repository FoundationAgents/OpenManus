# VPC Session Example

This example demonstrates how to create and use VPC (Virtual Private Cloud) sessions with the AgentBay SDK.

## Overview

VPC sessions provide enhanced security and networking capabilities by running your cloud sessions within a private network environment. This example shows how to create a VPC session and use its available modules.

## Running the Example

1. Ensure you have the AgentBay SDK installed
2. Set the `AGENTBAY_API_KEY` environment variable with your valid API key
3. Run the example:

```bash
cd docs/examples/python/vpc_session
python main.py
```

## What the Example Does

1. Initializes the AgentBay client with your API key
2. Creates a new VPC session with specific parameters
3. Tests FileSystem operations by writing and reading a file
4. Tests Command operations by executing system commands
5. Cleans up by deleting the session

## Key Concepts

- **VPC Session Creation**: VPC sessions are created by setting the `is_vpc` parameter to `True`
- **Module Availability**: VPC sessions have limited module availability compared to standard sessions
- **Resource Management**: VPC sessions should be properly deleted when no longer needed
- **Security**: VPC sessions provide network isolation for sensitive operations

## Available Modules in VPC Sessions

1. **FileSystem**: File and directory operations
2. **Command**: Command execution
3. **System Tools**: Specialized system-level tools
4. **Browser Tools**: Browser automation capabilities

## Next Steps

Try modifying the example to:
- Use context synchronization with VPC sessions
- Test different command executions
- Implement error handling for unavailable modules