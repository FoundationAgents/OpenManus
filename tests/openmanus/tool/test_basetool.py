from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.tool.base import BaseTool, CLIResult, ToolFailure, ToolResult


class MockTool(BaseTool):
    async def execute(self, **kwargs) -> Any:
        return "MockTool executed"


def test_basetool_to_param():
    tool = MockTool(name="test_tool", description="This is a test tool")
    expected = {
        "type": "function",
        "function": {
            "name": "test_tool",
            "description": "This is a test tool",
            "parameters": None,
        },
    }
    assert tool.to_param() == expected


def test_toolresult_bool():
    result = ToolResult(output="test_output")
    assert bool(result) is True

    result = ToolResult()
    assert bool(result) is False


def test_toolresult_add_output():
    result1 = ToolResult(output="output1")
    result2 = ToolResult(output="output2")
    combined_result = result1 + result2
    assert combined_result.output == "output1output2"


def test_toolresult_add_mixed():
    result1 = ToolResult(output="output1", error="error1")
    result2 = ToolResult(output="output2")
    combined_result = result1 + result2
    assert combined_result.output == "output1output2"
    assert combined_result.error == "error1"


def test_toolresult_add_base64_image():
    result1 = ToolResult(base64_image="image1")
    result2 = ToolResult(base64_image="image2")
    with pytest.raises(ValueError):
        _ = result1 + result2


def test_toolresult_str():
    result = ToolResult(output="test_output")
    assert str(result) == "test_output"

    result = ToolResult(error="test_error")
    assert str(result) == "Error: test_error"


def test_toolresult_replace():
    result = ToolResult(output="test_output", error="test_error")
    new_result = result.replace(output="new_output")
    assert new_result.output == "new_output"
    assert new_result.error == "test_error"


def test_cliresult_inheritance():
    cli_result = CLIResult(output="cli_output")
    assert cli_result.output == "cli_output"


def test_toolfailure_inheritance():
    tool_failure = ToolFailure(error="tool_error")
    assert tool_failure.error == "tool_error"


@pytest.mark.asyncio
async def test_tool_call(mocker):
    a = mocker.patch.object(
        MockTool, "execute", AsyncMock(return_value="MockTool executed")
    )
    tool = MockTool(name="test_tool", description="This is a test tool")
    result = await tool(param1="value1", param2="value2")
    assert result == "MockTool executed"
    a.assert_called_once_with(param1="value1", param2="value2")
