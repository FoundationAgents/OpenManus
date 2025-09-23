from abc import ABC, abstractmethod
from typing import Optional

from pydantic import Field

from app.agent.base import BaseAgent
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

    @abstractmethod
    async def think(self) -> bool:
        """Process current state and decide next action"""

    @abstractmethod
    async def act(self) -> str:
        """Execute decided actions"""

    async def step(self) -> str:
        """Execute a single step: think and act."""
        should_act = await self.think()
        
        # Check for interrupt after thinking but before acting
        if hasattr(self, 'interrupt_requested') and self.interrupt_requested:
            from app.logger import logger
            from app.schema import Message
            logger.info("Interrupt detected after thinking - will process additional request in next step")
            
            # Add dummy tool responses for any pending tool calls to satisfy OpenAI API
            if hasattr(self, 'tool_calls') and self.tool_calls:
                for tool_call in self.tool_calls:
                    self.memory.add_message(
                        Message.tool_message(
                            content="[処理中断 - 追加要求により統合処理へ移行]",
                            name=tool_call.function.name,
                            tool_call_id=tool_call.id
                        )
                    )
                logger.info(f"Added dummy responses for {len(self.tool_calls)} tool calls")
            
            # Add the interrupt message as additional request
            self.update_memory("user", f"[追加要求] {self.interrupt_message}")
            self.interrupt_message = None
            self.interrupt_requested = False
            # Skip act and process in next step
            return "Additional request received - processing in next step"
        
        if not should_act:
            return "Thinking complete - no action needed"
        return await self.act()
