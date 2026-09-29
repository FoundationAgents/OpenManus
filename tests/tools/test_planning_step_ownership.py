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
    from app.tool.planning import PlanningTool
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["create", "update"])
async def test_plan_owns_step_list_after_command(command):
    tool = PlanningTool()
    if command == "update":
        await tool.execute(command="create", plan_id="p", title="Plan", steps=["first"])
        await tool.execute(command="mark_step", step_index=0, step_status="completed")
    steps = ["first", "second"]
    await tool.execute(command=command, plan_id="p", title="Plan", steps=steps)

    steps.clear()

    plan = tool.plans["p"]
    assert plan["steps"] == ["first", "second"]
    assert len(plan["steps"]) == len(plan["step_statuses"]) == len(plan["step_notes"])
    await tool.execute(command="mark_step", step_index=1, step_status="completed")
    if command == "update":
        assert plan["step_statuses"][0] == "completed"


@pytest.mark.asyncio
async def test_reusing_input_list_does_not_link_two_plans():
    tool = PlanningTool()
    steps = ["first"]
    for plan_id in ["a", "b"]:
        await tool.execute(
            command="create", plan_id=plan_id, title=plan_id, steps=steps
        )
    tool.plans["a"]["steps"][0] = "changed"
    assert tool.plans["b"]["steps"] == ["first"]
    assert steps == ["first"]
