"""Tool Calling Emulation System.

This package provides a complete tool calling emulation system for LLM APIs
that don't natively support tool calling.

Components:
- emulator: Main orchestration and high-level interface
- system_prompts: System prompt generation
- response_parser: Extract tool calls from text responses
- execution_loop: Execute tools and manage iterations
- result_formatter: Format results for LLM consumption
- error_handler: Graceful error handling
- mcp_bridge: Fallback to MCP protocol
- optimization: Caching and parallel execution
- audit_log: Comprehensive audit trail
- iteration_manager: Multi-turn conversation management

Usage:
    from app.tool_calling import create_emulator
    from app.tool.tool_registry import get_global_tool_registry
    
    # Get tool registry
    registry = get_global_tool_registry()
    tools = {name: registry.get_instance(name) for name in registry.get_tool_names()}
    
    # Create emulator
    emulator = create_emulator(tools, config={'max_iterations': 5})
    
    # Generate system prompt
    system_prompt = emulator.generate_system_prompt()
    
    # Process LLM response
    result = await emulator.process_response(llm_response)
    
    if result['has_tool_calls']:
        # Tool calls were executed
        formatted_results = result['formatted_results']
        # Inject back into conversation...
"""

from app.tool_calling.audit_log import (
    AuditLogger,
    ToolCallRecord,
    get_audit_logger,
    set_audit_logger,
)
from app.tool_calling.emulator import (
    ToolCallingEmulator,
    create_emulator,
)
from app.tool_calling.error_handler import (
    ErrorHandler,
    ErrorType,
    ToolCallError,
    handle_tool_error,
)
from app.tool_calling.execution_loop import (
    ToolExecutionContext,
    ToolExecutionLoop,
    create_tool_execution_loop,
)
from app.tool_calling.iteration_manager import (
    ConversationState,
    IterationManager,
    IterationState,
    get_iteration_manager,
    set_iteration_manager,
)
from app.tool_calling.mcp_bridge import (
    FallbackStrategy,
    MCPBridge,
    get_mcp_bridge,
    set_mcp_bridge,
)
from app.tool_calling.optimization import (
    OptimizationManager,
    ParallelExecutor,
    ToolExecutionCache,
    get_optimization_manager,
    set_optimization_manager,
)
from app.tool_calling.response_parser import (
    ResponseParser,
    ToolCall,
    ToolCallParseError,
    extract_and_clean_response,
    parse_tool_calls,
)
from app.tool_calling.result_formatter import (
    ResultFormatter,
    format_tool_result,
)
from app.tool_calling.system_prompts import (
    SystemPromptGenerator,
    build_tool_calling_prompt,
    MINIMAL_PROMPT,
    VERBOSE_PROMPT,
)

__all__ = [
    # Main emulator
    'ToolCallingEmulator',
    'create_emulator',
    
    # Response parsing
    'ResponseParser',
    'ToolCall',
    'ToolCallParseError',
    'parse_tool_calls',
    'extract_and_clean_response',
    
    # System prompts
    'SystemPromptGenerator',
    'build_tool_calling_prompt',
    'MINIMAL_PROMPT',
    'VERBOSE_PROMPT',
    
    # Result formatting
    'ResultFormatter',
    'format_tool_result',
    
    # Error handling
    'ErrorHandler',
    'ErrorType',
    'ToolCallError',
    'handle_tool_error',
    
    # Execution
    'ToolExecutionLoop',
    'ToolExecutionContext',
    'create_tool_execution_loop',
    
    # Iteration management
    'IterationManager',
    'IterationState',
    'ConversationState',
    'get_iteration_manager',
    'set_iteration_manager',
    
    # MCP bridge
    'MCPBridge',
    'FallbackStrategy',
    'get_mcp_bridge',
    'set_mcp_bridge',
    
    # Optimization
    'OptimizationManager',
    'ToolExecutionCache',
    'ParallelExecutor',
    'get_optimization_manager',
    'set_optimization_manager',
    
    # Audit logging
    'AuditLogger',
    'ToolCallRecord',
    'get_audit_logger',
    'set_audit_logger',
]

# Package metadata
__version__ = '1.0.0'
__author__ = 'OpenManus Team'
__description__ = 'Tool calling emulation system for LLMs'
