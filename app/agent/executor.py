import json
from typing import Any, Dict, List, Optional, Union

from app.agent.toolcall import ToolCallAgent
from app.agent.base import Task, TaskInterrupted


class ExecutorAgent(ToolCallAgent):
    """Executor that consumes a planner-produced plan and runs its steps with tools."""

    name: str = "executor"
    description: str = "Executes structured plan steps and emits execution events."

    async def run(self, task: Task, plan: Any) -> str:
        if task.is_interrupted():
            raise TaskInterrupted()

        steps = self._normalize_plan(plan)
        results: List[str] = []

        for idx, step in enumerate(steps):
            if task.is_interrupted():
                raise TaskInterrupted()

            task.emit("execute.step.start", {"index": idx, "step": step})
            step_prompt = self._format_step_prompt(step, idx)
            result = await super().run(task, step_prompt)
            results.append(result)

        return "\n".join(results)

    def _normalize_plan(self, plan: Any) -> List[Dict[str, Any]]:
        """Accept list/dict/str plan and normalize to list of dict steps."""
        if isinstance(plan, list):
            return [self._ensure_dict(step, i) for i, step in enumerate(plan)]
        if isinstance(plan, dict):
            return [self._ensure_dict(plan, 0)]
        if isinstance(plan, str):
            try:
                data = json.loads(plan)
                if isinstance(data, list):
                    return [self._ensure_dict(s, i) for i, s in enumerate(data)]
                if isinstance(data, dict):
                    return [self._ensure_dict(data, 0)]
            except json.JSONDecodeError:
                pass
        # fallback single step
        return [
            {
                "id": "step-1",
                "title": "Execute task",
                "action": str(plan),
                "expected_result": "Task completed",
            }
        ]

    def _ensure_dict(self, step: Any, idx: int) -> Dict[str, Any]:
        if isinstance(step, dict):
            if "id" not in step:
                step = {**step, "id": step.get("title") or f"step-{idx+1}"}
            return step
        return {
            "id": f"step-{idx+1}",
            "title": "Execute step",
            "action": str(step),
            "expected_result": "",
        }

    def _format_step_prompt(self, step: Dict[str, Any], idx: int) -> str:
        title = step.get("title") or f"Step {idx+1}"
        action = step.get("action") or ""
        expected = step.get("expected_result") or ""
        return (
            f"Step {idx+1}: {title}\n"
            f"Action: {action}\n"
            f"Expected Result: {expected}\n"
            "Execute this step using available tools. Return a concise result."
        )

    async def execute_tool(self, command, task: Task) -> str:  # type: ignore[override]
        if task.is_interrupted():
            raise TaskInterrupted()

        name = getattr(getattr(command, "function", None), "name", None)
        raw_args = getattr(getattr(command, "function", None), "arguments", None)
        parsed_args: Union[dict, str, None]
        try:
            parsed_args = json.loads(raw_args or "{}")
        except Exception:
            parsed_args = raw_args

        if name:
            task.emit("tool.call", {"tool": name, "args": parsed_args})

        result = await super().execute_tool(command, task)

        task.emit("tool.result", {"tool": name, "result": result})
        return result


__all__ = ["ExecutorAgent"]
