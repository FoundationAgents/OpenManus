from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional, AsyncGenerator # 添加 AsyncGenerator

from pydantic import BaseModel, Field, model_validator

from app.llm import LLM
from app.logger import logger
from app.sandbox.client import SANDBOX_CLIENT
from app.schema import ROLE_TYPE, AgentState, Memory, Message


class BaseAgent(BaseModel, ABC):
    """Abstract base class for managing agent state and execution.

    Provides foundational functionality for state transitions, memory management,
    and a step-based execution loop. Subclasses must implement the `step` method.
    """

    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")

    # Prompts
    system_prompt: Optional[str] = Field(
        None, description="System-level instruction prompt"
    )
    next_step_prompt: Optional[str] = Field(
        None, description="Prompt for determining next action"
    )

    # Dependencies
    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    memory: Memory = Field(default_factory=Memory, description="Agent's memory store")
    state: AgentState = Field(
        default=AgentState.IDLE, description="Current agent state"
    )

    # Execution control
    max_steps: int = Field(default=10, description="Maximum steps before termination")
    current_step: int = Field(default=0, description="Current step in execution")

    duplicate_threshold: int = 2

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"  # Allow extra fields for flexibility in subclasses

    @model_validator(mode="after")
    def initialize_agent(self) -> "BaseAgent":
        """Initialize agent with default settings if not provided."""
        if self.llm is None or not isinstance(self.llm, LLM):
            self.llm = LLM(config_name=self.name.lower())
        if not isinstance(self.memory, Memory):
            self.memory = Memory()
        return self

    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """Context manager for safe agent state transitions.

        Args:
            new_state: The state to transition to during the context.

        Yields:
            None: Allows execution within the new state.

        Raises:
            ValueError: If the new_state is invalid.
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")

        previous_state = self.state
        self.state = new_state
        try:
            yield
        except Exception as e:
            # Don't automatically revert state on error if it was handled inside loop
            if self.state != AgentState.ERROR:
                 self.state = AgentState.ERROR # Transition to ERROR if not already set
            raise e
        finally:
            # Only revert if the final state inside the context was the 'new_state'
            # If it changed to FINISHED or ERROR, keep that state.
            if self.state == new_state:
                 self.state = previous_state # Revert only if state wasn't finalized

    def update_memory(
        self,
        role: ROLE_TYPE,  # type: ignore
        content: str,
        base64_image: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Add a message to the agent's memory.

        Args:
            role: The role of the message sender (user, system, assistant, tool).
            content: The message content.
            base64_image: Optional base64 encoded image.
            **kwargs: Additional arguments (e.g., tool_call_id for tool messages).

        Raises:
            ValueError: If the role is unsupported.
        """
        message_map = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda content, **kw: Message.tool_message(content, **kw),
        }

        if role not in message_map:
            raise ValueError(f"Unsupported message role: {role}")

        # Build arguments specific to the message type
        msg_kwargs = {}
        if role in ["user", "assistant", "tool"] and base64_image:
            msg_kwargs["base64_image"] = base64_image

        # Add other relevant kwargs based on role
        if role == "tool":
            # Pass tool_call_id etc. if provided in kwargs
            msg_kwargs.update(kwargs)
        elif role == "assistant":
             # Pass tool_calls etc. if provided in kwargs
             msg_kwargs.update(kwargs)
        # System messages don't take extra kwargs from this function's perspective

        # Call the appropriate message constructor
        self.memory.add_message(message_map[role](content, **msg_kwargs))


    async def run(self, request: Optional[str] = None) -> AsyncGenerator[str, None]: # 修改返回类型提示
        """Execute the agent's main loop asynchronously, yielding updates."""
        if self.state != AgentState.IDLE and self.state != AgentState.FINISHED and self.state != AgentState.ERROR:
             # Allow rerunning if finished or errored, but not if already running
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        # Reset state for a new run
        self.current_step = 0
        self.state = AgentState.IDLE # Ensure starting state is IDLE

        # If a request is provided, it's added to the existing memory.
        if request:
            # Avoid adding duplicate user message if memory already ends with it
            if not self.memory.messages or self.memory.messages[-1].role != "user" or self.memory.messages[-1].content != request:
                 self.update_memory("user", request)

        cumulative_output = "" # Accumulate output for the current turn for Gradio streaming
        async with self.state_context(AgentState.RUNNING):
            while (
                self.current_step < self.max_steps and self.state != AgentState.FINISHED
            ):
                self.current_step += 1
                logger.info(f"Executing step {self.current_step}/{self.max_steps}")

                memory_before_step = len(self.memory.messages)
                try:
                    # step() should handle its own state updates and memory additions
                    await self.step()
                except Exception as e:
                    logger.error(f"Error during step {self.current_step}: {e}", exc_info=True)
                    error_msg = f"Error during step {self.current_step}: {str(e)}"
                    # Add error to memory *if not already added by step()*
                    if not self.memory.messages or self.memory.messages[-1].content != error_msg:
                         self.update_memory("system", error_msg)
                    self.state = AgentState.ERROR # Ensure state is ERROR
                    # Yield the error immediately
                    new_messages_on_error = self.memory.messages[memory_before_step:]
                    error_output = ""
                    for msg in new_messages_on_error:
                         if msg.role == "system": # Assuming error is logged as system msg
                              error_output += f"\n\n**Error:**\n{msg.content}"
                    if error_output:
                         cumulative_output += error_output
                         yield cumulative_output # Yield current state including error
                    break # Exit the loop on error

                # Check for stuck state *after* the step
                if self.is_stuck():
                    # handle_stuck_state modifies the *next* prompt, doesn't yield directly
                    self.handle_stuck_state()

                # --- Yield new messages added during the step ---
                new_messages = self.memory.messages[memory_before_step:]
                step_output = ""
                for msg in new_messages:
                    # Format message based on role for better display
                    if msg.role == "assistant":
                        thought_prefix = "Thinking:\n" if msg.content else ""
                        tool_calls_str = ""
                        if msg.tool_calls:
                            tool_calls_str = "\nRequesting Tools:\n" + "\n".join([f"- {tc.function.name}({tc.function.arguments or '{}'})" for tc in msg.tool_calls])
                        step_output += f"\n\n**Assistant Thoughts/Plan (Step {self.current_step}):**\n{thought_prefix}{msg.content or ''}{tool_calls_str}"
                    elif msg.role == "tool":
                        # Try to format tool output nicely, handle potential long outputs
                        tool_content = str(msg.content)
                        if len(tool_content) > 500: # Truncate long tool outputs for UI clarity
                            tool_content = tool_content[:500] + "..."
                        step_output += f"\n\n**Tool Result ({msg.name}):**\n```\n{tool_content}\n```"
                    elif msg.role == "system" and "stuck state" in str(msg.content): # Show stuck warning
                         step_output += f"\n\n**System Note:**\n{msg.content}"
                    # Ignore user messages added during run, and other system messages unless needed

                if step_output:
                    cumulative_output += step_output
                    yield cumulative_output # Yield the accumulated output for this turn

                # Check if agent finished *after* processing step results
                if self.state == AgentState.FINISHED:
                    logger.info("Agent finished execution.")
                    # Optionally add a final "Finished" message?
                    # cumulative_output += "\n\n**Agent Finished**"
                    # yield cumulative_output
                    break

            # --- End of loop ---
            if self.current_step >= self.max_steps and self.state != AgentState.FINISHED and self.state != AgentState.ERROR:
                termination_msg = f"Terminated: Reached max steps ({self.max_steps})"
                logger.warning(termination_msg)
                # Add to memory?
                # self.update_memory("system", termination_msg)
                cumulative_output += f"\n\n**System Note:**\n{termination_msg}"
                yield cumulative_output # Yield final termination message

        # Final cleanup outside the state context
        # Only cleanup if the agent owns the sandbox exclusively? Might need adjustment.
        # await SANDBOX_CLIENT.cleanup() # Commented out for now

        # Ensure state reflects reality after loop exit
        if self.state == AgentState.RUNNING: # If loop finished due to max_steps but not explicitly set to FINISHED/ERROR
             self.state = AgentState.IDLE # Revert to IDLE if max steps reached without finish/error

    @abstractmethod
    async def step(self) -> str:
        """Execute a single step in the agent's workflow.

        Must be implemented by subclasses to define specific behavior.
        Should update self.memory and potentially self.state.
        Return value is not directly used by the new run generator.
        """
        pass # Make it concrete for type checking, subclasses override

    def handle_stuck_state(self):
        """Handle stuck state by adding a prompt to change strategy"""
        stuck_prompt = "\
        Observed duplicate responses. Consider new strategies and avoid repeating ineffective paths already attempted."
        # Add as a system message instead of modifying next_step_prompt directly
        self.update_memory("system", stuck_prompt)
        logger.warning(f"Agent detected stuck state. Added system message: {stuck_prompt}")

    def is_stuck(self) -> bool:
        """Check if the agent is stuck in a loop by detecting duplicate assistant content"""
        if len(self.memory.messages) < self.duplicate_threshold * 2: # Need enough history
            return False

        # Look at the last few assistant messages
        last_assistant_msgs = [msg for msg in self.memory.messages[-self.duplicate_threshold*2:] if msg.role == "assistant"]
        if len(last_assistant_msgs) < self.duplicate_threshold:
             return False

        last_content = last_assistant_msgs[-1].content
        if not last_content: # Ignore empty content
             return False

        # Check if the last 'duplicate_threshold' assistant messages have the same content
        return all(msg.content == last_content for msg in last_assistant_msgs[-self.duplicate_threshold:])


    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value
