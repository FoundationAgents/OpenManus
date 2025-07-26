import pytest

from app.agent.checklist_manager import ChecklistManager
from app.tool.checklist_tools import (
    AddChecklistTaskTool,
    UpdateChecklistTaskTool,
    ViewChecklistTool,
)


@pytest.mark.asyncio
async def test_add_and_view_task_with_agent(tmp_path):
    from app import config as app_config

    app_config.WORKSPACE_ROOT = tmp_path
    manager = ChecklistManager()
    add_tool = AddChecklistTaskTool()
    await add_tool.execute(task_description="Task A", assigned_agent="Agent1")
    await manager._load_checklist()
    tasks = manager.get_tasks()
    assert tasks == [{"description": "Task A", "status": "Pendente", "agent": "Agent1"}]
    view_tool = ViewChecklistTool()
    result = await view_tool.execute()
    assert "Agent1" in result.output


@pytest.mark.asyncio
async def test_update_task_agent(tmp_path):
    from app import config as app_config

    app_config.WORKSPACE_ROOT = tmp_path
    manager = ChecklistManager()
    add_tool = AddChecklistTaskTool()
    await add_tool.execute(task_description="Task B", assigned_agent="Agent1")
    updater = UpdateChecklistTaskTool()
    await updater.execute(
        task_description="Task B", new_status="Em Andamento", new_agent="Agent2"
    )
    await manager._load_checklist()
    task = manager.get_task_by_description("Task B")
    assert task["status"] == "Em andamento"
    assert task["agent"] == "Agent2"
