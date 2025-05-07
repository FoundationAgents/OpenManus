import importlib

import pytest

from app.agent import (
    BaseAgent,
    BrowserAgent,
    MCPAgent,
    PlanningAgent,
    ReActAgent,
    SWEAgent,
    ToolCallAgent,
)


def test_base_agent_init():
    with pytest.raises(TypeError):  # it's an abstract class
        BaseAgent()


def test_browser_agent_init():
    agent = BrowserAgent()
    assert isinstance(agent, BrowserAgent)


def test_mcp_agent_init():
    agent = MCPAgent()
    assert isinstance(agent, MCPAgent)


def test_planning_agent_init():
    agent = PlanningAgent()
    assert isinstance(agent, PlanningAgent)


def test_react_agent_init():
    with pytest.raises(TypeError):  # it's an abstract class
        ReActAgent()


def test_swe_agent_init():
    agent = SWEAgent()
    assert isinstance(agent, SWEAgent)


def test_toolcall_agent_init():
    agent = ToolCallAgent()
    assert isinstance(agent, ToolCallAgent)


def test_all_imports():
    agents = [
        BaseAgent,
        BrowserAgent,
        MCPAgent,
        PlanningAgent,
        ReActAgent,
        SWEAgent,
        ToolCallAgent,
    ]
    for agent in agents:
        assert agent.__name__ in importlib.import_module("app.agent").__all__


def test_browser_agent_with_invalid_method_call():
    with pytest.raises(AttributeError):
        agent = BrowserAgent()
        agent.invalid_method()


def test_planning_agent_with_invalid_method_call():
    with pytest.raises(AttributeError):
        agent = PlanningAgent()
        agent.invalid_method()


def test_swe_agent_with_invalid_method_call():
    with pytest.raises(AttributeError):
        agent = SWEAgent()
        agent.invalid_method()
