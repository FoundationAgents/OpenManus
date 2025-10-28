# Code Module - Python

The Code module handles code execution operations in the AgentBay cloud environment.

## 📖 Related Tutorial

- [Code Execution Guide](../../../docs/guides/codespace/code-execution.md) - Detailed tutorial on executing code in cloud environments

## Methods

### run_code

Executes code in a specified programming language with a timeout.

```python
run_code(code: str, language: str, timeout_s: int = 60) -> CodeExecutionResult
```

**Parameters:**
- `code` (str): The code to execute.
- `language` (str): The programming language of the code. Must be either 'python' or 'javascript'.
- `timeout_s` (int, optional): The timeout for the code execution in seconds. Default is 60s. Note: Due to gateway limitations, each request cannot exceed 60 seconds.

**Returns:**
- `CodeExecutionResult`: A result object containing success status, execution result, error message if any, and request ID.

**Important Note:**
The `run_code` method requires a session created with the `code_latest` image to function properly. If you encounter errors indicating that the tool is not found, make sure to create your session with `image_id="code_latest"` in the `CreateSessionParams`.

**Usage Example:**

```python
import os
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

# Initialize AgentBay with API key
api_key = os.getenv("AGENTBAY_API_KEY")
agent_bay = AgentBay(api_key=api_key)

# Create a session with code_latest image
params = CreateSessionParams(image_id="code_latest")
session_result = agent_bay.create(params)
if session_result.success:
    session = session_result.session
else:
    print(f"Failed to create session: {session_result.error_message}")
    exit(1)

# Execute Python code
python_code = """
print("Hello from Python!")
result = 2 + 3
print(f"Result: {result}")
"""

code_result = session.code.run_code(python_code, "python")
if code_result.success:
    print(f"Python code output:\n{code_result.result}")
    # Expected output:
    # Hello from Python!
    # Result: 5
    print(f"Request ID: {code_result.request_id}")
    # Expected: A valid UUID-format request ID
else:
    print(f"Code execution failed: {code_result.error_message}")

# Execute JavaScript code
js_code = """
console.log("Hello from JavaScript!");
const result = 2 + 3;
console.log("Result:", result);
"""

js_result = session.code.run_code(js_code, "javascript", timeout_s=30)
if js_result.success:
    print(f"JavaScript code output:\n{js_result.result}")
    # Expected output:
    # Hello from JavaScript!
    # Result: 5
    print(f"Request ID: {js_result.request_id}")
    # Expected: A valid UUID-format request ID
else:
    print(f"Code execution failed: {js_result.error_message}")
```

## Error Handling

The run_code method returns a CodeExecutionResult with `success=False` if:
- The specified language is not supported (only 'python' and 'javascript' are supported)
- The code execution fails in the cloud environment
- Network or API communication errors occur

In these cases, the `error_message` field will contain details about the failure.

## Types

### CodeExecutionResult

```python
class CodeExecutionResult(ApiResponse):
    def __init__(
        self,
        request_id: str = "",
        success: bool = False,
        result: str = "",
        error_message: str = "",
    ):
        # Inherits request_id from ApiResponse
        self.success = success        # Whether the operation was successful
        self.result = result          # The execution result/output
        self.error_message = error_message  # Error message if failed
``` 