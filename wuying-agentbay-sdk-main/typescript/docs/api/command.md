# Command Class API Reference

The `Command` class provides methods for executing commands within a session in the AgentBay cloud environment.

## 📖 Related Tutorial

- [Command Execution Guide](../../../docs/guides/common-features/basics/command-execution.md) - Detailed tutorial on executing shell commands

## Methods

### executeCommand

Executes a shell command in the cloud environment.

```typescript
executeCommand(command: string, timeoutMs: number = 1000): Promise<CommandResult>
```

**Parameters:**
- `command` (string): The command to execute.
- `timeoutMs` (number, optional): The timeout for the command execution in milliseconds. Default is 1000ms.

**Returns:**
- `Promise<CommandResult>`: A promise that resolves to a result object containing the command output, success status, and request ID.

**CommandResult Interface:**
```typescript
interface CommandResult {
    requestId: string;      // Unique identifier for the API request
    success: boolean;       // Whether the operation was successful
    output: string;         // The command output (stdout)
    errorMessage?: string;  // Error message if the operation failed
}
```

**Note:** The `output` field contains the standard output (stdout) of the executed command. Error output (stderr) is typically included in the `errorMessage` field when the command fails.

**Usage Example:**

```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

async function main() {
    // Initialize AgentBay with API key
    const apiKey = process.env.AGENTBAY_API_KEY!;
    const ab = new AgentBay({ apiKey });

    // Create a session
    const sessionResult = await ab.create();
    const session = sessionResult.session;

    try {
        // Execute a command with default timeout (1000ms)
        const result = await session.command.executeCommand("ls -la");
        if (result.success) {
            console.log(`Command output:\n${result.output}`);
            // Expected output: Directory listing showing files and folders
            console.log(`Request ID: ${result.requestId}`);
            // Expected: A valid UUID-format request ID
        } else {
            console.error(`Command execution failed: ${result.errorMessage}`);
        }

        // Execute a command with custom timeout (5000ms)
        const resultWithTimeout = await session.command.executeCommand(
            "sleep 2 && echo 'Done'", 
            5000
        );
        if (resultWithTimeout.success) {
            console.log(`Command output: ${resultWithTimeout.output}`);
            // Expected output: "Done\n"
            // The command waits 2 seconds then outputs "Done"
        } else {
            console.error(`Command execution failed: ${resultWithTimeout.errorMessage}`);
        }

        // Note: If a command exceeds its timeout, it will return an error
        // Example: await session.command.executeCommand("sleep 3", 1000)
        // Returns error in errorMessage field
    } catch (error) {
        console.error('Error:', error);
    }
}

main().catch(console.error);
```

## Related Resources

- [Session Class](session.md): The session class that provides access to the Command class.
- [Code Class](code.md): For executing Python and JavaScript code.
- [FileSystem Class](filesystem.md): Provides methods for file operations within a session.

