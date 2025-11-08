"""Tool calling emulator - Main orchestration module.

This module provides the high-level interface for tool calling emulation.
It orchestrates all components to enable tool calling for LLM APIs that
don't natively support it.
"""

import uuid
from typing import Any, Callable, Dict, List, Optional

from app.logger import logger
from app.tool_calling.execution_loop import (
    ToolExecutionContext,
    ToolExecutionLoop,
)
from app.tool_calling.iteration_manager import get_iteration_manager
from app.tool_calling.response_parser import ResponseParser
from app.tool_calling.result_formatter import ResultFormatter
from app.tool_calling.system_prompts import SystemPromptGenerator


class ToolCallingEmulator:
    """Main emulator for tool calling functionality.
    
    This class provides the high-level interface for tool calling emulation.
    It manages the complete flow:
    1. Generates system prompts teaching LLM how to call tools
    2. Parses LLM responses for tool calls
    3. Executes tools (with caching, parallelization, etc.)
    4. Formats results and injects back into conversation
    5. Manages multi-turn iterations
    """
    
    def __init__(
        self,
        tool_registry: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize tool calling emulator.
        
        Args:
            tool_registry: Dictionary mapping tool names to tool instances
            config: Optional configuration dictionary
        """
        self.tool_registry = tool_registry
        self.config = config or {}
        
        # Initialize components
        self.prompt_generator = SystemPromptGenerator()
        self.parser = ResponseParser()
        self.formatter = ResultFormatter()
        self.iteration_manager = get_iteration_manager()
        
        # Initialize execution loop
        self.execution_loop = ToolExecutionLoop(
            tool_registry=tool_registry,
            max_iterations=self.config.get('max_iterations', 5),
            timeout_per_tool=self.config.get('timeout_per_tool', 30.0),
            enable_parallel=self.config.get('parallel_execution', True),
            enable_caching=self.config.get('caching_enabled', True),
            enable_fallback=self.config.get('enable_fallback', True)
        )
        
        # Register tools with prompt generator
        self._register_tools()
        
        logger.info(
            f"ToolCallingEmulator initialized with {len(tool_registry)} tools"
        )
    
    def _register_tools(self):
        """Register all tools with the prompt generator."""
        for tool_name, tool_instance in self.tool_registry.items():
            # Extract tool metadata
            description = getattr(tool_instance, 'description', '')
            parameters = getattr(tool_instance, 'parameters', {})
            
            # Register with prompt generator
            self.prompt_generator.register_tool(
                name=tool_name,
                description=description,
                parameters=parameters
            )
            
            logger.debug(f"Registered tool for prompts: {tool_name}")
    
    def generate_system_prompt(
        self,
        include_examples: bool = True,
        custom_instructions: Optional[str] = None
    ) -> str:
        """Generate system prompt for tool calling.
        
        Args:
            include_examples: Whether to include usage examples
            custom_instructions: Optional custom instructions
            
        Returns:
            Complete system prompt
        """
        return self.prompt_generator.generate_system_prompt(
            include_examples=include_examples,
            custom_instructions=custom_instructions
        )
    
    async def process_response(
        self,
        llm_response: str,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process an LLM response and execute any tool calls.
        
        Args:
            llm_response: Response from the LLM
            conversation_id: Optional conversation ID
            session_id: Optional session ID
            agent_id: Optional agent ID
            
        Returns:
            Dictionary containing:
            - has_tool_calls: bool
            - tool_results: Dict of results (if any)
            - cleaned_response: Response with tool calls removed
            - formatted_results: Formatted results for conversation
            - should_continue: Whether to continue iteration
        """
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Get or create conversation state
        state = self.iteration_manager.get_conversation(conversation_id)
        if not state:
            state = self.iteration_manager.start_conversation(
                conversation_id=conversation_id,
                max_iterations=self.config.get('max_iterations', 5)
            )
        
        # Start new iteration
        try:
            iteration = state.start_iteration()
        except RuntimeError as e:
            # Max iterations exceeded
            logger.warning(f"Max iterations exceeded for {conversation_id}")
            return {
                'has_tool_calls': False,
                'tool_results': {},
                'cleaned_response': llm_response,
                'formatted_results': '',
                'should_continue': False,
                'error': str(e)
            }
        
        # Parse response for tool calls
        tool_calls, cleaned_response = self.parser.extract_and_clean(llm_response)
        
        iteration.llm_response = llm_response
        
        if not tool_calls:
            logger.debug("No tool calls found in response")
            return {
                'has_tool_calls': False,
                'tool_results': {},
                'cleaned_response': cleaned_response,
                'formatted_results': '',
                'should_continue': False
            }
        
        logger.info(f"Found {len(tool_calls)} tool call(s) in response")
        
        # Create execution context
        context = ToolExecutionContext(
            conversation_id=conversation_id,
            session_id=session_id,
            agent_id=agent_id
        )
        
        # Execute tool calls
        tool_results = await self.execution_loop.execute_tool_calls(
            llm_response=llm_response,
            context=context,
            iteration=iteration
        )
        
        # Format results
        formatted_results = self._format_results_for_llm(tool_calls, tool_results)
        
        # Determine if should continue
        should_continue = (
            state.should_continue() and
            len(tool_results) > 0 and
            not iteration.has_errors()
        )
        
        return {
            'has_tool_calls': True,
            'tool_results': tool_results,
            'cleaned_response': cleaned_response,
            'formatted_results': formatted_results,
            'should_continue': should_continue,
            'iteration': iteration.iteration_number,
            'max_iterations': state.max_iterations
        }
    
    def _format_results_for_llm(
        self,
        tool_calls: List[Any],
        results: Dict[str, Any]
    ) -> str:
        """Format tool results for LLM consumption.
        
        Args:
            tool_calls: List of tool calls
            results: Dictionary of results
            
        Returns:
            Formatted string
        """
        if not results:
            return ""
        
        formatted = "\n\n=== Tool Results ===\n\n"
        
        # Match tool calls to results (simplified)
        for i, (call_id, result) in enumerate(results.items(), 1):
            if i <= len(tool_calls):
                tool_call = tool_calls[i-1]
                tool_name = tool_call.name
            else:
                tool_name = "unknown"
            
            formatted += self.formatter.format_result(
                tool_name=tool_name,
                result=result,
                include_metadata=True
            )
            formatted += "\n"
        
        formatted += "=== End Tool Results ===\n\n"
        formatted += "Please continue your response using the information above.\n"
        
        return formatted
    
    async def run_complete_iteration(
        self,
        initial_prompt: str,
        llm_callback: Callable[[str], str],
        max_iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run a complete tool calling iteration loop.
        
        This is a convenience method that handles the complete flow:
        1. Add system prompt to initial prompt
        2. Get LLM response
        3. Execute tool calls
        4. Inject results
        5. Repeat until complete
        
        Args:
            initial_prompt: User's initial prompt
            llm_callback: Async function that takes a prompt and returns LLM response
            max_iterations: Optional override for max iterations
            
        Returns:
            Dictionary with final response and metadata
        """
        conversation_id = str(uuid.uuid4())
        
        # Create conversation
        state = self.iteration_manager.start_conversation(
            conversation_id=conversation_id,
            max_iterations=max_iterations or self.config.get('max_iterations', 5)
        )
        
        # Generate system prompt
        system_prompt = self.generate_system_prompt()
        
        # Combine system prompt with initial prompt
        full_prompt = f"{system_prompt}\n\nUser: {initial_prompt}"
        
        current_prompt = full_prompt
        conversation_history = []
        
        while state.should_continue():
            logger.info(
                f"Iteration {state.current_iteration}/{state.max_iterations}"
            )
            
            # Get LLM response
            llm_response = await llm_callback(current_prompt)
            conversation_history.append({
                'role': 'assistant',
                'content': llm_response
            })
            
            # Process response
            result = await self.process_response(
                llm_response=llm_response,
                conversation_id=conversation_id
            )
            
            if not result['has_tool_calls']:
                # No more tool calls, we're done
                logger.info("No tool calls found, iteration complete")
                break
            
            # Add tool results to conversation
            conversation_history.append({
                'role': 'system',
                'content': result['formatted_results']
            })
            
            # Prepare next prompt
            current_prompt = result['formatted_results']
            
            if not result['should_continue']:
                break
        
        # End conversation
        final_response = conversation_history[-1]['content'] if conversation_history else ""
        self.iteration_manager.end_conversation(
            conversation_id=conversation_id,
            final_response=final_response
        )
        
        return {
            'conversation_id': conversation_id,
            'final_response': final_response,
            'conversation_history': conversation_history,
            'total_iterations': state.current_iteration,
            'total_tool_calls': state.get_total_tool_calls(),
            'summary': state.get_summary()
        }
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names.
        
        Returns:
            List of tool names
        """
        return list(self.tool_registry.keys())
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool.
        
        Args:
            tool_name: Tool name
            
        Returns:
            Tool information dictionary or None
        """
        if tool_name not in self.tool_registry:
            return None
        
        tool = self.tool_registry[tool_name]
        return {
            'name': tool_name,
            'description': getattr(tool, 'description', ''),
            'parameters': getattr(tool, 'parameters', {})
        }


def create_emulator(
    tool_registry: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
) -> ToolCallingEmulator:
    """Create a tool calling emulator.
    
    Args:
        tool_registry: Tool registry
        config: Optional configuration
        
    Returns:
        ToolCallingEmulator instance
    """
    return ToolCallingEmulator(
        tool_registry=tool_registry,
        config=config
    )
