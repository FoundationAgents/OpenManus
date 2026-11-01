"""State transitions do not require an LLM or sandbox connection."""

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from app.schema import AgentState


@pytest.fixture
def agent(monkeypatch):
    llm = ModuleType("app.llm")
    llm.LLM = type("LLM", (), {})
    logger = ModuleType("app.logger")
    logger.logger = MagicMock()
    sandbox = ModuleType("app.sandbox.client")
    sandbox.SANDBOX_CLIENT = MagicMock()
    with monkeypatch.context() as context:
        for dependency in (llm, logger, sandbox):
            context.setitem(sys.modules, dependency.__name__, dependency)
        source = Path(__file__).parents[2] / "app" / "agent" / "base.py"
        spec = importlib.util.spec_from_file_location("state_context_base", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    class StateAgent(module.BaseAgent):
        async def step(self):
            return "done"

    return StateAgent.model_construct(name="state-test", llm=None)


@pytest.mark.asyncio
async def test_failure_keeps_error_state_and_original_exception(agent):
    failure = RuntimeError("step failed")
    with pytest.raises(RuntimeError) as caught:
        async with agent.state_context(AgentState.RUNNING):
            assert agent.state == AgentState.RUNNING
            raise failure
    assert caught.value is failure
    assert agent.state == AgentState.ERROR


@pytest.mark.asyncio
async def test_success_restores_previous_state(agent):
    async with agent.state_context(AgentState.RUNNING):
        assert agent.state == AgentState.RUNNING
    assert agent.state == AgentState.IDLE


@pytest.mark.asyncio
async def test_successful_error_context_restores_previous_state(agent):
    async with agent.state_context(AgentState.ERROR):
        assert agent.state == AgentState.ERROR
    assert agent.state == AgentState.IDLE


@pytest.mark.asyncio
async def test_successful_body_state_change_restores_previous_state(agent):
    async with agent.state_context(AgentState.RUNNING):
        agent.state = AgentState.ERROR
    assert agent.state == AgentState.IDLE


@pytest.mark.asyncio
async def test_cancellation_restores_previous_state(agent):
    with pytest.raises(asyncio.CancelledError):
        async with agent.state_context(AgentState.RUNNING):
            raise asyncio.CancelledError
    assert agent.state == AgentState.IDLE


@pytest.mark.asyncio
async def test_invalid_state_does_not_change_agent(agent):
    with pytest.raises(ValueError, match="Invalid state"):
        async with agent.state_context("invalid"):
            pytest.fail("invalid context must not be entered")
    assert agent.state == AgentState.IDLE
