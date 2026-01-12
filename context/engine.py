from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import queue
import asyncio

from core.task import Task


class ContextEngine:
    """Builds prompt context from task state and recent events (no vector store)."""

    @classmethod
    def build(
        cls,
        task: Task,
        agent_role: Optional[str] = None,
        step_type: Optional[str] = None,
        budget: int = 4000,
    ) -> Dict[str, Any]:
        """Assemble context sections and enforce a simple character budget."""
        events = cls._snapshot_events(task)

        hard_facts = cls._collect_hard_facts(events)
        recent_events = cls._collect_recent(events)
        process_summary = cls._summarize(events, hard_facts)

        context = {
            "agent_role": agent_role,
            "step_type": step_type,
            "hard_facts": hard_facts,
            "recent_events": recent_events,
            "process_summary": process_summary,
        }

        return cls._enforce_budget(context, budget)

    @staticmethod
    def _snapshot_events(task: Task) -> List[Dict[str, Any]]:
        """Copy events without mutating the queue (supports asyncio.Queue and queue.Queue)."""
        q = task.event_queue
        items: List[Any] = []
        if isinstance(q, queue.Queue):
            try:
                items = list(q.queue)  # type: ignore[attr-defined]
            except Exception:
                items = []
        elif isinstance(q, asyncio.Queue):
            try:
                items = list(q._queue)  # type: ignore[attr-defined]
            except Exception:
                items = []
        return [e for e in items if isinstance(e, dict) and "type" in e]

    @staticmethod
    def _collect_hard_facts(events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract stable context: user goal and plan."""
        plan = None
        plan_steps: List[Any] = []
        user_goal = None

        for ev in events:
            etype = ev.get("type")
            data = ev.get("data", {})
            if etype == "plan.done":
                plan = data.get("plan") or plan
            elif etype == "plan.step":
                plan_steps.append(data.get("step"))
            elif etype == "thought" and not user_goal:
                # Heuristic: first thought often echoes the goal
                user_goal = data.get("content") or data

        if plan is None and plan_steps:
            plan = plan_steps

        return {"user_goal": user_goal, "plan": plan}

    @staticmethod
    def _collect_recent(events: List[Dict[str, Any]], limit: int = 5) -> List[Any]:
        """Collect recent tool-related events."""
        tool_events = [
            ev
            for ev in events
            if ev.get("type") in {"tool.call", "tool.result", "step_result", "execute.step.start"}
        ]
        return tool_events[-limit:]

    @staticmethod
    def _summarize(events: List[Dict[str, Any]], hard_facts: Dict[str, Any]) -> str:
        tool_calls = sum(1 for e in events if e.get("type") == "tool.call")
        tool_results = sum(1 for e in events if e.get("type") == "tool.result")
        steps = sum(1 for e in events if e.get("type") in {"plan.step", "execute.step.start"})
        plan_known = bool(hard_facts.get("plan"))
        return (
            f"Steps seen: {steps}; tool calls: {tool_calls}; tool results: {tool_results}; "
            f"plan_available: {plan_known}"
        )

    @staticmethod
    def _enforce_budget(context: Dict[str, Any], budget: int) -> Dict[str, Any]:
        """Trim context to fit a simple character budget."""
        text = json.dumps(context, ensure_ascii=False)
        if len(text) <= budget:
            return context

        # Trim recent events first, then hard facts strings
        recent = context.get("recent_events") or []
        while recent and len(json.dumps(context, ensure_ascii=False)) > budget:
            recent.pop(0)
        context["recent_events"] = recent

        def _truncate_str(value: Any, max_len: int) -> Any:
            if isinstance(value, str) and len(value) > max_len:
                return value[-max_len:]
            return value

        context["process_summary"] = _truncate_str(context.get("process_summary"), 300)
        hard = context.get("hard_facts") or {}
        if isinstance(hard, dict):
            hard["user_goal"] = _truncate_str(hard.get("user_goal"), 500)
        context["hard_facts"] = hard
        return context


__all__ = ["ContextEngine"]
