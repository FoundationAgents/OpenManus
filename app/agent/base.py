import asyncio
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional

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
    user_pause_requested_event: asyncio.Event = Field(default_factory=asyncio.Event, description="Event to signal a user-initiated pause.")
    # interaction_interval: int = 20 # Interval for periodic user interaction - Removed as per new design
    tool_calls: Optional[List[dict]] = Field(default=None, description="Tool calls generated in the last step")

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
        self.state = new_state # Actual assignment happens here
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR  # Transition to ERROR on failure
            raise e
        finally:
            # Only revert to previous_state if the state wasn't set to a terminal one
            # within the context.
            if self.state not in [
                AgentState.FINISHED,
                AgentState.ERROR,
                AgentState.USER_HALTED,
                AgentState.AWAITING_USER_FEEDBACK,
                AgentState.USER_PAUSED, # Add this line
            ]:
                self.state = previous_state
            else:
                pass # State is terminal or AWAITING_USER_FEEDBACK, not reverting.
            # If it IS a terminal state, leave it as is.

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

        # Create message with appropriate parameters based on role
        kwargs = {"base64_image": base64_image, **(kwargs if role == "tool" else {})}
        self.memory.add_message(message_map[role](content, **kwargs))

    async def run(self, request: Optional[str] = None) -> str:
        # Step 0: Initial validation and state setup
        if self.state == AgentState.IDLE:
            if request:
                self.update_memory("user", request)
            self.state = AgentState.RUNNING
        elif self.state == AgentState.AWAITING_USER_FEEDBACK:
            if request: # Se um novo request/input do usuário for fornecido diretamente ao run()
                self.update_memory("user", request)
                self.state = AgentState.RUNNING # Mudar para RUNNING para processar o novo request
            else: # Se run() for chamado sem novo request, mas esperamos que o feedback já esteja na memória
                self.state = AgentState.RUNNING # Mudar para RUNNING para continuar o processamento
        elif self.state == AgentState.RUNNING: # Explicitly allow re-calling run if already running (e.g. internal restart)
             if request: # If a new request is passed, it might mean a change of plans.
                 self.update_memory("user", request)
        else:
            logger.error(f"Run method called on agent in an unstartable/unresumable state: {self.state.value}. Raising RuntimeError.")
            raise RuntimeError(f"Cannot run/resume agent from state: {self.state.value}")

        results: List[str] = []

        outer_loop_iterations = 0
        while self.state == AgentState.RUNNING: # Modified loop condition
            outer_loop_iterations += 1

            # REMOVED THE IF BLOCK that transitioned AWAITING_USER_FEEDBACK to RUNNING here
            
            async with self.state_context(AgentState.RUNNING): # new_state is RUNNING
                
                while self.state not in [AgentState.FINISHED, AgentState.ERROR, AgentState.USER_HALTED, AgentState.USER_PAUSED]:
                    self.current_step += 1

                    if hasattr(self, 'user_pause_requested_event') and self.user_pause_requested_event.is_set():
                        self.user_pause_requested_event.clear()
                        self.state = AgentState.USER_PAUSED
                        break # Break the inner step execution loop

                    if await self.should_request_feedback():
                        self.state = AgentState.AWAITING_USER_FEEDBACK 
                        break 
                    
                    if self.state in [AgentState.FINISHED, AgentState.ERROR, AgentState.USER_HALTED, AgentState.AWAITING_USER_FEEDBACK]:
                        break

                    step_result = await self.step() 
                    results.append(f"Step {self.current_step}: {step_result}") # step_result can be very long, so original log is better

                    if self.is_stuck():
                        self.handle_stuck_state() 
                
            # After state_context is done:
            if self.state == AgentState.AWAITING_USER_FEEDBACK:
                break
            elif self.state == AgentState.USER_PAUSED:
                break

            if self.state not in [AgentState.RUNNING]: # If state changed to FINISHED, ERROR, USER_HALTED inside context
                break
            
        # New conditional logic for determining final agent state
        if self.state == AgentState.USER_HALTED:
            pass
            # State remains USER_HALTED. No reset to IDLE here.
        elif self.state == AgentState.AWAITING_USER_FEEDBACK:
            pass
            # State remains AWAITING_USER_FEEDBACK.
        elif self.state == AgentState.USER_PAUSED:
            # State remains USER_PAUSED.
            pass
        elif self.current_step >= self.max_steps and self.max_steps > 0:
            self.state = AgentState.FINISHED
        elif not self.tool_calls and self.state == AgentState.RUNNING: # This condition might need re-evaluation with tool_calls being on Manus
            self.state = AgentState.FINISHED
        elif self.state == AgentState.RUNNING: # Fallback for RUNNING state
            self.state = AgentState.FINISHED
        elif self.state == AgentState.ERROR:
            pass
            # State remains ERROR
        elif self.state == AgentState.FINISHED: # If already FINISHED by step logic
            pass
            # State remains FINISHED
        # Note: AgentState.IDLE, AgentState.INIT, AgentState.PAUSED (distinct from AWAITING_USER_FEEDBACK)
        # are not typically expected here if the main loop ran. If they occur, it's unusual.
        else:
            logger.error(f"Execution ended with an unexpected or unhandled state: {self.state.value} at step {self.current_step}. Review agent logic.") # Original log
            # Forcing a defined state like ERROR might be an option here if this case is problematic.
            # For now, it will retain the unexpected state.

        # Final log message reflecting the decided state.
        
        # Append a final status message to results for the return string.
        # This replaces the old run_result_message.
        final_summary = f"Execution concluded. Final state: {self.state.value}, Current step: {self.current_step}."
        results.append(final_summary)

        await SANDBOX_CLIENT.cleanup()
        return "\n".join(results) if results else "No steps executed or execution ended."

    @abstractmethod
    async def step(self) -> str:
        """Execute a single step in the agent's workflow.

        Must be implemented by subclasses to define specific behavior.
        """

    @abstractmethod
    async def should_request_feedback(self) -> bool:
        """Determines if the agent should pause and request user feedback.

        Must be implemented by subclasses to define specific feedback conditions.
        """

    def handle_stuck_state(self):
        """Handle stuck state by adding a prompt to change strategy"""
        stuck_prompt = "\
        Observed duplicate responses. Consider new strategies and avoid repeating ineffective paths already attempted."
        self.next_step_prompt = f"{stuck_prompt}\n{self.next_step_prompt}"

    def is_stuck(self) -> bool:
        """Check if the agent is stuck in a loop by detecting duplicate content"""
        if len(self.memory.messages) < 2:
            return False

        last_message = self.memory.messages[-1]
        if not last_message.content:
            return False

        # Count identical content occurrences
        duplicate_count = sum(
            1
            for msg in reversed(self.memory.messages[:-1])
            if msg.role == "assistant" and msg.content == last_message.content
        )

        return duplicate_count >= self.duplicate_threshold

    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value
