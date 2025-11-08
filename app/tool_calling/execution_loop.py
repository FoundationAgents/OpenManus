"""Tool calling execution loop.

Orchestrates the complete tool calling flow:
1. Parse LLM response for tool calls
2. Validate tool calls
3. Execute tools (parallel or sequential)
4. Format results
5. Inject back into conversation
6. Repeat until complete
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.logger import logger
from app.tool.base import ToolResult
from app.tool_calling.audit_log import get_audit_logger
from app.tool_calling.error_handler import ErrorHandler, ErrorType
from app.tool_calling.iteration_manager import IterationState, get_iteration_manager
from app.tool_calling.mcp_bridge import FallbackStrategy
from app.tool_calling.optimization import get_optimization_manager
from app.tool_calling.response_parser import ResponseParser, ToolCall
from app.tool_calling.result_formatter import ResultFormatter


class ToolExecutionContext:
    """Context for tool execution."""
    
    def __init__(
        self,
        conversation_id: str,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ):
        self.conversation_id = conversation_id
        self.session_id = session_id
        self.agent_id = agent_id
        self.call_counter = 0
    
    def generate_call_id(self) -> str:
        """Generate unique call ID."""
        self.call_counter += 1
        return f"{self.conversation_id}-{self.call_counter}-{uuid.uuid4().hex[:8]}"


class ToolExecutionLoop:
    """Main loop for tool calling execution."""
    
    def __init__(
        self,
        tool_registry: Dict[str, Any],
        max_iterations: int = 5,
        timeout_per_tool: float = 30.0,
        enable_parallel: bool = True,
        enable_caching: bool = True,
        enable_fallback: bool = True
    ):
        """Initialize execution loop.
        
        Args:
            tool_registry: Registry of available tools
            max_iterations: Maximum tool calling iterations
            timeout_per_tool: Timeout per tool execution
            enable_parallel: Enable parallel execution
            enable_caching: Enable result caching
            enable_fallback: Enable MCP fallback
        """
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations
        self.timeout_per_tool = timeout_per_tool
        
        # Initialize components
        self.parser = ResponseParser(strict_mode=False)
        self.formatter = ResultFormatter()
        self.error_handler = ErrorHandler(
            available_tools=list(tool_registry.keys())
        )
        self.iteration_manager = get_iteration_manager()
        self.optimization_manager = get_optimization_manager()
        self.audit_logger = get_audit_logger()
        self.fallback_strategy = FallbackStrategy(enable_mcp_fallback=enable_fallback)
        
        self.enable_parallel = enable_parallel
        self.enable_caching = enable_caching
        
        logger.info(
            f"ToolExecutionLoop initialized "
            f"(parallel={enable_parallel}, caching={enable_caching}, "
            f"max_iterations={max_iterations})"
        )
    
    async def execute_tool_calls(
        self,
        llm_response: str,
        context: ToolExecutionContext,
        iteration: IterationState
    ) -> Dict[str, ToolResult]:
        """Execute tool calls from LLM response.
        
        Args:
            llm_response: LLM response containing tool calls
            context: Execution context
            iteration: Current iteration state
            
        Returns:
            Dictionary mapping call IDs to results
        """
        # Parse tool calls
        tool_calls = self.parser.extract_tool_calls(llm_response)
        
        if not tool_calls:
            logger.debug("No tool calls found in response")
            return {}
        
        logger.info(f"Found {len(tool_calls)} tool call(s) to execute")
        
        # Execute tool calls
        results = {}
        
        if self.enable_parallel and len(tool_calls) > 1:
            # Parallel execution
            results = await self._execute_parallel(tool_calls, context, iteration)
        else:
            # Sequential execution
            results = await self._execute_sequential(tool_calls, context, iteration)
        
        return results
    
    async def _execute_sequential(
        self,
        tool_calls: List[ToolCall],
        context: ToolExecutionContext,
        iteration: IterationState
    ) -> Dict[str, ToolResult]:
        """Execute tool calls sequentially.
        
        Args:
            tool_calls: List of tool calls
            context: Execution context
            iteration: Current iteration state
            
        Returns:
            Dictionary mapping call IDs to results
        """
        results = {}
        
        for tool_call in tool_calls:
            call_id = context.generate_call_id()
            
            # Execute single tool
            result = await self._execute_single_tool(
                call_id=call_id,
                tool_call=tool_call,
                context=context,
                iteration=iteration
            )
            
            results[call_id] = result
        
        return results
    
    async def _execute_parallel(
        self,
        tool_calls: List[ToolCall],
        context: ToolExecutionContext,
        iteration: IterationState
    ) -> Dict[str, ToolResult]:
        """Execute tool calls in parallel.
        
        Args:
            tool_calls: List of tool calls
            context: Execution context
            iteration: Current iteration state
            
        Returns:
            Dictionary mapping call IDs to results
        """
        logger.info(f"Executing {len(tool_calls)} tools in parallel")
        
        # Create tasks
        tasks = []
        call_ids = []
        
        for tool_call in tool_calls:
            call_id = context.generate_call_id()
            call_ids.append(call_id)
            
            task = self._execute_single_tool(
                call_id=call_id,
                tool_call=tool_call,
                context=context,
                iteration=iteration
            )
            tasks.append(task)
        
        # Execute all tasks
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Map results to call IDs
        results = {}
        for call_id, result in zip(call_ids, task_results):
            if isinstance(result, Exception):
                results[call_id] = ToolResult(error=str(result))
            else:
                results[call_id] = result
        
        return results
    
    async def _execute_single_tool(
        self,
        call_id: str,
        tool_call: ToolCall,
        context: ToolExecutionContext,
        iteration: IterationState
    ) -> ToolResult:
        """Execute a single tool call.
        
        Args:
            call_id: Unique call ID
            tool_call: Tool call to execute
            context: Execution context
            iteration: Current iteration state
            
        Returns:
            ToolResult
        """
        tool_name = tool_call.name
        args = tool_call.args
        
        logger.debug(f"Executing tool '{tool_name}' (call_id={call_id})")
        
        # Add to iteration
        iteration.add_tool_call(tool_name, args)
        
        # Validate tool exists
        if tool_name not in self.tool_registry:
            error = self.error_handler.handle_tool_not_found(tool_name)
            iteration.add_error(error.message)
            
            # Log to audit
            self.audit_logger.log_call(
                call_id=call_id,
                tool_name=tool_name,
                arguments=args,
                result_success=False,
                result_error=error.message,
                session_id=context.session_id,
                agent_id=context.agent_id,
                iteration=iteration.iteration_number
            )
            
            return error.to_result()
        
        # Check cache
        cached_result = None
        if self.enable_caching:
            cached_result = self.optimization_manager.get_cached_result(tool_name, args)
            if cached_result:
                logger.debug(f"Using cached result for {tool_name}")
                
                # Log to audit (cached)
                self.audit_logger.log_call(
                    call_id=call_id,
                    tool_name=tool_name,
                    arguments=args,
                    result_success=not cached_result.error,
                    result_output=str(cached_result.output) if cached_result.output else None,
                    result_error=cached_result.error,
                    execution_time=0.0,
                    session_id=context.session_id,
                    agent_id=context.agent_id,
                    iteration=iteration.iteration_number,
                    cached=True
                )
                
                return cached_result
        
        # Execute tool
        start_time = time.time()
        
        try:
            # Get tool instance
            tool_instance = self.tool_registry[tool_name]
            
            # Execute with timeout
            result = await asyncio.wait_for(
                tool_instance.execute(**args),
                timeout=self.timeout_per_tool
            )
            
            execution_time = time.time() - start_time
            
            # Cache result
            if self.enable_caching and not result.error:
                self.optimization_manager.cache_result(tool_name, args, result)
            
            # Log to audit
            self.audit_logger.log_call(
                call_id=call_id,
                tool_name=tool_name,
                arguments=args,
                result_success=not result.error,
                result_output=str(result.output) if result.output else None,
                result_error=result.error,
                execution_time=execution_time,
                session_id=context.session_id,
                agent_id=context.agent_id,
                iteration=iteration.iteration_number
            )
            
            logger.info(f"Tool '{tool_name}' executed successfully in {execution_time:.2f}s")
            
            return result
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            error = self.error_handler.handle_timeout(tool_name, self.timeout_per_tool)
            iteration.add_error(error.message)
            
            # Log to audit
            self.audit_logger.log_call(
                call_id=call_id,
                tool_name=tool_name,
                arguments=args,
                result_success=False,
                result_error=error.message,
                execution_time=execution_time,
                session_id=context.session_id,
                agent_id=context.agent_id,
                iteration=iteration.iteration_number
            )
            
            return error.to_result()
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Tool execution failed: {e}")
            
            # Try fallback
            if self.fallback_strategy:
                logger.info(f"Trying fallback for {tool_name}")
                fallback_result = await self.fallback_strategy.try_fallback(
                    tool_name, args, str(e)
                )
                
                if not fallback_result.error:
                    logger.info(f"Fallback successful for {tool_name}")
                    return fallback_result
            
            error = self.error_handler.handle_execution_error(tool_name, e)
            iteration.add_error(error.message)
            
            # Log to audit
            self.audit_logger.log_call(
                call_id=call_id,
                tool_name=tool_name,
                arguments=args,
                result_success=False,
                result_error=error.message,
                execution_time=execution_time,
                session_id=context.session_id,
                agent_id=context.agent_id,
                iteration=iteration.iteration_number
            )
            
            return error.to_result()
    
    def format_results_for_conversation(
        self,
        results: Dict[str, ToolResult],
        tool_calls: List[ToolCall]
    ) -> str:
        """Format tool results for injection into conversation.
        
        Args:
            results: Dictionary of results
            tool_calls: Original tool calls
            
        Returns:
            Formatted results string
        """
        if not results:
            return ""
        
        formatted = "\n\n=== Tool Execution Results ===\n\n"
        
        for call_id, result in results.items():
            # Find corresponding tool call (simplified - use call_id mapping in production)
            formatted += self.formatter.format_result(
                tool_name="tool",  # Would map from call_id
                result=result,
                include_metadata=True
            )
            formatted += "\n"
        
        return formatted


def create_tool_execution_loop(
    tool_registry: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
) -> ToolExecutionLoop:
    """Create a tool execution loop with configuration.
    
    Args:
        tool_registry: Tool registry
        config: Optional configuration
        
    Returns:
        ToolExecutionLoop instance
    """
    config = config or {}
    
    return ToolExecutionLoop(
        tool_registry=tool_registry,
        max_iterations=config.get('max_iterations', 5),
        timeout_per_tool=config.get('timeout_per_tool', 30.0),
        enable_parallel=config.get('enable_parallel', True),
        enable_caching=config.get('enable_caching', True),
        enable_fallback=config.get('enable_fallback', True)
    )
