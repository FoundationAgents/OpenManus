from abc import ABC, abstractmethod
from typing import Optional

from pydantic import Field

from app.agent.base import BaseAgent
from app.event import AgentEvent, ReActAgentEvents
from app.llm import LLM
from app.schema import AgentState, Memory


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

    @abstractmethod
    async def think(self) -> bool:
        """Process current state and decide next action"""

    @abstractmethod
    async def act(self) -> str:
        """Execute decided actions"""

    async def step(self) -> str:
        """Execute a single step: think and act."""
        self.events.emit(ReActAgentEvents.STEP_START, {})
        self.events.emit(ReActAgentEvents.THINK_START, {})
        should_act = await self.think()
        self.events.emit(ReActAgentEvents.THINK_COMPLETE, {})

        if self.should_terminate:
            self.events.emit(ReActAgentEvents.STEP_COMPLETE, {})
            return "Terminated"

        total_input_tokens = self.llm.total_input_tokens
        total_completion_tokens = self.llm.total_completion_tokens
        input_tokens = total_input_tokens - self.pre_step_input_tokens
        completion_tokens = total_completion_tokens - self.pre_step_completion_tokens
        self.events.emit(
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

        if not should_act:
            self.events.emit(ReActAgentEvents.STEP_COMPLETE, {})
            return "Thinking complete - no action needed"
        self.events.emit(ReActAgentEvents.ACT_START, {})
        result = await self.act()
        self.events.emit(ReActAgentEvents.ACT_COMPLETE, {})

        total_input_tokens = self.llm.total_input_tokens
        total_completion_tokens = self.llm.total_completion_tokens
        input_tokens = total_input_tokens - self.pre_step_input_tokens
        completion_tokens = total_completion_tokens - self.pre_step_completion_tokens
        self.events.emit(
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

        self.events.emit(ReActAgentEvents.STEP_COMPLETE, {})
        if self.should_terminate:
            return "Terminated"

        return result
