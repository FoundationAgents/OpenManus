"""ReActAgent — Think → Act → Observe loop with explicit structured trace events.

Every step emits three lifecycle events so the UI and logs have a complete,
structured trace of the agent's reasoning:

  agent:lifecycle:step:reason   — the LLM's textual reasoning (thought)
  agent:lifecycle:step:act      — what tools were decided and dispatched
  agent:lifecycle:step:observe  — summary of the tool results (observation)

These map directly to the classic ReAct paper's Reason / Act / Observe cycle.
"""
from abc import ABC, abstractmethod
from typing import Optional

from pydantic import Field

from app.agent.base import BaseAgent, Task, TaskInterrupted
from app.config import config
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

    max_steps: int = config.agent.max_steps
    current_step: int = 0

    @abstractmethod
    async def think(self, task: Task) -> bool:
        """Process current state and decide next action.

        Must call ``task.emit('agent:lifecycle:step:reason', {...})`` with the
        LLM's reasoning text before returning.
        """

    @abstractmethod
    async def act(self, task: Task) -> str:
        """Execute decided actions.

        Must call ``task.emit('agent:lifecycle:step:observe', {...})`` with a
        summary of tool results before returning.
        """

    async def step(self, task: Task) -> str:
        """Execute a single step: Reason → Act → Observe.

        Emits structured lifecycle events for the full ReAct trace:
        - step:start       already emitted by BaseAgent.run()
        - step:reason      emitted inside think() when the LLM responds
        - step:act         emitted here before dispatching act()
        - step:observe     emitted inside act() after tools complete
        - step:complete    emitted here with the step summary
        """
        if task.is_interrupted():
            raise TaskInterrupted()

        # ── Reason ────────────────────────────────────────────────────────
        should_act = await self.think(task)

        if task.is_interrupted():
            raise TaskInterrupted()

        if not should_act:
            task.emit(
                "agent:lifecycle:step:complete",
                {
                    "step": self.current_step,
                    "outcome": "no_action",
                    "summary": "Thinking complete — no tool action required.",
                },
            )
            return "Thinking complete - no action needed"

        # ── Act ───────────────────────────────────────────────────────────
        task.emit(
            "agent:lifecycle:step:act",
            {
                "step": self.current_step,
                "agent": self.name,
            },
        )
        observation = await self.act(task)

        # ── Observe ───────────────────────────────────────────────────────
        task.emit(
            "agent:lifecycle:step:complete",
            {
                "step": self.current_step,
                "outcome": "acted",
                "summary": observation[:400] if observation else "",
            },
        )
        return observation
