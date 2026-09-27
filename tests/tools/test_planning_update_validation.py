from copy import deepcopy
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
    from app.exceptions import ToolError
    from app.tool.planning import PlanningTool
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


@pytest.mark.asyncio
@pytest.mark.parametrize("steps", ["not a list", ["valid", 42], {"step": "invalid"}])
async def test_invalid_update_preserves_the_entire_plan(steps):
    tool = PlanningTool()
    await tool.execute(
        command="create", plan_id="plan", title="original", steps=["first", "second"]
    )
    await tool.execute(
        command="mark_step",
        step_index=0,
        step_status="completed",
        step_notes="already done",
    )
    before = deepcopy(tool.plans)

    with pytest.raises(ToolError, match="list of strings"):
        await tool.execute(
            command="update", plan_id="plan", title="changed", steps=steps
        )

    assert tool.plans == before
    assert "original" in (await tool.execute(command="get")).output


@pytest.mark.asyncio
async def test_valid_update_preserves_progress_of_unchanged_steps():
    tool = PlanningTool()
    await tool.execute(
        command="create", plan_id="plan", title="original", steps=["first", "second"]
    )
    await tool.execute(
        command="mark_step", step_index=0, step_status="completed", step_notes="done"
    )
    await tool.execute(
        command="update", plan_id="plan", title="changed", steps=["first", "new"]
    )
    assert tool.plans["plan"] == {
        "plan_id": "plan",
        "title": "changed",
        "steps": ["first", "new"],
        "step_statuses": ["completed", "not_started"],
        "step_notes": ["done", ""],
    }


@pytest.mark.asyncio
async def test_title_only_update_preserves_steps():
    tool = PlanningTool()
    await tool.execute(command="create", plan_id="plan", title="old", steps=["first"])
    await tool.execute(command="update", plan_id="plan", title="new")
    assert tool.plans["plan"]["title"] == "new"
    assert tool.plans["plan"]["steps"] == ["first"]
