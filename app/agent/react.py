from abc import ABC, abstractmethod
from typing import Optional

from pydantic import Field

from app.agent.base import BaseAgent, BaseAgentEvents
from app.llm import LLM
from app.schema import AgentState, Memory


class ReActAgentEvents(BaseAgentEvents):
    THINK_START = "agent:think:start"
    THINK_COMPLETE = "agent:think:complete"
    THINK_ERROR = "agent:think:error"
    THINK_TOKEN_COUNT = "agent:think:token:count"
    ACT_START = "agent:act:start"
    ACT_COMPLETE = "agent:act:complete"
    ACT_ERROR = "agent:act:error"
    ACT_TOKEN_COUNT = "agent:act:token:count"


class ReActAgent(BaseAgent, ABC):
    name: str
    description: Optional[str] = None

    system_prompt: Optional[str] = None
    next_step_prompt: Optional[str] = None

    llm: Optional[LLM] = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE

    max_steps: int = 10
    current_step: int = 0

    pre_step_input_tokens: int = 0
    pre_step_completion_tokens: int = 0

    async def think(self) -> bool:
        """Process current state and decide next action"""

    async def act(self) -> str:
        """Execute decided actions"""

    @BaseAgent.event_wrapper(
        ReActAgentEvents.STEP_START,
        ReActAgentEvents.STEP_COMPLETE,
        ReActAgentEvents.STEP_ERROR,
    )
    async def step(self) -> str:
        """Execute a single step: think and act."""
        self.emit(ReActAgentEvents.THINK_START, {})
        should_act = await self.think()
        total_input_tokens = self.llm.total_input_tokens
        total_completion_tokens = self.llm.total_completion_tokens
        input_tokens = total_input_tokens - self.pre_step_input_tokens
        completion_tokens = total_completion_tokens - self.pre_step_completion_tokens
        self.emit(
            ReActAgentEvents.THINK_TOKEN_COUNT,
            {
                "input": input_tokens,
                "completion": completion_tokens,
                "total_input": total_input_tokens,
                "total_completion": total_completion_tokens,
            },
        )
        self.pre_step_input_tokens = total_input_tokens
        self.pre_step_completion_tokens = total_completion_tokens
        self.emit(ReActAgentEvents.THINK_COMPLETE, {})
        if not should_act and not self.should_terminate:
            return "Thinking complete - no action needed"
        self.emit(ReActAgentEvents.ACT_START, {})
        result = await self.act()

        total_input_tokens = self.llm.total_input_tokens
        total_completion_tokens = self.llm.total_completion_tokens
        input_tokens = total_input_tokens - self.pre_step_input_tokens
        completion_tokens = total_completion_tokens - self.pre_step_completion_tokens
        self.emit(
            ReActAgentEvents.ACT_TOKEN_COUNT,
            {
                "input": input_tokens,
                "completion": completion_tokens,
                "total_input": total_input_tokens,
                "total_completion": total_completion_tokens,
            },
        )
        self.pre_step_input_tokens = total_input_tokens
        self.pre_step_completion_tokens = total_completion_tokens
        self.emit(ReActAgentEvents.ACT_COMPLETE, {})
        return result
