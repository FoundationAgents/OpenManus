"""ManusAgentTool for exposing the Manus agent as an MCP tool."""

import asyncio
import json
import os
from typing import AsyncGenerator, Optional, Union

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
            "max_steps": {
                "type": "integer",
                "description": "Maximum number of steps the agent can take (default: use agent's default)",
                "default": 80
            }
        },
        "required": ["prompt"]
    }

    async def execute(self, prompt: str, max_steps: Optional[int] = None, **kwargs) -> Union[ToolResult, AsyncGenerator[str, None]]:
        """Execute the Manus agent with the given prompt.

        Args:
            prompt: The user prompt to process
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

            # Check if streaming should be used based on server setting only
            server_streaming = os.environ.get("MCP_SERVER_STREAMING", "false").lower() == "true"
            logger.info(f"Server streaming setting: {server_streaming}")

            # If server has streaming enabled, use the streaming generator
            if server_streaming:
                logger.info(f"Using streaming mode for prompt: {prompt}")
                # This function returns an async generator that will yield string results
                return self._run_with_streaming(prompt, max_steps, agent)

            # Otherwise, run non-streaming version where we directly run the agent
            # and capture the final thought
            logger.info(f"Running Manus agent with prompt: {prompt}")

            # Initialize the agent
            agent.messages = [Message.user_message(prompt)]
            agent.current_step = 0
            agent.state = AgentState.RUNNING

            # Track the last two thoughts
            thoughts = []

            # Run steps until completion or max steps reached
            while agent.state == AgentState.RUNNING and agent.current_step < agent.max_steps:
                agent.current_step += 1

                try:
                    # Execute thinking step
                    should_act = await agent.think()

                    # Capture the most recent thought
                    last_messages = [msg for msg in agent.memory.messages
                                  if hasattr(msg, "role") and msg.role == "assistant"
                                  and hasattr(msg, "content") and msg.content.strip()]

                    # Store thought if it exists
                    if last_messages:
                        current_thought = last_messages[-1].content
                        if current_thought not in thoughts:  # avoid duplicates
                            thoughts.append(current_thought)

                    # If should act, perform the action
                    if should_act:
                        await agent.act()

                except Exception as e:
                    logger.error(f"Error in agent step {agent.current_step}: {str(e)}")
                    agent.state = AgentState.FINISHED

                # Break if agent is finished
                if agent.state == AgentState.FINISHED:
                    break

            # Process the collected thoughts
            processed_thoughts = []

            # Get the last two thoughts (or fewer if not enough)
            last_n_thoughts = thoughts[-2:] if len(thoughts) >= 2 else thoughts

            # Add thought marker to each thought if not already present
            for i, thought in enumerate(last_n_thoughts):
                if not any(marker in thought for marker in ["✨ Manus's thoughts:", "Manus's thoughts:"]):
                    processed_thoughts.append(f"✨ Manus's thoughts {i+1}: {thought}")
                else:
                    processed_thoughts.append(thought)

            # Join thoughts with a separator
            final_output = "\n\n---\n\n".join(processed_thoughts)

            # Return the thoughts in a clean structure
            logger.info(f"Completed processing in {agent.current_step} steps, captured {len(processed_thoughts)} thoughts")
            return ToolResult(
                output=json.dumps({
                    "status": "complete",
                    "thoughts": final_output
                })
            )

        except Exception as e:
            logger.error(f"Error running Manus agent: {str(e)}")
            return ToolResult(
                error=f"Error running Manus agent: {str(e)}"
            )

    async def _run_with_streaming(self, prompt: str, max_steps: Optional[int] = None, agent: Optional[Manus] = None) -> AsyncGenerator[str, None]:
        """Run the agent with streaming output.

        Yields JSON strings with progress updates and directly captures the final thought.
        The implementation mirrors the non-streaming version but yields progress updates.
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

            # Yield initial status
            initial_status = json.dumps({
                "status": "started",
                "step": 0,
                "message": f"Processing: '{prompt[:50]}{'...' if len(prompt) > 50 else ''}"
            })
            logger.info(f"Started processing with prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
            yield initial_status

            # Track thoughts for final output
            thoughts = []

            # Run steps until completion or max steps reached
            while agent.state == AgentState.RUNNING and agent.current_step < agent.max_steps:
                agent.current_step += 1

                # Execute a single step
                try:
                    should_act = await agent.think()

                    # Get messages that contain thinking
                    last_messages = [msg for msg in agent.memory.messages
                                   if hasattr(msg, "role") and msg.role == "assistant"
                                   and hasattr(msg, "content") and msg.content.strip()]

                    # Store thought if it exists and is not a duplicate
                    if last_messages:
                        current_thought = last_messages[-1].content
                        if current_thought not in thoughts:  # avoid duplicates
                            thoughts.append(current_thought)

                    # Yield a progress update
                    yield json.dumps({
                        "status": "thinking",
                        "step": agent.current_step
                    })

                    # If should act, perform the action
                    if should_act:
                        await agent.act()

                        # Yield an action progress update
                        yield json.dumps({
                            "status": "acting",
                            "step": agent.current_step
                        })

                except Exception as e:
                    # Yield any errors that occur during processing
                    error_msg = str(e)
                    yield json.dumps({
                        "status": "error",
                        "step": agent.current_step,
                        "error": error_msg
                    })
                    agent.state = AgentState.FINISHED

                # Small delay to avoid overwhelming the client
                await asyncio.sleep(0.05)

                # Break if agent is finished
                if agent.state == AgentState.FINISHED:
                    break

            # Process the collected thoughts
            processed_thoughts = []

            # Get the last two thoughts (or fewer if not enough)
            last_n_thoughts = thoughts[-2:] if len(thoughts) >= 2 else thoughts

            # Add thought marker to each thought if not already present
            for i, thought in enumerate(last_n_thoughts):
                if not any(marker in thought for marker in ["✨ Manus's thoughts:", "Manus's thoughts:"]):
                    processed_thoughts.append(f"✨ Manus's thoughts {i+1}: {thought}")
                else:
                    processed_thoughts.append(thought)

            # Join thoughts with a separator
            final_output = "\n\n---\n\n".join(processed_thoughts)

            # Log completion
            logger.info(f"Completed processing in {agent.current_step} steps, captured {len(processed_thoughts)} thoughts")

            # Yield the combined thoughts in the result
            final_result = json.dumps({
                "status": "complete",
                "thoughts": final_output
            })
            yield final_result

        except Exception as e:
            # Yield any exceptions that occur
            error_msg = json.dumps({
                "status": "error",
                "error": str(e)
            })
            logger.error(f"Streaming error: {str(e)}")
            yield error_msg
