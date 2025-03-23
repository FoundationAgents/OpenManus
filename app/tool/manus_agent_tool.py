"""ManusAgentTool for exposing the Manus agent as an MCP tool."""

import asyncio
import json
import os
import re
from typing import AsyncGenerator, Dict, Optional, Union

from app.agent.manus import Manus
from app.logger import logger
from app.schema import AgentState, Message
from app.tool.base import BaseTool, ToolResult

# Summary extraction configuration constants
MIN_STEP_CONTENT_LENGTH = 100  # Minimum length (chars) for step content to be considered substantial
MAX_STEP_CONTENT_LENGTH = 10000  # Maximum length to return from a step before truncating
FALLBACK_CONTENT_LENGTH = 800   # Number of chars to extract from end of result if no good step is found


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

            # Otherwise, run normally and return a single result
            logger.info(f"Running Manus agent with prompt: {prompt}")
            result = await agent.run(prompt)

            # Extract a summary from the verbose result
            summary = self._extract_summary_from_result(result)
            logger.info(f"Manus agent completed processing, extracted summary from result")

            # Return the summarized result instead of the full verbose output
            return ToolResult(
                output=json.dumps({
                    "status": "complete",
                    "result": summary,
                    "full_result": result  # Keep full result available if needed but don't display it by default
                })
            )

        except Exception as e:
            logger.error(f"Error running Manus agent: {str(e)}")
            return ToolResult(
                error=f"Error running Manus agent: {str(e)}"
            )

    def _extract_summary_from_result(self, result: str) -> str:
        """Extract a concise summary from the agent's result.

        Analyzes the structured data and step outputs to identify the most meaningful content.
        Priority is given to the final JSON output if available, followed by step-based extraction.
        """
        logger.debug(f"Extracting summary from result of length {len(result)}")

        # First, check for JSON data which often contains the structured final result
        json_start = result.find('{')
        json_end = result.rfind('}')

        if json_start != -1 and json_end != -1 and json_end > json_start:
            try:
                # Extract and parse the JSON content
                json_text = result[json_start:json_end+1]
                data = json.loads(json_text)

                # If we have valid JSON data, create a compact summary of keys and values
                summary_lines = ["Summary of results:"]

                # Limit the output to important top-level keys
                for key, value in data.items():
                    # Skip metadata and context keys that aren't directly useful
                    if key.lower() in ['metadata', 'context', 'debug_info', 'raw_data']:
                        continue

                    # Handle different value types appropriately
                    if isinstance(value, dict):
                        # For nested dictionaries, show a sample of key-value pairs
                        nested_items = list(value.items())[:3]  # Show only first 3 items
                        nested_preview = ", ".join([f"{k}: {str(v)[:50]}" for k, v in nested_items])
                        summary_lines.append(f"- {key}: {{{nested_preview}}}")
                        if len(value) > 3:
                            summary_lines.append(f"  ...and {len(value)-3} more entries")
                    elif isinstance(value, list):
                        # For lists, show the count and a preview
                        list_len = len(value)
                        if list_len > 0:
                            preview = str(value[0])[:50]
                            if len(preview) == 50:
                                preview += "..."
                            summary_lines.append(f"- {key}: [{list_len} items, first: {preview}]")
                        else:
                            summary_lines.append(f"- {key}: [empty list]")
                    else:
                        # For simple values, show directly with truncation
                        val_str = str(value)
                        if len(val_str) > 100:
                            val_str = val_str[:100] + "..."
                        summary_lines.append(f"- {key}: {val_str}")

                # If we have a decent summary, return it
                if len(summary_lines) > 1:  # More than just the header
                    return "\n".join(summary_lines)

                # If the summary was empty or had only system keys, fall through to step-based extraction

            except json.JSONDecodeError:
                logger.debug("Failed to decode JSON in the result")

        # If JSON extraction failed or was not useful, try to find the most informative steps
        steps = result.split("Step ")
        last_step_with_results = None
        last_step_content = ""

        # Go backwards through the steps to find the last one with meaningful results
        if len(steps) > 1:
            for i in range(len(steps)-1, 0, -1):  # Start from the last step
                step = steps[i]
                # Skip termination steps
                if "terminate" in step or "The interaction has been completed" in step:
                    continue

                # Look for steps with extracted data or meaningful content
                if "Extracted from page" in step or "Extracted text" in step or "Result:" in step:
                    # Try to extract the content after these markers
                    for marker in ["Extracted from page:", "Extracted text:", "Result:"]:
                        marker_pos = step.find(marker)
                        if marker_pos != -1:
                            # Extract content after the marker, up to next step or end
                            content_start = marker_pos + len(marker)
                            extract = step[content_start:].strip()

                            # If we have substantial content, use it
                            if len(extract) > MIN_STEP_CONTENT_LENGTH:
                                last_step_with_results = i
                                last_step_content = extract
                                break

                # If we haven't found specific extracts, check for any substantial content
                if len(step.strip()) > MIN_STEP_CONTENT_LENGTH and not last_step_with_results:
                    # Look for content after "Agent:" or "Observation:" markers
                    for marker in ["Agent:", "Observation:", "Action:"]:
                        marker_pos = step.find(marker)
                        if marker_pos != -1:
                            # Extract content after the marker
                            content_start = marker_pos + len(marker)
                            extract = step[content_start:].strip()

                            # If we have substantial content, use it
                            if len(extract) > MIN_STEP_CONTENT_LENGTH:
                                last_step_with_results = i
                                last_step_content = extract
                                break

                    # If no marker-based content was found, use the whole step
                    if not last_step_content and len(step.strip()) > MIN_STEP_CONTENT_LENGTH:
                        last_step_with_results = i
                        last_step_content = step.strip()

        if last_step_with_results and last_step_content:
            # Clean up and format the content
            if len(last_step_content) > MAX_STEP_CONTENT_LENGTH:
                last_step_content = last_step_content[:MAX_STEP_CONTENT_LENGTH] + "..."
            logger.debug(f"Using content from step {last_step_with_results}")
            return f"Step {last_step_with_results} result: {last_step_content}"

        # If all else fails, return a reasonable section from the end of the result
        if len(result) > FALLBACK_CONTENT_LENGTH:
            end_content = result[-FALLBACK_CONTENT_LENGTH:].strip()
            logger.debug(f"Using last {FALLBACK_CONTENT_LENGTH} characters as summary")
            return end_content

        # For short results, just return the whole thing
        return result.strip()

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
