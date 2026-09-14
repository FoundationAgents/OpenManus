"""Regression tests for per-request isolation of step counter and memory.

See issue #544: running several requests with the same agent instance kept
counting steps from the previous request and answered the new request with the
previous request's messages still in memory.
"""

from pathlib import Path
from typing import List

import pytest
from pydantic import Field


_CONFIG_PATH = Path(__file__).parents[2] / "config" / "config.toml"
_CREATED_TEST_CONFIG = not _CONFIG_PATH.exists()
if _CREATED_TEST_CONFIG:
    _CONFIG_PATH.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n'
    )

try:
    from app.agent.base import BaseAgent
    from app.agent.toolcall import ToolCallAgent
    from app.flow.planning import PlanningFlow
    from app.schema import AgentState, Function, Message, ToolCall
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


class RecordingAgent(BaseAgent):
    """Agent that records the step numbers it saw and then finishes."""

    name: str = "recording"
    next_step_prompt: str = "original next step prompt"
    max_steps: int = 5
    steps_per_run: int = 2
    seen_steps: List[int] = Field(default_factory=list)

    async def step(self) -> str:
        self.seen_steps.append(self.current_step)
        self.update_memory("assistant", f"answer for step {self.current_step}")
        if self.current_step >= self.steps_per_run:
            self.state = AgentState.FINISHED
        return f"result {self.current_step}"


class NeverFinishingAgent(BaseAgent):
    """Agent that keeps working until max_steps is reached."""

    name: str = "never_finishing"
    max_steps: int = 3

    async def step(self) -> str:
        return f"result {self.current_step}"


class StubToolCallAgent(ToolCallAgent):
    """ToolCallAgent that never talks to an LLM."""

    name: str = "stub_toolcall"

    async def think(self) -> bool:
        self.state = AgentState.FINISHED
        return False


@pytest.mark.asyncio
async def test_step_counter_restarts_for_each_request():
    agent = RecordingAgent()

    first = await agent.run("first request")
    second = await agent.run("second request")

    assert agent.seen_steps == [1, 2, 1, 2]
    assert first.startswith("Step 1:")
    assert second.startswith("Step 1:")
    assert "Step 3:" not in second


@pytest.mark.asyncio
async def test_memory_is_cleared_between_requests():
    agent = RecordingAgent()

    await agent.run("first request")
    await agent.run("second request")

    contents = [msg.content for msg in agent.memory.messages]
    assert "first request" not in contents
    assert "second request" in contents
    # Only the new request plus the answers produced while serving it.
    assert len(agent.memory.messages) == 3


@pytest.mark.asyncio
async def test_system_messages_survive_the_reset():
    agent = RecordingAgent()
    agent.memory.add_message(Message.system_message("MCP server instructions"))

    await agent.run("first request")
    await agent.run("second request")

    system_messages = [msg for msg in agent.memory.messages if msg.role == "system"]
    assert [msg.content for msg in system_messages] == ["MCP server instructions"]


@pytest.mark.asyncio
async def test_system_messages_can_be_dropped_too():
    agent = RecordingAgent(keep_system_messages_on_reset=False)
    agent.memory.add_message(Message.system_message("MCP server instructions"))

    await agent.run("first request")

    assert not [msg for msg in agent.memory.messages if msg.role == "system"]


@pytest.mark.asyncio
async def test_memory_can_be_kept_across_runs_on_demand():
    agent = RecordingAgent(reset_memory_on_run=False)

    await agent.run("first request")
    await agent.run("second request")

    contents = [msg.content for msg in agent.memory.messages]
    assert "first request" in contents
    assert "second request" in contents
    # The step counter still restarts even when memory is preserved.
    assert agent.seen_steps == [1, 2, 1, 2]


@pytest.mark.asyncio
async def test_stuck_state_prompt_is_not_inherited_by_the_next_request():
    agent = RecordingAgent()
    original_prompt = agent.next_step_prompt

    agent.handle_stuck_state()
    assert agent.next_step_prompt != original_prompt

    await agent.run("next request")

    assert agent.next_step_prompt == original_prompt


@pytest.mark.asyncio
async def test_max_steps_run_reports_its_step_count_and_restarts():
    agent = NeverFinishingAgent()

    result = await agent.run("first request")

    assert f"Terminated: Reached max steps ({agent.max_steps})" in result
    assert agent.current_step == agent.max_steps
    assert agent.state == AgentState.IDLE

    second = await agent.run("second request")

    assert second.startswith("Step 1:")


@pytest.mark.asyncio
async def test_toolcall_agent_reset_clears_pending_tool_calls():
    agent = StubToolCallAgent()
    agent.tool_calls = [
        ToolCall(id="1", function=Function(name="terminate", arguments="{}"))
    ]
    agent._current_base64_image = "stale-image"

    await agent.run("new request")

    assert agent.tool_calls == []
    assert agent._current_base64_image is None


@pytest.mark.asyncio
async def test_planning_flow_keeps_executor_memory_across_plan_steps(monkeypatch):
    executor = RecordingAgent()
    flow = PlanningFlow(agents={"default": executor})

    async def fake_plan_text() -> str:
        return "plan status"

    async def fake_mark_step_completed() -> None:
        return None

    monkeypatch.setattr(flow, "_get_plan_text", fake_plan_text)
    monkeypatch.setattr(flow, "_mark_step_completed", fake_mark_step_completed)

    flow.current_step_index = 0
    await flow._execute_step(executor, {"text": "first plan step"})
    flow.current_step_index = 1
    await flow._execute_step(executor, {"text": "second plan step"})

    contents = " ".join(msg.content or "" for msg in executor.memory.messages)
    assert "first plan step" in contents
    assert "second plan step" in contents
    # The flow restores the agent's own setting once the step is done.
    assert executor.reset_memory_on_run is True
