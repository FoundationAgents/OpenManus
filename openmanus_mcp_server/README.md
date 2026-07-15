# OpenManus MCP Server

Model Context Protocol (MCP) server that exposes OpenManus autonomous agent capabilities to VS Code extensions (Codex, Antigravity) and other MCP clients.

## Features

- **11 MCP Tools**: Task execution, file operations, code execution, web search, git operations, and more
- **4 MCP Resources**: Configuration, prompt templates
- **5 MCP Prompts**: Code review, bug fix, feature implementation, refactoring, test generation
- **Dual Transport**: Stdio (default) and SSE (for remote access)
- **Task Management**: Full lifecycle with status tracking and cancellation

## Installation

### Prerequisites

- Python 3.10+
- Node.js (for using developer validation tools/MCP Inspector)

### Install Dependencies

From the workspace root directory:
```bash
pip install -r openmanus_mcp_server/requirements.txt
```

## Usage

You can run, test, and debug the MCP server completely standalone using the standard transports or the official **MCP Developer tools**.

### 🛠️ 1. Standalone Debugging via MCP Inspector (Highly Recommended)

The Model Context Protocol team provides a web-based **MCP Inspector** utility. This lets you inspect and trigger tools interactively in a beautiful graphical interface without any IDE integration:

```bash
npx @modelcontextprotocol/inspector python -m openmanus_mcp_server
```

When you run this command:
1. It launches a local web server at `http://localhost:5173` (or opens it automatically).
2. It establishes a standard stdio connection with the Python server.
3. You can click on **Tools**, fill out the input arguments (like `task` inside `openmanus_run_task`), click **Run Tool**, and watch the live OpenManus agent run directly in your terminal!

---

### 📥 2. Stdio Transport Mode (For IDEs and parent-child shells)

To run the server in standard I/O mode:
```bash
python -m openmanus_mcp_server
```

---

### 🌐 3. SSE Transport Mode (HTTP Web Server)

To host the MCP server as a network-accessible web service:
```bash
python -m openmanus_mcp_server --sse --port 8765
```

This launches a FastAPI application at `http://localhost:8765`:
* **SSE Endpoint**: `http://localhost:8765/sse` (to establish the stream connection)
* **Message POST Endpoint**: `http://localhost:8765/messages/` (to send JSON-RPC payloads)

---

### ⚙️ 4. Custom Configuration Integration

To execute with a specific OpenManus config file:
```bash
python -m openmanus_mcp_server --config config/config.toml
```

## Available Tools

| Tool | Description |
|------|-------------|
| `openmanus_run_task` | Execute an autonomous task |
| `openmanus_get_status` | Get task status |
| `openmanus_cancel_task` | Cancel a running task |
| `openmanus_list_tasks` | List all tasks |
| `openmanus_read_output` | Read task output |
| `openmanus_code_execute` | Execute code in sandbox |
| `openmanus_file_read` | Read file contents |
| `openmanus_file_write` | Write file contents |
| `openmanus_web_search` | Search the web |
| `openmanus_git_operation` | Execute Git operations |
| `openmanus_list_files` | List directory contents |

## Configuration

Create a config file (`~/.openmanus/config.yaml`):

```yaml
llm:
  model: gpt-4o
  api_key: sk-...

agent:
  max_steps: 30
  output_dir: ~/.openmanus/output
```

## Architecture

```
MCP Client (VS Code Extension)
    ↓ (stdio or SSE)
OpenManus MCP Server
    ↓
OpenManus Agent Engine
    ↓
LLM Provider / Browser / File System
```

## Development

```bash
# Run in development mode
python -m openmanus_mcp_server

# Run tests
pytest tests/

# Lint
flake8 openmanus_mcp_server/
mypy openmanus_mcp_server/
```

## Security

- API keys stored in memory only
- Path traversal protection
- Workspace boundary enforcement
- SSE requires authentication (when enabled)

## License

MIT

## References

- [MCP Specification](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [OpenManus](https://github.com/mannaandpoem/OpenManus)
