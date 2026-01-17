import tempfile

import pytest
import pytest_asyncio

from app.config import config
from app.sandbox.core.sandbox import DockerSandbox, SandboxSettings
from app.tool.file_operators import LocalFileOperator, SandboxFileOperator
from app.tool.str_replace_editor import StrReplaceEditor


@pytest_asyncio.fixture(scope="module")
async def sandbox_instance():
    """Creates a single sandbox instance for all sandbox tests."""
    sandbox = DockerSandbox(
        SandboxSettings(
            image="python:3.12-slim",
            work_dir="/workspace",
            memory_limit="1g",
            cpu_limit=0.5,
            network_enabled=True,
        )
    )
    await sandbox.create()
    try:
        yield sandbox
    finally:
        await sandbox.cleanup()


@pytest.fixture
def workspace_path():
    if config.sandbox.use_sandbox:
        return lambda name: f"/workspace/{name}"
    else:
        tmpdir = tempfile.gettempdir()
        return lambda name: f"{tmpdir}/{name}"


@pytest_asyncio.fixture(params=["local", "sandbox"])
async def editor(request, sandbox_instance) -> StrReplaceEditor:
    """Returns a configured StrReplaceEditor for both local and sandbox environments."""
    config.sandbox.use_sandbox = request.param == "sandbox"
    editor = StrReplaceEditor()

    if request.param == "sandbox":
        # Replace internal sandbox operator with one that uses the shared instance
        op = SandboxFileOperator()
        op.sandbox_client.sandbox = sandbox_instance
        editor._sandbox_operator = op

    return editor


@pytest.mark.asyncio
async def test_str_replace_editor_lifecycle(editor: StrReplaceEditor, workspace_path):
    """Full lifecycle test for StrReplaceEditor: create, insert, replace, undo, rename, delete."""
    base = workspace_path("editor_test.txt")
    renamed = workspace_path("renamed_editor_test.txt")

    # Create a file
    content = "Hello\nWorld\nEnd"
    result = await editor.execute(command="create", path=base, file_text=content)
    assert "File created successfully" in result

    # Insert a new line
    result = await editor.execute(
        command="insert", path=base, insert_line=1, new_str="Inserted Line"
    )
    assert "The file" in result

    # Replace a string
    result = await editor.execute(
        command="str_replace", path=base, old_str="World", new_str="🌍"
    )
    assert "has been edited" in result

    # Undo the replacement
    result = await editor.execute(command="undo_edit", path=base)
    assert "undone successfully" in result

    # Rename the file
    result = await editor.execute(command="rename", path=base, new_path=renamed)
    assert f"Renamed {base} to {renamed}" in result

    # Delete the file
    result = await editor.execute(command="delete", path=renamed)
    assert "Deleted" in result
