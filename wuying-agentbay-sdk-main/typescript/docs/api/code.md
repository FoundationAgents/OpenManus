# Code Module - TypeScript

The Code module handles code execution operations in the AgentBay cloud environment.

## 📖 Related Tutorial

- [Code Execution Guide](../../../docs/guides/codespace/code-execution.md) - Detailed tutorial on executing code in cloud environments

## Methods

### runCode

Executes code in a specified programming language with a timeout.

```typescript
runCode(code: string, language: string, timeoutS: number = 60): Promise<CodeExecutionResult>
```

**Parameters:**
- `code` (string): The code to execute.
- `language` (string): The programming language of the code. Must be either 'python' or 'javascript'.
- `timeoutS` (number, optional): The timeout for the code execution in seconds. Default is 60s. Note: Due to gateway limitations, each request cannot exceed 60 seconds.

**Returns:**
- `Promise<CodeExecutionResult>`: A promise that resolves to a result object containing success status, execution result, error message if any, and request ID.

**Important Note:**
The `runCode` method requires a session created with the `code_latest` image to function properly. If you encounter errors indicating that the tool is not found, make sure to create your session with `imageId: "code_latest"` in the session creation parameters.

**Usage Example:**

```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

async function main() {
    // Initialize AgentBay with API key
    const apiKey = process.env.AGENTBAY_API_KEY!;
    const agentBay = new AgentBay({ apiKey });

    // Create a session with code_latest image
    const sessionResult = await agentBay.create({
        imageId: "code_latest"
    });
    if (!sessionResult.success) {
        console.error(`Failed to create session: ${sessionResult.errorMessage}`);
        return;
    }
    const session = sessionResult.session;

    // Execute Python code
    const pythonCode = `
print("Hello from Python!")
result = 2 + 3
print(f"Result: {result}")
`;

    const codeResult = await session.code.runCode(pythonCode, "python");
    if (codeResult.success) {
        console.log(`Python code output:\n${codeResult.result}`);
        // Expected output:
        // Hello from Python!
        // Result: 5
        console.log(`Request ID: ${codeResult.requestId}`);
        // Expected: A valid UUID-format request ID
    } else {
        console.error(`Code execution failed: ${codeResult.errorMessage}`);
    }

    // Execute JavaScript code
    const jsCode = `
console.log("Hello from JavaScript!");
const result = 2 + 3;
console.log("Result:", result);
`;

    const jsResult = await session.code.runCode(jsCode, "javascript", 30);
    if (jsResult.success) {
        console.log(`JavaScript code output:\n${jsResult.result}`);
        // Expected output:
        // Hello from JavaScript!
        // Result: 5
        console.log(`Request ID: ${jsResult.requestId}`);
        // Expected: A valid UUID-format request ID
    } else {
        console.error(`Code execution failed: ${jsResult.errorMessage}`);
    }
}

main().catch(console.error);
```

## Error Handling

The runCode method returns a CodeExecutionResult with `success: false` if:
- The specified language is not supported (only 'python' and 'javascript' are supported)
- The code execution fails in the cloud environment
- Network or API communication errors occur

In these cases, the `errorMessage` field will contain details about the failure.

## Types

### CodeExecutionResult

```typescript
interface CodeExecutionResult {
    requestId: string;      // Unique identifier for the API request
    success: boolean;       // Whether the operation was successful
    result: string;         // The execution result/output
    errorMessage?: string;  // Error message if the operation failed
}
``` 