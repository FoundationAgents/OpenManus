import pytest

# Importing app.tool pulls in the project configuration, which may be absent in a
# bare checkout; skip instead of failing on an environment problem.
try:
    from app.tool.base import CLIResult, ToolFailure, ToolResult
except Exception as exc:  # pragma: no cover - environment without a config file
    pytest.skip(f"project configuration unavailable: {exc}", allow_module_level=True)


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (ToolResult(output="done"), "done"),
        (ToolResult(output={"count": 5}), "{'count': 5}"),
        (ToolResult(output=[1, 2]), "[1, 2]"),
        (ToolResult(output=7), "7"),
        (ToolResult(), ""),
        (ToolFailure(error="boom"), "Error: boom"),
        (CLIResult(output="line"), "line"),
    ],
)
def test_tool_result_renders_as_text(result, expected):
    assert str(result) == expected


def test_tool_result_supports_f_strings():
    assert f"result: {ToolResult(output={'ok': True})}" == "result: {'ok': True}"
