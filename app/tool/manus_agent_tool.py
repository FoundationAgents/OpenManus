"""ManusAgentTool for exposing the Manus agent as an MCP tool."""

import asyncio
import json
from typing import AsyncGenerator, Dict, Optional, Union

from app.agent.manus import Manus
from app.logger import logger
from app.schema import AgentState, Message
from app.tool.base import BaseTool, ToolResult


class ManusAgentTool(BaseTool):
    """Tool that exposes the Manus agent as a single MCP tool.
    
    This tool provides a high-level interface to the Manus agent, allowing
    clients to send a prompt and receive the full agent processing results.
    """
    
    name: str = "manus_agent"
    description: str = "Runs the Manus agent to process user requests using multiple capabilities"
    parameters: dict = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The user's prompt or request to process"
            },
            "streaming": {
                "type": "boolean",
                "description": "Whether to stream results as they become available (only works with SSE transport)",
                "default": False
            },
            "max_steps": {
                "type": "integer",
                "description": "Maximum number of steps the agent can take (default: use agent's default)",
                "default": None
            }
        },
        "required": ["prompt"]
    }
    
    async def execute(self, prompt: str, streaming: bool = False, max_steps: Optional[int] = None, **kwargs) -> Union[ToolResult, AsyncGenerator[str, None]]:
        """Execute the Manus agent with the given prompt.
        
        Args:
            prompt: The user prompt to process
            streaming: Whether to stream results (only works with SSE transport)
            max_steps: Maximum number of agent steps (None uses agent default)
            
        Returns:
            Either a ToolResult with the final result, or an AsyncGenerator for streaming
        """
        try:
            # Create Manus agent instance - do this first to ensure imports work
            logger.info(f"Creating Manus agent instance for prompt: {prompt}")
            agent = Manus()
            if max_steps is not None:
                agent.max_steps = max_steps
                
            # If streaming is requested, return the streaming generator 
            if streaming:
                logger.info(f"Using streaming mode for prompt: {prompt}")
                # This function returns an async generator that will yield string results
                return self._run_with_streaming(prompt, max_steps, agent)
            
            # Otherwise, run normally and return a single result
            logger.info(f"Running Manus agent with prompt: {prompt}")
            result = await agent.run(prompt)
            
            # Return the agent's final result
            logger.info(f"Manus agent completed processing")
            return ToolResult(
                output=json.dumps({
                    "status": "complete",
                    "result": result
                })
            )
            
        except Exception as e:
            logger.error(f"Error running Manus agent: {str(e)}")
            return ToolResult(
                error=f"Error running Manus agent: {str(e)}"
            )
    
    def _extract_summary_from_result(self, result: str) -> str:
        """Extract a concise summary from a detailed result.
        
        This analyzes the result string to extract key information and summarize it.
        """
        try:
            # Try to parse as JSON
            data = json.loads(result)
            
            # Handle browser_use tool results
            if isinstance(data, dict):
                # Check if this is a flight search result
                if 'flight_search_details' in data:
                    route = data.get('flight_search_details', {}).get('route', 'Unknown route')
                    dates = data.get('flight_search_details', {}).get('dates', 'Unknown dates')
                    cheapest = next((f['price'] for f in data.get('available_flights', []) if f.get('price')), 'Unknown')
                    fastest = next((f"Duration: {f['duration']}" for f in data.get('available_flights', []) 
                                    if f.get('duration') and 'Nonstop' in f.get('stops', '')), 'No nonstop flights')
                    return f"Flight search for {route}, {dates}. Cheapest: {cheapest}. {fastest}"
                
                # Summary for extracted page content
                if any(key in data for key in ['interactive_elements', 'available_flights', 'flight_search']):
                    return f"Extracted page information with {len(data)} data points"
                    
            # If we can't generate a specific summary, create a general one
            return f"Result: {result[:150]}..." if len(result) > 150 else f"Result: {result}"
                
        except (json.JSONDecodeError, TypeError, ValueError):
            # For non-JSON results or other errors, return a truncated version
            return f"Result: {result[:100]}..." if len(result) > 100 else f"Result: {result}"
    
    async def _run_with_streaming(self, prompt: str, max_steps: Optional[int] = None, agent: Optional[Manus] = None) -> AsyncGenerator[str, None]:
        """Run the agent with streaming output.
        
        Yields JSON strings with progress updates and final results.
        Provides concise summaries instead of verbose output for better readability.
        """
        try:
            # Create agent if not provided
            if agent is None:
                logger.info(f"Creating new Manus agent for streaming")
                agent = Manus()
                if max_steps is not None:
                    agent.max_steps = max_steps
            
            # Initialize the agent
            logger.info(f"Initializing agent for streaming with prompt: {prompt}")
            agent.messages = [Message.user_message(prompt)]
            agent.current_step = 0
            agent.state = AgentState.RUNNING
            
            # Yield initial status with more useful information
            initial_status = json.dumps({
                "status": "started", 
                "step": 0,
                "message": f"Starting to process: '{prompt[:50]}{'...' if len(prompt) > 50 else ''}'"
            })
            logger.info(f"Yielding initial status: {initial_status}")
            yield initial_status
            
            # Track actions for final summary
            actions_summary = []
            
            # Run steps until completion or max steps reached
            while agent.state == AgentState.RUNNING and agent.current_step < agent.max_steps:
                agent.current_step += 1
                
                # Execute a single step
                try:
                    should_act = await agent.think()
                    
                    # Get the last message content for a thinking summary
                    last_messages = [msg for msg in agent.memory.messages[-2:] 
                                   if hasattr(msg, "role") and hasattr(msg, "content")]
                    thinking_content = last_messages[-1].content if last_messages else "No content available"
                    
                    # Create a more concise thinking summary
                    thinking_summary = thinking_content[:150] + "..." if len(thinking_content) > 150 else thinking_content
                    
                    # Yield a concise thinking result
                    yield json.dumps({
                        "status": "thinking",
                        "step": agent.current_step,
                        "content": thinking_summary
                    })
                    
                    # If should act, perform the action
                    if should_act:
                        result = await agent.act()
                        result_str = str(result)
                        
                        # Extract useful summary from the action result
                        summary = self._extract_summary_from_result(result_str)
                        actions_summary.append(f"Step {agent.current_step}: {summary}")
                        
                        # Yield the action result with concise summary
                        yield json.dumps({
                            "status": "acting",
                            "step": agent.current_step,
                            "action": summary
                        })
                    
                except Exception as e:
                    # Yield any errors that occur during processing
                    error_msg = str(e)
                    yield json.dumps({
                        "status": "error",
                        "step": agent.current_step,
                        "error": error_msg
                    })
                    actions_summary.append(f"Step {agent.current_step}: Error - {error_msg}")
                    agent.state = AgentState.FINISHED
                
                # Small delay to avoid overwhelming the client
                await asyncio.sleep(0.1)
                
                # Break if agent is finished
                if agent.state == AgentState.FINISHED:
                    break
            
            # Get final response from agent memory
            last_messages = [msg for msg in agent.memory.messages[-3:] 
                           if hasattr(msg, "role") and hasattr(msg, "content")]
            final_content = last_messages[-1].content if last_messages else "No final content available"
            
            # Create shortened version for the response
            short_content = final_content[:300] + "..." if len(final_content) > 300 else final_content
            
            # Yield final result with concise summary and important details only
            final_result = json.dumps({
                "status": "complete",
                "content": short_content,
                "steps_summary": actions_summary[-3:] if len(actions_summary) > 3 else actions_summary
            })
            logger.info(f"Yielding final result summary: {final_result[:100]}..." if len(final_result) > 100 else f"Yielding final result: {final_result}")
            yield final_result
            
        except Exception as e:
            # Yield any exceptions that occur
            error_msg = json.dumps({
                "status": "error",
                "error": str(e)
            })
            logger.error(f"Streaming error: {str(e)}")
            logger.info(f"Yielding error: {error_msg}")
            yield error_msg
