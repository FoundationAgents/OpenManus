# Command Execution Guide

This guide covers command execution capabilities in AgentBay SDK. The command module allows you to execute shell commands and system operations in cloud sessions.

## 📋 Table of Contents

- [Overview](#overview)
- [Basic Command Execution](#basic-command-execution)
- [Command with Timeout](#command-with-timeout)
- [Working with Command Output](#working-with-command-output)
- [Advanced Patterns](#advanced-patterns)

<a id="overview"></a>
## 🎯 Overview

The `session.command` module provides programmatic access to execute shell commands in cloud sessions. This is useful for:

- **System Operations** - Run shell commands, manage processes
- **Environment Setup** - Install packages, configure environments
- **File Processing** - Use command-line tools for file operations
- **Automation** - Automate complex workflows

### Command Module Features

- ✅ Synchronous command execution
- ✅ Timeout support
- ✅ Output and error capture
- ✅ Exit code handling

<a id="basic-command-execution"></a>
## 💻 Basic Command Execution

### Simple Commands

```python
from agentbay import AgentBay

agent_bay = AgentBay(api_key="your-api-key")
result = agent_bay.create()

if result.success:
    session = result.session
    
    cmd_result = session.command.execute_command("ls -la /tmp")
    if cmd_result.success:
        print("Output:", cmd_result.output)
    else:
        print("Command failed:", cmd_result.error_message)
    
    agent_bay.delete(session)
else:
    print("Failed to create session:", result.error_message)

# Output example:
# Output: total 140
# drwxrwxrwt 21 root   root    4096 Oct  2 14:57 .
# drwxr-xr-x 19 root   root    4096 Oct  2 14:20 ..
# -rw-------  1 root   root       0 Oct  2 14:20 example.lock
# srwxr-xr-x  1 root   root       0 Oct  2 14:20 service.sock
# ...
```

### Command with Arguments

```python
session = agent_bay.create().session

commands = [
    "echo 'Hello from cloud'",
    "pwd",
    "whoami",
    "uname -a"
]

for cmd in commands:
    result = session.command.execute_command(cmd)
    if result.success:
        print(f"{cmd} -> {result.output.strip()}")
    else:
        print(f"{cmd} failed: {result.error_message}")

agent_bay.delete(session)

# Output example:
# echo 'Hello from cloud' -> Hello from cloud
# pwd -> /home/user
# whoami -> user
# uname -a -> Linux hostname 5.15.0-125-generic #135-Ubuntu SMP x86_64 x86_64 x86_64 GNU/Linux
```

<a id="command-with-timeout"></a>
## ⏱️ Command with Timeout

### Setting Execution Timeout

```python
session = agent_bay.create().session

# Command completes within timeout
result = session.command.execute_command("sleep 3", timeout_ms=5000)
if result.success:
    print("Command completed within timeout")
else:
    print("Command timed out or failed:", result.error_message)

# Command exceeds timeout
result = session.command.execute_command("sleep 10", timeout_ms=2000)
if result.success:
    print("Command completed")
else:
    print("Command timed out:", result.error_message)

agent_bay.delete(session)

# Output example:
# Command completed within timeout
# Command timed out: Error in response: Execution failed. Error code:-1 Error message: [timeout]
```

<a id="working-with-command-output"></a>
## 📤 Working with Command Output

### Capturing Output

```python
session = agent_bay.create().session

result = session.command.execute_command("df -h")
if result.success:
    print("Full output:")
    print(result.output)
    
    lines = result.output.strip().split('\n')
    print(f"Found {len(lines)} filesystems")
else:
    print("Command failed:", result.error_message)

agent_bay.delete(session)

# Output example:
# Full output:
# Filesystem      Size  Used Avail Use% Mounted on
# tmpfs           756M  2.9M  753M   1% /run
# /dev/vda3        99G   23G   72G  24% /
# tmpfs           3.7G     0  3.7G   0% /dev/shm
# tmpfs           5.0M     0  5.0M   0% /run/lock
# ...
# Found 8 filesystems
```

<a id="advanced-patterns"></a>
## 🔧 Advanced Patterns

### Command Chaining

```python
session = agent_bay.create().session

result = session.command.execute_command(
    "mkdir -p /tmp/test && cd /tmp/test && echo 'Hello' > file.txt && cat file.txt"
)
if result.success:
    print("Output:", result.output)

agent_bay.delete(session)

# Output example:
# Output: Hello
```

## 📚 Related Documentation

- [Code Execution (CodeSpace)](../../codespace/code-execution.md) - Python, JavaScript code execution
- [File Operations](file-operations.md) - File handling and management
- [Session Management](session-management.md) - Session lifecycle

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../README.md)

Happy automating with AgentBay! 🚀
