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
            # If streaming is requested, return the generator
            if streaming:
                return self._run_with_streaming(prompt, max_steps)
            
            # Otherwise, run normally and return a single result
            agent = Manus()
            if max_steps is not None:
                agent.max_steps = max_steps
                
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
    
    async def _run_with_streaming(self, prompt: str, max_steps: Optional[int] = None) -> AsyncGenerator[str, None]:
        """Run the agent with streaming output.
        
        Yields JSON strings with progress updates and final results.
        """
        try:
            agent = Manus()
            if max_steps is not None:
                agent.max_steps = max_steps
                
            # Initialize the agent
            agent.messages = [Message.user_message(prompt)]
            agent.current_step = 0
            agent.state = AgentState.RUNNING
            
            # Yield initial status
            yield json.dumps({
                "status": "started", 
                "step": 0,
                "prompt": prompt
            })
            
            # Run steps until completion or max steps reached
            while agent.state == AgentState.RUNNING and agent.current_step < agent.max_steps:
                agent.current_step += 1
                
                # Execute a single step
                try:
                    should_act = await agent.think()
                    
                    # Yield the thinking result
                    yield json.dumps({
                        "status": "thinking",
                        "step": agent.current_step,
                        "should_act": should_act,
                        "messages": [
                            {"role": msg.role, "content": msg.content}
                            for msg in agent.memory.messages[-2:] if hasattr(msg, "role") and hasattr(msg, "content")
                        ]
                    })
                    
                    # If should act, perform the action
                    if should_act:
                        result = await agent.act()
                        
                        # Yield the action result
                        yield json.dumps({
                            "status": "acting",
                            "step": agent.current_step,
                            "result": str(result),
                            "state": agent.state.value
                        })
                    
                except Exception as e:
                    # Yield any errors that occur during processing
                    yield json.dumps({
                        "status": "error",
                        "step": agent.current_step,
                        "error": str(e)
                    })
                    agent.state = AgentState.FINISHED
                
                # Small delay to avoid overwhelming the client
                await asyncio.sleep(0.1)
                
                # Break if agent is finished
                if agent.state == AgentState.FINISHED:
                    break
            
            # Yield final result
            yield json.dumps({
                "status": "complete",
                "total_steps": agent.current_step,
                "final_state": agent.state.value,
                "messages": [
                    {"role": msg.role, "content": msg.content}
                    for msg in agent.memory.messages[-3:] if hasattr(msg, "role") and hasattr(msg, "content")
                ]
            })
            
        except Exception as e:
            # Yield any exceptions that occur
            yield json.dumps({
                "status": "error",
                "error": str(e)
            })
