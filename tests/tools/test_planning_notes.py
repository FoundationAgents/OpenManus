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
    from app.tool import PlanningTool
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


@pytest.mark.asyncio
@pytest.mark.parametrize("clear_notes", [False, True])
async def test_mark_step_clears_explicit_empty_notes_but_preserves_omitted_notes(
    clear_notes,
):
    tool = PlanningTool()
    await tool.execute(command="create", plan_id="task", title="Task", steps=["Deploy"])
    await tool.execute(
        command="mark_step",
        plan_id="task",
        step_index=0,
        step_status="blocked",
        step_notes="Waiting for approval",
    )

    arguments = {"step_notes": ""} if clear_notes else {}
    await tool.execute(
        command="mark_step",
        plan_id="task",
        step_index=0,
        step_status="completed",
        **arguments,
    )
    result = await tool.execute(command="get", plan_id="task")

    assert "1/1 steps completed" in result.output
    if clear_notes:
        assert "Waiting for approval" not in result.output
        assert tool.plans["task"]["step_notes"] == [""]
    else:
        assert "Waiting for approval" in result.output
        assert tool.plans["task"]["step_notes"] == ["Waiting for approval"]
