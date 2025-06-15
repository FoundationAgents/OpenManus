from typing import List

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.prompt.swe import SYSTEM_PROMPT
from app.tool import Bash, StrReplaceEditor, Terminate, ToolCollection
from app.tool.ask_human import AskHuman # Added import
from app.logger import logger # Added import
from app.schema import AgentState # Added import


class SWEAgent(ToolCallAgent):
    """An agent that implements the SWEAgent paradigm for executing code and natural conversations."""

    name: str = "swe"
    description: str = "an autonomous AI programmer that interacts directly with the computer to solve tasks."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = ""

    available_tools: ToolCollection = ToolCollection(
        Bash(), StrReplaceEditor(), Terminate(), AskHuman() # Added AskHuman
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    max_steps: int = 50 # Increased max_steps

    async def should_request_feedback(self) -> bool:
        """Determines if the agent should pause and request user feedback.

        This method implements the logic for deciding when to ask for feedback
        based on criteria like being stuck, facing ambiguity, or missing critical information.
        """
        # 1. Check if the agent is stuck (using existing mechanism)
        if self.is_stuck():
            logger.info("Feedback condition: Agent is stuck (duplicate responses).")
            # Ensure there's a question to ask, perhaps by setting a default or using the stuck prompt.
            # For now, we assume the LLM will use ask_human based on the system prompt if it's stuck.
            # We might need a more direct way to set the question for ask_human here.
            self.update_memory("system", "You seem to be stuck. Consider asking the user for guidance using the 'ask_human' tool if you are unsure how to proceed.")
            return True

        # 2. Check for keywords indicating ambiguity or missing information in recent memory
        # Look at the last few messages for tell-tale signs.
        # This is a simple heuristic and can be expanded.
        recent_messages_to_check = 3
        keywords = ["not provided", "unclear", "missing api key", "what is the value", "unknown parameter", "clarify"]
        
        for message in self.memory.messages[-recent_messages_to_check:]:
            if message.content: # Ensure content is not None
                for keyword in keywords:
                    if keyword in message.content.lower():
                        logger.info(f"Feedback condition: Keyword '{keyword}' found in recent messages.")
                        # Prompt the LLM to ask a question.
                        self.update_memory("system", f"It seems there's some uncertainty (related to '{keyword}'). Please use the 'ask_human' tool to ask the user for clarification or missing information.")
                        return True
        
        # 3. Placeholder for checking for repeated failed attempts
        # TODO: Implement logic to detect repeated failed tool executions or lack of progress towards a goal.
        # This might involve analyzing tool execution results or other progress metrics.
        # For example, if the last N tool calls resulted in errors or no change in state.

        # 4. Check for excessive steps without finishing (as a fallback)
        # This is a softer version of the old interaction_interval, but more of a "are we taking too long?" check.
        # Only trigger if a significant number of steps have passed without resolution.
        if self.current_step > (self.max_steps * 0.75) and self.state != AgentState.FINISHED:
             logger.info(f"Feedback condition: Agent has taken {self.current_step} steps without finishing.")
             self.update_memory("system", "You've taken a significant number of steps. If you're not confident in the current path, consider using 'ask_human' to check in with the user or ask for guidance.")
             return True

        return False
