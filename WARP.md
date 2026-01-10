# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

OpenManus is an open-source AI agent framework built on Python 3.12+ that supports multiple execution modes, tool calling, browser automation, and MCP (Model Context Protocol) integration. It's designed to be a versatile agent that can solve various tasks using multiple tools.

## Common Commands

### Setup and Installation

```bash
# Using uv (recommended)
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt

# Using conda
conda create -n open_manus python=3.12
conda activate open_manus
pip install -r requirements.txt

# Optional: Install browser automation (Playwright)
playwright install
```

### Configuration

```bash
# Create config file from example
cp config/config.example.toml config/config.toml

# Edit config.toml to add API keys and settings
# Required: Set llm.api_key with your LLM provider API key
```

### Running the Application

```bash
# Main agent (single-agent mode)
python main.py

# With prompt argument
python main.py --prompt "Your task here"

# MCP tool version
python run_mcp.py

# With MCP options
python run_mcp.py --connection stdio --interactive

# Multi-agent flow (unstable)
python run_flow.py
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/sandbox/test_sandbox.py

# Run tests with verbose output
pytest -v

# Run specific test
pytest tests/sandbox/test_sandbox.py::test_sandbox_file_operations
```

### Code Quality

```bash
# Run pre-commit checks
pre-commit run --all-files

# Manual formatting with black
black .

# Import sorting with isort
isort --profile black --filter-files --lines-after-imports=2 .

# Remove unused imports with autoflake
autoflake --remove-all-unused-imports --ignore-init-module-imports --in-place --recursive .
```

### Development with Data Analysis Agent

```bash
# Enable data analysis agent in config.toml:
# [runflow]
# use_data_analysis_agent = true

# Install chart visualization dependencies
cd app/tool/chart_visualization
npm install

# Run chart visualization tests
python -m app.tool.chart_visualization.test.chart_demo
python -m app.tool.chart_visualization.test.report_demo
```

## Architecture

### Core Components

**Agent Hierarchy**: The codebase uses an inheritance-based agent architecture:
- `BaseAgent` (app/agent/base.py): Abstract base providing state management, memory, and execution loop
- `ReActAgent` (app/agent/react.py): Implements ReAct pattern (think → act → observe)
- `ToolCallAgent` (app/agent/toolcall.py): Handles tool/function calling with LLM integration
- `Manus` (app/agent/manus.py): The main general-purpose agent with MCP support

**Agent Execution Flow**: All agents follow a step-based execution pattern:
1. `run()` method initiates the agent loop (max_steps iterations)
2. `step()` method is called each iteration (think → act cycle in ReAct agents)
3. `think()` generates next action using LLM
4. `act()` executes the action (tool calls, etc.)
5. Results are added to agent memory and loop continues until completion or max_steps

**Tool System**: Tools inherit from `BaseTool` (app/tool/base.py) and must implement:
- `name`, `description`, and `parameters` (OpenAI function calling format)
- `execute(**kwargs)` async method returning `ToolResult`
- `to_param()` converts tool to function calling format
- Tools are organized in `ToolCollection` (app/tool/tool_collection.py)

**MCP Integration**: OpenManus supports MCP (Model Context Protocol) for remote tool access:
- `MCPClients` manages multiple MCP server connections (stdio and SSE)
- `MCPClientTool` wraps MCP tools as local tools
- MCP servers configured in `config/mcp.json`
- Manus agent automatically connects to configured MCP servers on initialization

**Memory System**: Conversation history is managed through:
- `Memory` class (app/schema.py) stores list of `Message` objects
- `Message` supports different roles: system, user, assistant, tool
- Messages can include text, tool calls, and base64-encoded images
- Memory has configurable max_messages limit (default 100)

**LLM Integration**: The `LLM` class (app/llm.py) provides:
- Singleton pattern per config name
- Support for OpenAI, Azure OpenAI, Anthropic, Ollama, AWS Bedrock
- Token counting with `TokenCounter` class
- Retry logic with exponential backoff for rate limits
- `ask()` for text generation, `ask_tool()` for function calling

**Flow System**: Multi-agent coordination via flows (app/flow/):
- `BaseFlow` abstract class for flow implementations
- `PlanningFlow` coordinates multiple agents with planning step
- `FlowFactory` creates flows with agent configuration
- Flows execute task → planning → agent selection → execution cycle

### Key Directories

- `app/agent/`: Agent implementations (base, manus, toolcall, browser, data_analysis, etc.)
- `app/tool/`: Tool implementations (bash, browser, file operations, search, planning, etc.)
- `app/flow/`: Multi-agent flow orchestration
- `app/sandbox/`: Docker-based sandboxed execution environment
- `app/mcp/`: MCP server and client implementation
- `app/prompt/`: System and step prompts for different agents
- `config/`: Configuration files (TOML for settings, JSON for MCP servers)
- `workspace/`: Default working directory for agent file operations
- `tests/`: Test suite (primarily sandbox tests)

### Important Patterns

**Async/Await**: All agent operations are async. Use `asyncio.run()` for entry points and `await` for agent methods.

**Configuration Loading**: Configuration is loaded from `config/config.toml` via `app.config.Config` singleton. Access via `from app.config import config`. MCP configuration loaded separately from `config/mcp.json`.

**Tool Result Handling**: Tools return `ToolResult` objects with:
- `output`: Success output string
- `error`: Error message if failed
- `base64_image`: Optional image data
- `system`: Optional system message

**Agent State Transitions**: Agents use `state_context` for safe state transitions (IDLE → RUNNING → FINISHED/ERROR). State automatically reverts on exceptions.

**Browser Context Management**: Browser tools use `BrowserContextHelper` to manage Playwright browser instances. Browser context is shared across tool calls within a step and cleaned up after agent completion.

**Sandbox Execution**: When `use_sandbox=true` in config, code execution happens in Docker containers:
- Managed by `DockerSandbox` class
- Isolated filesystem and network (configurable)
- Terminal access via `DockerTerminal`
- Automatic cleanup on agent completion

## Configuration Guidelines

### LLM Configuration

The `[llm]` section in `config.toml` defines the default LLM. You can define multiple LLM configs (e.g., `[llm.vision]`) for different purposes. Required fields:
- `model`: Model identifier
- `base_url`: API endpoint
- `api_key`: Authentication key
- `max_tokens`: Response token limit
- `temperature`: Sampling temperature

### Browser Configuration

Optional `[browser]` section controls browser automation:
- `headless`: Run browser without UI (default: false)
- `disable_security`: Disable security features for automation (default: true)
- `chrome_instance_path`: Connect to existing Chrome instance
- `wss_url` or `cdp_url`: Connect to remote browser
- `proxy`: Proxy configuration with server/username/password

### Sandbox Configuration

Optional `[sandbox]` section for isolated code execution:
- `use_sandbox`: Enable Docker sandbox (default: false)
- `image`: Docker base image (default: python:3.12-slim)
- `work_dir`: Container working directory
- `memory_limit` and `cpu_limit`: Resource limits
- `network_enabled`: Allow network access in sandbox

### MCP Configuration

MCP servers configured in `config/mcp.json` (not TOML):
```json
{
  "mcpServers": {
    "server_id": {
      "type": "stdio" | "sse",
      "command": "python",
      "args": ["-m", "module.name"],
      "url": "http://..."
    }
  }
}
```

## Development Notes

**Adding New Tools**: 
1. Create class inheriting from `BaseTool` in `app/tool/`
2. Define `name`, `description`, and `parameters` (JSON schema)
3. Implement `async def execute(self, **kwargs)` 
4. Return `ToolResult` using `self.success_response()` or `self.fail_response()`
5. Add to agent's `available_tools` in `ToolCollection`

**Adding New Agents**:
1. Inherit from `BaseAgent` or `ToolCallAgent` in `app/agent/`
2. Define `name`, `description`, `system_prompt`, `next_step_prompt`
3. Override `step()` for BaseAgent or use default think→act cycle from ToolCallAgent
4. Configure `available_tools` with appropriate tool collection
5. Set `max_steps` based on expected task complexity

**Prompt Engineering**: System prompts are in `app/prompt/` organized by agent type. Prompts use f-string formatting with variables like `{directory}` for workspace root.

**Debugging**: Use `app.logger` (Loguru) for logging. Log levels: `logger.debug()`, `logger.info()`, `logger.warning()`, `logger.error()`.

**Pre-commit Hooks**: Always run `pre-commit run --all-files` before submitting PRs. This runs black (formatting), isort (import sorting), autoflake (unused import removal), and YAML/file checks.

**Testing Focus**: Current test coverage primarily on sandbox functionality (tests/sandbox/). When adding new sandbox features, add corresponding tests following existing patterns with pytest and pytest-asyncio.

**Token Limits**: The LLM class includes token counting (`TokenCounter`) that estimates token usage for text and images. Monitor token usage to avoid exceeding LLM context limits.

**Error Handling**: Agents handle `TokenLimitExceeded` exceptions by transitioning to FINISHED state. Tool execution errors are caught and returned as tool results rather than raising exceptions.
