# Command Class API Reference

The `Command` class provides methods for executing commands within a session in the AgentBay cloud environment.

## 📖 Related Tutorial

- [Command Execution Guide](../../../docs/guides/common-features/basics/command-execution.md) - Detailed tutorial on executing shell commands

## Methods

### execute_command

Executes a shell command in the cloud environment.

```python
execute_command(command: str, timeout_ms: int = 1000) -> CommandResult
```

**Parameters:**
- `command` (str): The command to execute.
- `timeout_ms` (int, optional): The timeout for the command execution in milliseconds. Default is 1000ms.

**Returns:**
- `CommandResult`: A result object containing the command output, success status, request ID, and error message if any.

**Usage Example:**

```python
import os
from agentbay import AgentBay

# Initialize AgentBay with API key
api_key = os.getenv("AGENTBAY_API_KEY")
ab = AgentBay(api_key=api_key)

# Create a session
session_result = ab.create()
session = session_result.session

# Execute a command with default timeout (1000ms)
result = session.command.execute_command("ls -la")
if result.success:
    print(f"Command output:\n{result.output}")
    # Expected output: Directory listing showing files and folders
    print(f"Request ID: {result.request_id}")
    # Expected: A valid UUID-format request ID
else:
    print(f"Command execution failed: {result.error_message}")

# Execute a command with custom timeout (5000ms)
result_with_timeout = session.command.execute_command("sleep 2 && echo 'Done'", timeout_ms=5000)
if result_with_timeout.success:
    print(f"Command output: {result_with_timeout.output}")
    # Expected output: "Done\n"
    # The command waits 2 seconds then outputs "Done"
else:
    print(f"Command execution failed: {result_with_timeout.error_message}")

# Note: If a command exceeds its timeout, it will return an error
# Example: session.command.execute_command("sleep 3", timeout_ms=1000)
# Returns error: "Error in response: Execution failed. Error code:-1 Error message: [timeout]"
```

## Related Resources

- [Session Class](session.md): The session class that provides access to the Command class.
- [Code Class](code.md): For executing Python and JavaScript code.
- [FileSystem Class](filesystem.md): Provides methods for file operations within a session.
