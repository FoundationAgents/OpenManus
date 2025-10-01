# OpenManus AI Coding Agent Instructions

## Project Architecture

OpenManus is a multi-agent framework for AI automation with three execution modes:
- **Direct Mode** (`main.py`): Single Manus agent with tool collection
- **MCP Mode** (`run_mcp.py`): Model Context Protocol integration for external tools
- **Flow Mode** (`run_flow.py`): Multi-agent orchestration with planning

### Core Components

**Agents** (`app/agent/`): All inherit from `BaseAgent` with state management, memory, and step-based execution. Key agents:
- `Manus`: Main general-purpose agent with browser, file editing, Python execution
- `MCPAgent`: Connects to MCP servers for external tool integration  
- `DataAnalysis`: Specialized for data analysis and visualization tasks

**Tools** (`app/tool/`): Implement `BaseTool` interface. Core tools include:
- `StrReplaceEditor`: File operations with sandbox support
- `BrowserUseTool`: Web automation via browser-use library
- `PythonExecute`: Code execution with sandbox isolation
- `MCPClientTool`: Bridge to external MCP servers

**Configuration** (`app/config.py`): Singleton pattern loads from `config/config.toml`. Supports multiple LLM providers (OpenAI, Anthropic, Azure, Ollama, AWS Bedrock).

## Development Patterns

### Tool Implementation
```python
class MyTool(BaseTool):
    name: str = "my_tool"
    description: str = "Tool description"
    
    async def execute(self, **kwargs) -> ToolResult:
        return ToolSuccess(result="Success message")
```

### Agent Creation
Use factory pattern for async initialization:
```python
agent = await Manus.create()  # Handles MCP server connections
try:
    await agent.run(prompt)
finally:
    await agent.cleanup()  # Essential for browser/MCP cleanup
```

### Memory Management
Agents use structured memory with role-based messages:
```python
agent.update_memory("user", "request")
agent.update_memory("assistant", "response")
agent.update_memory("tool", result, tool_call_id=id)
```

## Configuration Examples

**Basic Setup** (`config/config.toml`):
```toml
[llm]
model = "claude-3-7-sonnet-20250219"
base_url = "https://api.anthropic.com/v1/"
api_key = "YOUR_API_KEY"
max_tokens = 8192
temperature = 0.0
```

**MCP Integration** (`config/mcp.json`):
```json
{
  "mcpServers": {
    "server1": {
      "type": "sse",
      "url": "http://localhost:8000/sse"
    }
  }
}
```

## Key Workflows

**Tool Development**: Create tool → Add to `ToolCollection` → Register in agent
**Testing**: Use `pytest` with `tests/` structure. Run `pre-commit run --all-files` before commits
**Browser Automation**: Uses `BrowserContextHelper` for state management across browser operations
**Sandbox Execution**: Optional Docker isolation via `SandboxSettings` in config

## Critical Integration Points

- **MCP Protocol**: Enables external tool integration via stdio/SSE connections
- **Browser Context**: Maintains page state across tool calls with cleanup handling
- **Async Architecture**: All agents/tools use async/await with proper resource cleanup
- **State Management**: Agents track execution state (IDLE/RUNNING/FINISHED/ERROR)

## Project-Specific Conventions

- Configuration uses TOML + JSON hybrid (TOML for main config, JSON for MCP servers)
- All file paths use `pathlib.Path` objects, converted to strings for tool interfaces
- Error handling via custom `ToolError` exceptions and `ToolResult` return types
- Logging with `loguru` library using structured messages
- Factory pattern for complex object initialization requiring async setup