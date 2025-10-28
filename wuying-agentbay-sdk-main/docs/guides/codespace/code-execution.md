# Code Execution Guide (CodeSpace)

This guide covers code execution capabilities in AgentBay SDK's CodeSpace environment. CodeSpace provides a dedicated development environment optimized for running code in Python and JavaScript.

## 📋 Table of Contents

- [Overview](#overview)
- [CodeSpace Environment](#codespace-environment)
- [Python Code Execution](#python-code-execution)
- [JavaScript Code Execution](#javascript-code-execution)
- [Code Execution with File I/O](#code-execution-with-file-io)
- [Best Practices](#best-practices)

<a id="overview"></a>
## 🎯 Overview

CodeSpace is AgentBay's development-focused environment that provides:

- **Multi-language Support** - Run Python and JavaScript/Node.js code
- **Isolated Execution** - Secure, containerized code execution
- **Development Tools** - Pre-installed interpreters and development utilities
- **File Operations** - Read and write files for script execution

<a id="codespace-environment"></a>
## 🔧 CodeSpace Environment

### Creating a CodeSpace Session

To use code execution features, create a session with the `code_latest` image:

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

agent_bay = AgentBay(api_key="your-api-key")

session_params = CreateSessionParams(image_id="code_latest")
result = agent_bay.create(session_params)

if result.success:
    session = result.session
    print(f"CodeSpace session created: {session.session_id}")
else:
    print(f"Failed to create session: {result.error_message}")
```

**Important:** The `run_code()` method requires `image_id="code_latest"` when creating the session.

<a id="python-code-execution"></a>
## 🐍 Python Code Execution

### Basic Python Execution

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

agent_bay = AgentBay(api_key="your-api-key")

session_params = CreateSessionParams(image_id="code_latest")
result = agent_bay.create(session_params)

if result.success:
    session = result.session
    
    code = """
import os
import sys
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print("Hello from AgentBay!")
"""
    
    result = session.code.run_code(code, "python")
    if result.success:
        print("Output:", result.result)
        # Output: Python version: 3.11.2 (main, Apr 28 2025, 14:11:48) [GCC 12.2.0]
        #         Current directory: /workspace
        #         Hello from AgentBay!
    else:
        print("Execution failed:", result.error_message)
    
    agent_bay.delete(session)
```

### Python with Calculations

```python
session_params = CreateSessionParams(image_id="code_latest")
result = agent_bay.create(session_params)

if result.success:
    session = result.session
    
    code = """
import math

# Calculate factorial
def factorial(n):
    return math.factorial(n)

# Fibonacci sequence
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(f"Factorial of 10: {factorial(10)}")
print(f"Fibonacci of 10: {fibonacci(10)}")

# List comprehension
squares = [x**2 for x in range(1, 11)]
print(f"Squares: {squares}")
"""
    
    result = session.code.run_code(code, "python")
    if result.success:
        print("Output:", result.result)
        # Output: Factorial of 10: 3628800
        #         Fibonacci of 10: 55
        #         Squares: [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]
    
    agent_bay.delete(session)
```

<a id="javascript-code-execution"></a>
## 🟨 JavaScript Code Execution

### Node.js Code Execution

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

agent_bay = AgentBay(api_key="your-api-key")

session_params = CreateSessionParams(image_id="code_latest")
result = agent_bay.create(session_params)

if result.success:
    session = result.session
    
    js_code = """
const fs = require('fs');
const path = require('path');

console.log('Node.js version:', process.version);
console.log('Current directory:', process.cwd());

// Create a simple file
fs.writeFileSync('/tmp/hello.txt', 'Hello from Node.js!');
console.log('File created successfully');
"""
    
    result = session.code.run_code(js_code, "javascript")
    if result.success:
        print("Output:", result.result)
        # Output: Node.js version: v18.20.5
        #         Current directory: /workspace
        #         File created successfully
    else:
        print("Execution failed:", result.error_message)
    
    agent_bay.delete(session)
```

### JavaScript with Data Processing

```python
session_params = CreateSessionParams(image_id="code_latest")
result = agent_bay.create(session_params)

if result.success:
    session = result.session
    
    js_code = """
// Array operations
const numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

const sum = numbers.reduce((a, b) => a + b, 0);
const avg = sum / numbers.length;
const squares = numbers.map(x => x * x);

console.log('Numbers:', numbers);
console.log('Sum:', sum);
console.log('Average:', avg);
console.log('Squares:', squares);

// Object manipulation
const data = {
    name: 'AgentBay',
    version: '1.0',
    features: ['Python', 'JavaScript', 'File I/O']
};

console.log('\\nData:', JSON.stringify(data, null, 2));
"""
    
    result = session.code.run_code(js_code, "javascript")
    if result.success:
        print("Output:", result.result)
        # Output: Numbers: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        #         Sum: 55
        #         Average: 5.5
        #         Squares: [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]
        #         
        #         Data: {
        #           "name": "AgentBay",
        #           "version": "1.0",
        #           "features": [
        #             "Python",
        #             "JavaScript",
        #             "File I/O"
        #           ]
        #         }
    
    agent_bay.delete(session)
```

<a id="code-execution-with-file-io"></a>
## 📁 Code Execution with File I/O

### Writing and Executing Scripts

```python
from agentbay import AgentBay

agent_bay = AgentBay(api_key="your-api-key")
result = agent_bay.create()

if result.success:
    session = result.session
    
    script_content = """
import json
import sys

data = {
    'message': 'Hello from uploaded script',
    'args': sys.argv[1:] if len(sys.argv) > 1 else []
}

with open('/tmp/output.json', 'w') as f:
    json.dump(data, f, indent=2)

print(json.dumps(data, indent=2))
"""
    
    write_result = session.file_system.write_file("/tmp/script.py", script_content)
    if write_result.success:
        print("Script uploaded successfully")
        
        exec_result = session.command.execute_command("python3 /tmp/script.py arg1 arg2")
        if exec_result.success:
            print("Script output:", exec_result.output)
            # Script output: {
            #   "message": "Hello from uploaded script",
            #   "args": [
            #     "arg1",
            #     "arg2"
            #   ]
            # }
            
            output_result = session.file_system.read_file("/tmp/output.json")
            if output_result.success:
                print("Output file content:", output_result.content)
                # Output file content: {
                #   "message": "Hello from uploaded script",
                #   "args": [
                #     "arg1",
                #     "arg2"
                #   ]
                # }
        else:
            print("Execution failed:", exec_result.error_message)
    else:
        print("Failed to write script:", write_result.error_message)
    
    agent_bay.delete(session)
```

### Multi-file Projects

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

agent_bay = AgentBay(api_key="your-api-key")

session_params = CreateSessionParams(image_id="code_latest")
result = agent_bay.create(session_params)

if result.success:
    session = result.session
    
    session.file_system.create_directory("/workspace/myproject")
    
    main_py = """
from utils import greet

if __name__ == "__main__":
    print(greet("AgentBay"))
"""
    
    utils_py = """
def greet(name):
    return f"Hello, {name}!"
"""
    
    session.file_system.write_file("/workspace/myproject/main.py", main_py)
    session.file_system.write_file("/workspace/myproject/utils.py", utils_py)
    
    result = session.command.execute_command("cd /workspace/myproject && python3 main.py")
    if result.success:
        print("Project output:", result.output)
        # Project output: Hello, AgentBay!
    else:
        print("Execution failed:", result.error_message)
    
    agent_bay.delete(session)
```

<a id="best-practices"></a>
## 💡 Best Practices

### 1. Use Timeout for Long-Running Code

The default timeout for `run_code()` is 60 seconds. **Note: Due to gateway limitations, each request cannot exceed 60 seconds.**

```python
# Default timeout is 60 seconds
result = session.code.run_code(code, "python")

# You can specify a custom timeout (max 60 seconds)
result = session.code.run_code(code, "python", timeout_s=60)
```

### 2. Use Standard Library Only

CodeSpace comes with Python and Node.js standard libraries pre-installed. For best performance and reliability, use only built-in modules:

**Python**: `os`, `sys`, `json`, `math`, `datetime`, `re`, etc.  
**JavaScript**: `fs`, `path`, `os`, `crypto`, etc.

## 📚 Related Documentation

- [File Operations](../common-features/basics/file-operations.md) - File handling and management
- [Session Management](../common-features/basics/session-management.md) - Session lifecycle and configuration
- [Command Execution](../common-features/basics/command-execution.md) - Shell command execution

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../README.md)

Happy coding with AgentBay CodeSpace! 🚀
