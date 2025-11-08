# MCP Bridge Implementation

## Overview

The MCP (Model Context Protocol) Bridge provides a unified interface for tool execution with automatic fallback capabilities. It detects whether the current LLM model supports native tool calling and automatically routes tool execution either through native APIs or via MCP stdio clients.

## Architecture

### Components

1. **MCPBridge** (`app/mcp/bridge.py`)
   - Main bridge component that handles tool execution routing
   - Detects model capabilities automatically
   - Manages fallback to stdio MCP servers
   - Handles connection pooling and process management

2. **ModularMCPServer** (`app/mcp/modular_server.py`)
   - Modular server framework supporting multiple service registrations
   - Supports both stdio and SSE transports
   - Provides discovery endpoint for available tools
   - Configurable via `config/mcp.json`

3. **Service Base Classes** (`app/mcp/service_base.py`)
   - Abstract base class for MCP services
   - Registry system for service discovery
   - Built-in tool registration and metadata handling

4. **Configuration** (`app/config.py` - MCPSettings)
   - Enhanced configuration supporting bridge settings
   - Internal and external server definitions
   - Fallback detection parameters
   - Connection pool settings

## Configuration

### MCP Configuration (`config/mcp.json`)

```json
{
    "defaultTransport": "stdio",
    "enableFallback": true,
    "fallbackDetection": {
        "checkSupportsTools": true,
        "checkApiType": true,
        "unsupportedApiTypes": ["ollama", "custom"]
    },
    "internalServers": {
        "tools": {
            "type": "stdio",
            "command": "python",
            "args": ["-m", "app.mcp.server"],
            "namespace": "openmanus.tools",
            "enabled": true,
            "autoStart": true
        }
    },
    "connectionPool": {
        "maxConnections": 10,
        "connectionTimeout": 30,
        "retryAttempts": 3,
        "retryDelay": 1.0
    }
}
```

### TOML Configuration (`config/config.toml`)

```toml
[mcp]
enable_fallback = true
default_transport = "stdio"
server_reference = "app.mcp.modular_server"
```

## Usage

### CLI Usage

#### Run with MCP Bridge (automatic fallback)
```bash
python run_mcp.py --bridge
```

#### Run with manual server start
```bash
python run_mcp.py --bridge --start-server
```

#### Run specific service
```bash
python -m app.mcp.modular_server --service tools
```

#### List available services
```bash
python -m app.mcp.modular_server --list-services
```

#### Discovery mode
```bash
python -m app.mcp.modular_server --discovery
```

### Flow Integration

The MCP Bridge is automatically integrated into flow execution:

```bash
python run_flow.py
```

The bridge will:
1. Detect model capabilities from configuration
2. Initialize in native or fallback mode
3. Route all tool calls appropriately
4. Handle cleanup automatically

### Programmatic Usage

```python
from app.mcp.bridge import MCPBridge

# Initialize bridge
bridge = MCPBridge()
await bridge.initialize()

# Execute tool
result = await bridge.execute_tool("bash", command="echo 'hello'")

# List tools
tools = await bridge.list_tools()

# Get status
status = bridge.get_status()

# Cleanup
await bridge.cleanup()
```

## Fallback Detection

The bridge automatically detects when to use fallback mode:

### Detection Methods

1. **Explicit supports_tools flag**
   ```json
   {"supports_tools": false}
   ```

2. **API Type checking**
   ```json
   {"api_type": "ollama"}  // Triggers fallback
   ```

3. **URL Pattern matching**
   ```json
   {"base_url": "http://localhost:11434"}  // Ollama URL
   ```

### Configuration Override

You can disable fallback or adjust detection:

```json
{
    "enableFallback": false,
    "fallbackDetection": {
        "checkSupportsTools": true,
        "checkApiType": true,
        "unsupportedApiTypes": ["ollama", "custom"]
    }
}
```

## Internal Services

### Tools Service
- **Namespace**: `openmanus.tools`
- **Tools**: bash, browser, editor, terminate
- **Auto-start**: Yes (default)

### Knowledge Service
- **Namespace**: `openmanus.knowledge`
- **Tools**: Knowledge base operations (placeholder)
- **Auto-start**: No (default)

### Memory Service
- **Namespace**: `openmanus.memory`
- **Tools**: Memory operations (placeholder)
- **Auto-start**: No (default)

## External Services

External MCP servers can be configured:

```json
{
    "externalServers": {
        "filesystem": {
            "type": "stdio",
            "command": "npx",
            "args": ["@modelcontextprotocol/server-filesystem", "/tmp"],
            "namespace": "external.filesystem",
            "enabled": true,
            "auth": {
                "type": "bearer",
                "token": "${FILESYSTEM_TOKEN}"
            }
        },
        "github": {
            "type": "sse",
            "url": "https://api.github.com/mcp",
            "namespace": "external.github",
            "enabled": false
        }
    }
}
```

## Connection Pooling

The bridge manages connection pools for efficient resource usage:

- **Max connections**: 10 (configurable)
- **Connection timeout**: 30s
- **Retry attempts**: 3 with exponential backoff
- **Keep-alive**: Automatic for SSE connections

## Logging

Bridge logging can be configured:

```json
{
    "logging": {
        "level": "INFO",
        "logToolCalls": true,
        "logFallbacks": true
    }
}
```

Log levels:
- `DEBUG`: Detailed execution traces
- `INFO`: General operation logs
- `WARNING`: Fallback activations
- `ERROR`: Execution failures

## Testing

### Unit Tests
```bash
python -m pytest tests/test_mcp_bridge.py -v
```

### Integration Tests
```bash
python test_mcp_bridge.py all
python test_mcp_bridge.py native
python test_mcp_bridge.py fallback
python test_mcp_bridge.py discovery
```

### Manual Testing

1. **Test Native Mode**
   ```bash
   python test_mcp_bridge.py native
   ```

2. **Test Fallback Mode**
   ```bash
   python test_mcp_bridge.py fallback
   ```

3. **Test Discovery**
   ```bash
   python test_mcp_bridge.py discovery
   ```

## Troubleshooting

### Common Issues

1. **Server fails to start**
   - Check Python path in config
   - Verify module paths are correct
   - Check for missing dependencies

2. **Fallback not engaging**
   - Verify `enable_fallback: true` in config
   - Check model configuration for `supports_tools: false`
   - Review API type detection settings

3. **Tool execution fails**
   - Check server logs for errors
   - Verify tool parameters are correct
   - Check connection status with bridge.get_status()

### Debug Commands

```bash
# Check bridge status
python -c "
import asyncio
from app.mcp.bridge import MCPBridge
async def main():
    bridge = MCPBridge()
    await bridge.initialize()
    print(bridge.get_status())
    await bridge.cleanup()
asyncio.run(main())
"

# Test discovery
python -m app.mcp.modular_server --discovery

# List services
python -m app.mcp.modular_server --list-services
```

## Migration Guide

### From Legacy MCP Server

1. Update configuration from `mcpServers` to `internalServers`
2. Update CLI scripts to use `--bridge` flag
3. Replace direct server references with bridge calls
4. Update tool execution to use `bridge.execute_tool()`

### Configuration Migration

**Before:**
```json
{
    "mcpServers": {
        "server1": {
            "type": "stdio",
            "command": "python",
            "args": ["-m", "app.mcp.server"]
        }
    }
}
```

**After:**
```json
{
    "internalServers": {
        "tools": {
            "type": "stdio",
            "command": "python",
            "args": ["-m", "app.mcp.modular_server", "--service", "tools"],
            "namespace": "openmanus.tools",
            "enabled": true,
            "autoStart": true
        }
    }
}
```

## API Reference

### MCPBridge

#### Methods

- `initialize(model_config=None)`: Initialize bridge with model detection
- `execute_tool(tool_name, **kwargs)`: Execute a tool via appropriate route
- `list_tools()`: List all available tools
- `get_tool_names()`: Get list of tool names
- `is_fallback_active()`: Check if fallback mode is active
- `get_status()`: Get comprehensive bridge status
- `cleanup()`: Clean up all resources

#### Properties

- `native_tools`: Dictionary of native tool instances
- `mcp_tools`: Dictionary of MCP tool proxies
- `fallback_active`: Boolean indicating current mode

### ModelCapabilityDetector

#### Static Methods

- `supports_tools(model_config)`: Check if model supports tools
- `should_use_fallback(model_config)`: Determine if fallback should be used

## Future Enhancements

1. **Service Hot-Reloading**: Dynamic service registration without restart
2. **Advanced Authentication**: OAuth2 and certificate-based auth
3. **Performance Monitoring**: Built-in metrics and dashboards
4. **Service Mesh**: Multi-node service coordination
5. **Tool Caching**: Intelligent result caching for common operations