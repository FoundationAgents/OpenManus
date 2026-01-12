import json
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.agent.base import BaseAgent, Task, TaskInterrupted
from app.prompt.planning import PLANNING_SYSTEM_PROMPT
from app.schema import Message
from context.engine import ContextEngine


class PlannerAgent(BaseAgent):
    """Lightweight planner that produces a structured plan without executing tools."""

    name: str = "planner"
    description: str = (
        "Generates structured plans (list[dict]) and emits plan events via task."
    )

    system_prompt: str = PLANNING_SYSTEM_PROMPT
    next_step_prompt: Optional[str] = None

    max_steps: int = 1
    current_step: int = 0

    plan_fields: List[str] = Field(
        default_factory=lambda: ["id", "title", "action", "expected_result"]
    )

    async def run(self, task: Task, input: Any) -> List[Dict[str, Any]]:
        if task.is_interrupted():
            raise TaskInterrupted()

        request = "" if input is None else str(input).strip()
        plan = await self._generate_plan(task, request)

        for idx, step in enumerate(plan):
            task.emit("plan.step", {"index": idx, "step": step})

        task.emit("plan.done", {"steps": len(plan), "plan": plan})
        return plan

    async def _generate_plan(self, task: Task, request: str) -> List[Dict[str, Any]]:
        """Use the existing LLM to create a structured plan without calling tools."""
        if task.is_interrupted():
            raise TaskInterrupted()

        if not request:
            default_plan = [
                {
                    "id": "step-1",
                    "title": "No request provided",
                    "action": "Await valid task input",
                    "expected_result": "Receive task details to plan",
                }
            ]
            return default_plan

        user_prompt = (
            "Create a concise, actionable plan as a JSON array. "
            "Each item must be an object with keys: "
            f"{', '.join(self.plan_fields)}. "
            "Keep 3-7 steps, ordered, no prose outside JSON."
            f"\n\nTask: {request}"
        )

        context = ContextEngine.build(task, agent_role=self.name, step_type="plan")
        ctx_msg = Message.system_message(json.dumps(context, ensure_ascii=False))

        response = await self.llm.ask(
            messages=[Message.user_message(user_prompt)],
            system_msgs=[Message.system_message(self.system_prompt), ctx_msg],
        )

        plan = self._parse_plan(response)
        if not plan:
            plan = [
                {
                    "id": "step-1",
                    "title": "Analyze task",
                    "action": f"Understand requirements: {request}",
                    "expected_result": "Clear scope and constraints",
                },
                {
                    "id": "step-2",
                    "title": "Execute task",
                    "action": "Perform required actions to complete the task",
                    "expected_result": "Task objectives met",
                },
                {
                    "id": "step-3",
                    "title": "Verify results",
                    "action": "Validate outputs and summarize findings",
                    "expected_result": "Confirmed completion with summary",
                },
            ]
        return plan

    def _parse_plan(self, text: str) -> List[Dict[str, Any]]:
        """Parse JSON plan and normalize fields."""
        if not text:
            return []
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []

        if not isinstance(data, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            step = {field: item.get(field) for field in self.plan_fields}
            # Fallback IDs if missing
            if not step.get("id"):
                step["id"] = f"step-{i+1}"
            if not step.get("title") and step.get("action"):
                step["title"] = step["action"]
            normalized.append(step)
        return normalized

    async def step(self, task: Task) -> str:  # pragma: no cover - run overrides loop
        raise NotImplementedError("PlannerAgent does not use step-based execution")
