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
    ACT_START = "agent:act:start"
    ACT_COMPLETE = "agent:act:complete"
    ACT_ERROR = "agent:act:error"


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

    @abstractmethod
    @BaseAgent.event_wrapper(
        ReActAgentEvents.THINK_START,
        ReActAgentEvents.THINK_COMPLETE,
        ReActAgentEvents.THINK_ERROR,
    )
    async def think(self) -> bool:
        """Process current state and decide next action"""

    @abstractmethod
    @BaseAgent.event_wrapper(
        ReActAgentEvents.ACT_START,
        ReActAgentEvents.ACT_COMPLETE,
        ReActAgentEvents.ACT_ERROR,
    )
    async def act(self) -> str:
        """Execute decided actions"""

    @BaseAgent.event_wrapper(
        ReActAgentEvents.STEP_START,
        ReActAgentEvents.STEP_COMPLETE,
        ReActAgentEvents.STEP_ERROR,
    )
    async def step(self) -> str:
        """Execute a single step: think and act."""
        should_act = await self.think()
        if not should_act:
            return "Thinking complete - no action needed"
        result = await self.act()
        return result
