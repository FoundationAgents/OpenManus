from types import SimpleNamespace

from app.agent.toolcall import ToolCallAgent


def test_response_content_prefers_regular_content():
    response = SimpleNamespace(
        content="regular content", reasoning_content="reasoning content"
    )

    assert ToolCallAgent._response_content(response) == "regular content"


def test_response_content_uses_reasoning_content_when_content_is_empty():
    response = SimpleNamespace(content="", reasoning_content="reasoning content")

    assert ToolCallAgent._response_content(response) == "reasoning content"


def test_response_content_uses_reasoning_content_when_content_is_whitespace():
    response = SimpleNamespace(content="\n\n", reasoning_content="reasoning content")

    assert ToolCallAgent._response_content(response) == "reasoning content"
