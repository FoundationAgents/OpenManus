"""Stuck detection must work while the agent keeps calling tools."""

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
    from app.agent.base import BaseAgent
    from app.schema import Memory, Message
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


class _ProbeAgent(BaseAgent):
    """Minimal agent: stuck detection does not need a model or a tool call."""

    name: str = "stuck-probe"

    async def step(self) -> str:
        return "step"


def _agent(messages):
    return _ProbeAgent(memory=Memory(messages=messages))


def _tool_result(text="Observed output of cmd `bash` executed:\nfile.txt"):
    return Message.tool_message(content=text, name="bash", tool_call_id="call_1")


def test_repeated_reply_is_stuck_between_tool_results():
    """The tool-calling loop always ends a step with a tool message."""
    messages = []
    for _ in range(3):
        messages.append(Message.assistant_message("I will list the files."))
        messages.append(_tool_result())

    assert messages[-1].role == "tool"
    assert _agent(messages).is_stuck() is True


def test_distinct_replies_are_not_stuck():
    messages = [Message.assistant_message("Listing files."), _tool_result()]
    messages += [Message.assistant_message("Reading the file."), _tool_result()]

    assert _agent(messages).is_stuck() is False


def test_duplicate_below_threshold_is_not_stuck():
    messages = [Message.assistant_message("Same plan."), _tool_result()]
    messages += [Message.assistant_message("Same plan."), _tool_result()]

    agent = _agent(messages)

    assert agent.duplicate_threshold == 2
    assert agent.is_stuck() is False


def test_empty_reply_never_marks_the_agent_stuck():
    messages = []
    for _ in range(3):
        messages.append(Message.from_tool_calls(content="", tool_calls=[]))
        messages.append(_tool_result())

    assert _agent(messages).is_stuck() is False


def test_repeated_reply_without_tools_is_still_stuck():
    messages = [
        Message.assistant_message("Nothing to do."),
        Message.assistant_message("Nothing to do."),
        Message.assistant_message("Nothing to do."),
    ]

    assert _agent(messages).is_stuck() is True


def test_single_message_memory_is_not_stuck():
    assert _agent([Message.assistant_message("hi")]).is_stuck() is False
    assert _agent([]).is_stuck() is False


@pytest.mark.asyncio
async def test_stuck_state_adds_a_strategy_hint():
    messages = []
    for _ in range(3):
        messages.append(Message.assistant_message("I will list the files."))
        messages.append(_tool_result())
    agent = _agent(messages)

    assert agent.is_stuck() is True
    agent.handle_stuck_state()
    assert "consider new strategies" in agent.next_step_prompt.lower()
