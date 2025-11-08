# Tool Calling Emulation System

## Overview

The Tool Calling Emulation System enables LLM APIs that don't natively support tool calling to use tools through structured text output. Instead of relying on API-level function calling, this system teaches LLMs to output tool calls in a specific format, then parses and executes them.

## Key Features

- **Pattern-Based Emulation**: LLM outputs tool calls in structured XML/JSON format
- **System Prompt Injection**: Automatic generation of system prompts teaching LLMs the format
- **Response Parsing**: Robust extraction of tool calls from text responses
- **Tool Execution**: Parallel or sequential execution with timeout handling
- **Result Formatting**: Clean formatting of tool results for LLM consumption
- **Multi-Turn Iterations**: Support for multiple tool calling rounds
- **MCP Fallback**: Automatic fallback to MCP protocol when pattern matching fails
- **Caching**: Result caching for improved performance
- **Audit Trail**: Comprehensive logging of all tool usage
- **Error Handling**: Graceful degradation with helpful error messages

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Tool Calling Flow                        │
└─────────────────────────────────────────────────────────────┘

1. User Query
   ↓
2. System Prompt Generator
   - Teaches LLM tool format
   - Lists available tools
   - Provides examples
   ↓
3. LLM Response
   - Contains tool calls in <tool_call> tags
   - May contain multiple calls
   ↓
4. Response Parser
   - Extracts tool calls
   - Validates JSON
   - Checks tool availability
   ↓
5. Execution Loop
   - Executes tools (parallel/sequential)
   - Handles timeouts
   - Manages caching
   ↓
6. Result Formatter
   - Formats results for LLM
   - Truncates large outputs
   - Adds metadata
   ↓
7. Iteration Manager
   - Injects results back
   - Manages multiple turns
   - Enforces max iterations
   ↓
8. Final Response
```

## Tool Call Format

LLMs are taught to output tool calls in this format:

```
<tool_call>
{
  "name": "tool_name",
  "args": {"arg1": "value1", "arg2": "value2"}
}
</tool_call>
```

### Example Response:

```
User: "What's the weather in Paris and calculate 15 * 8"

LLM: I'll help you with both requests.

First, let me check the weather:
<tool_call>
{
  "name": "get_weather",
  "args": {"location": "Paris"}
}
</tool_call>

And calculate that for you:
<tool_call>
{
  "name": "calculator",
  "args": {"expression": "15 * 8"}
}
</tool_call>
```

## Usage

### Basic Usage

```python
from app.tool_calling import create_emulator
from app.tool.tool_registry import get_global_tool_registry

# Get tool registry
registry = get_global_tool_registry()
tools = {name: registry.get_instance(name) for name in registry.get_tool_names()}

# Create emulator
config = {
    'max_iterations': 5,
    'timeout_per_tool': 30.0,
    'parallel_execution': True,
    'caching_enabled': True
}
emulator = create_emulator(tools, config)

# Generate system prompt
system_prompt = emulator.generate_system_prompt()

# Process LLM response
result = await emulator.process_response(llm_response)

if result['has_tool_calls']:
    # Tool calls were executed
    formatted_results = result['formatted_results']
    # Inject back into conversation...
```

### Custom Tools

```python
from app.tool.base import BaseTool, ToolResult

class MyCustomTool(BaseTool):
    name: str = "my_tool"
    description: str = "Does something useful"
    parameters: dict = {
        "input": {"type": "string", "description": "Input data"}
    }
    
    async def execute(self, **kwargs):
        input_data = kwargs.get("input", "")
        # Do work...
        return ToolResult(output=f"Processed: {input_data}")

# Register tool
tools = {"my_tool": MyCustomTool()}
emulator = create_emulator(tools)
```

## Configuration

Configuration can be done via `config/config.toml`:

```toml
[tool_calling]
enabled = true
emulation_mode = true
max_iterations = 5
timeout_per_tool = 30.0
parallel_execution = true
caching_enabled = true
cache_ttl = 3600
enable_fallback = true
enable_audit_log = true
audit_log_dir = "workspace/logs/tool_calls"
include_examples_in_prompt = true
strict_parsing = false
max_result_length = 10000

[tool_calling.tools]
python_execute = "local"
bash = "local"
web_search = "external"
# ... more tools
```

Or programmatically:

```python
config = {
    'max_iterations': 10,
    'timeout_per_tool': 60.0,
    'parallel_execution': False,
    'caching_enabled': True,
    'cache_ttl': 7200,
    'enable_fallback': True
}
emulator = create_emulator(tools, config)
```

## Components

### 1. Emulator (`emulator.py`)

Main orchestration class. Coordinates all components.

```python
from app.tool_calling import ToolCallingEmulator, create_emulator

emulator = create_emulator(tools, config)
```

### 2. System Prompts (`system_prompts.py`)

Generates system prompts teaching LLMs the tool format.

```python
from app.tool_calling import SystemPromptGenerator

generator = SystemPromptGenerator()
generator.register_tool("tool_name", "description", parameters)
prompt = generator.generate_system_prompt()
```

### 3. Response Parser (`response_parser.py`)

Extracts tool calls from LLM responses.

```python
from app.tool_calling import ResponseParser

parser = ResponseParser()
tool_calls = parser.extract_tool_calls(response)
tool_calls, cleaned_text = parser.extract_and_clean(response)
```

### 4. Execution Loop (`execution_loop.py`)

Executes tools and manages the flow.

```python
from app.tool_calling import ToolExecutionLoop

loop = ToolExecutionLoop(tools, max_iterations=5)
results = await loop.execute_tool_calls(llm_response, context, iteration)
```

### 5. Result Formatter (`result_formatter.py`)

Formats tool results for LLM consumption.

```python
from app.tool_calling import ResultFormatter

formatter = ResultFormatter(max_length=10000)
formatted = formatter.format_result(tool_name, result)
```

### 6. Error Handler (`error_handler.py`)

Handles errors gracefully with helpful messages.

```python
from app.tool_calling import ErrorHandler, ErrorType

handler = ErrorHandler(available_tools=tool_list)
error = handler.handle_tool_not_found("unknown_tool")
```

### 7. Optimization (`optimization.py`)

Caching and parallel execution.

```python
from app.tool_calling import OptimizationManager

manager = OptimizationManager(enable_caching=True, enable_parallel=True)
cached_result = manager.get_cached_result(tool_name, args)
```

### 8. Audit Log (`audit_log.py`)

Comprehensive audit trail.

```python
from app.tool_calling import get_audit_logger

logger = get_audit_logger()
logger.log_call(
    call_id="123",
    tool_name="web_search",
    arguments={"query": "test"},
    result_success=True,
    result_output="results..."
)
```

### 9. Iteration Manager (`iteration_manager.py`)

Manages multi-turn conversations.

```python
from app.tool_calling import get_iteration_manager

manager = get_iteration_manager()
state = manager.start_conversation("conv_id", max_iterations=5)
iteration = state.start_iteration()
```

### 10. MCP Bridge (`mcp_bridge.py`)

Fallback to MCP protocol.

```python
from app.tool_calling import MCPBridge, FallbackStrategy

bridge = MCPBridge()
strategy = FallbackStrategy(enable_mcp_fallback=True)
result = await strategy.try_fallback(tool_name, args, error)
```

## Performance Optimization

### Caching

Results are automatically cached based on tool name and arguments:

```python
# Enable caching
config = {'caching_enabled': True, 'cache_ttl': 3600}
emulator = create_emulator(tools, config)

# First call: executes tool
result1 = await emulator.process_response(response)

# Second call: uses cache (same args)
result2 = await emulator.process_response(response)
```

### Parallel Execution

Independent tool calls execute in parallel:

```python
config = {'parallel_execution': True}
emulator = create_emulator(tools, config)

# Multiple tool calls execute simultaneously
response = """
<tool_call>{"name": "tool1", "args": {}}</tool_call>
<tool_call>{"name": "tool2", "args": {}}</tool_call>
"""
result = await emulator.process_response(response)
```

## Error Handling

The system provides graceful error handling:

### Unknown Tool
```
ERROR: Tool 'unknown_tool' is not available.
Available tools: web_search, calculator, get_weather
```

### Invalid Arguments
```
ERROR: Invalid arguments for tool 'calculator': Missing required field 'expression'
```

### Execution Failure
```
ERROR: Tool 'calculator' execution failed: Division by zero
Suggestion: Check your input and try again.
```

### Timeout
```
ERROR: Tool 'web_search' timed out after 30 seconds.
Suggestion: Try breaking down your request.
```

## Audit Trail

All tool calls are logged:

```python
from app.tool_calling import get_audit_logger

logger = get_audit_logger()

# Get statistics
stats = logger.get_statistics()
print(f"Total calls: {stats['total_calls']}")
print(f"Success rate: {stats['success_rate']}")

# Get recent calls
recent = logger.get_recent_calls(limit=10)

# Search calls
results = logger.search_calls(
    tool_name="web_search",
    success=True,
    start_time=datetime.now() - timedelta(hours=1)
)

# Export to file
logger.export_to_json(Path("audit_log.json"))
```

## Testing

Run the test suite:

```bash
# All tool calling tests
pytest tests/tool_calling/ -v

# Specific test file
pytest tests/tool_calling/test_response_parser.py -v

# With coverage
pytest tests/tool_calling/ --cov=app.tool_calling --cov-report=html
```

## Examples

See `examples/tool_calling_demo.py` for comprehensive examples:

```bash
python examples/tool_calling_demo.py
```

## Integration with Existing Tools

The system integrates seamlessly with existing MCP tools:

```python
from app.tool.tool_registry import initialize_tool_registry, get_global_tool_registry

# Initialize tool registry
initialize_tool_registry()

# Get tools
registry = get_global_tool_registry()
tools = {name: registry.get_instance(name) for name in registry.get_tool_names()}

# Create emulator
emulator = create_emulator(tools)

# Available tools: bash, python_execute, web_search, browser, etc.
```

## Best Practices

1. **Set Appropriate Timeouts**: Default 30s per tool, adjust based on tool complexity
2. **Enable Caching**: Improves performance for repeated queries
3. **Use Parallel Execution**: For independent tool calls
4. **Monitor Audit Logs**: Track tool usage and errors
5. **Handle Errors Gracefully**: System provides helpful error messages
6. **Limit Iterations**: Prevent infinite loops (default: 5)
7. **Test Tool Calls**: Use strict parsing mode during development

## Troubleshooting

### LLM Not Outputting Correct Format

- Ensure system prompt is properly injected
- Try including more examples
- Use a more capable LLM model
- Check prompt length limits

### Tool Execution Failing

- Check tool implementation
- Verify arguments match schema
- Review audit logs for details
- Enable debug logging

### Performance Issues

- Enable caching
- Enable parallel execution
- Increase timeout values
- Check network connectivity

### Max Iterations Exceeded

- Simplify user query
- Increase max_iterations
- Check for circular dependencies
- Review LLM behavior

## Future Enhancements

- Dynamic tool loading from plugins
- Tool capability advertisement for MCP clients
- Advanced dependency analysis for parallel execution
- WebSocket support for real-time streaming
- Tool usage analytics dashboard
- A/B testing for different prompt strategies
- Tool call prediction and prefetching
- Integration with LangChain/LlamaIndex

## License

See LICENSE file for details.

## Contributing

Contributions welcome! Please follow existing code style and add tests for new features.
