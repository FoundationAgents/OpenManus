"""Regression tests for plan creation in PlanningFlow."""

import json
from pathlib import Path

import pytest


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.flow.planning import PlanningFlow
    from app.schema import AgentState, Function, ToolCall
    from app.tool.planning import PlanningTool
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


class FakeLLM:
    """Returns a scripted model answer."""

    def __init__(self, tool_calls=()):
        self.tool_calls_response = list(tool_calls)

    async def ask_tool(self, *args, **kwargs):
        class Response:
            pass

        response = Response()
        response.tool_calls = self.tool_calls_response
        response.content = ""
        return response

    async def ask(self, *args, **kwargs):
        return "summary"


class StubAgent:
    """Executor that finishes every step immediately."""

    description = "stub executor"

    def __init__(self):
        self.state = AgentState.IDLE

    async def run(self, prompt=None):
        return "step finished"


def _planning_call(arguments: dict) -> ToolCall:
    return ToolCall(
        id="call_1",
        function=Function(name="planning", arguments=json.dumps(arguments)),
    )


def _flow(tool_calls) -> PlanningFlow:
    return PlanningFlow.model_construct(
        agents={"stub": StubAgent()},
        tools=None,
        primary_agent_key="stub",
        executor_keys=["stub"],
        active_plan_id="plan_test",
        current_step_index=None,
        planning_tool=PlanningTool(),
        llm=FakeLLM(tool_calls),
    )


@pytest.mark.asyncio
async def test_plan_without_title_keeps_the_model_steps():
    """A `create` call without `title` must not abort the whole flow."""
    flow = _flow(
        [
            _planning_call(
                {"command": "create", "steps": ["Analyse sales data", "Write report"]}
            )
        ]
    )

    result = await flow.execute("Build a sales report")

    assert "Execution failed" not in result
    assert flow.planning_tool.plans["plan_test"]["steps"] == [
        "Analyse sales data",
        "Write report",
    ]
    assert "Plan completed" in result


@pytest.mark.asyncio
async def test_unusable_plan_falls_back_to_the_default_plan():
    """A rejected plan must fall back to the default plan, not end the run."""
    flow = _flow([_planning_call({"command": "create", "title": "Broken plan"})])

    result = await flow.execute("Build a sales report")

    assert "Execution failed" not in result
    assert flow.planning_tool.plans["plan_test"]["steps"] == [
        "Analyze request",
        "Execute task",
        "Verify results",
    ]
    assert "Plan completed" in result
