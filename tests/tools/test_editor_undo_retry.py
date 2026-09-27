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
    from app.tool.file_operators import LocalFileOperator
    from app.tool.str_replace_editor import StrReplaceEditor
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


@pytest.mark.asyncio
async def test_failed_undo_can_be_retried_without_losing_history(tmp_path, monkeypatch):
    path = tmp_path / "example.txt"
    path.write_text("original", encoding="utf-8")
    editor = StrReplaceEditor()
    operator = LocalFileOperator()
    monkeypatch.setattr(StrReplaceEditor, "_get_operator", lambda self: operator)
    await editor.execute(
        command="str_replace", path=str(path), old_str="original", new_str="edited"
    )

    async def fail_write(path, content):
        raise ToolError("temporary write failure")

    with monkeypatch.context() as patch:
        patch.setattr(operator, "write_file", fail_write)
        with pytest.raises(ToolError, match="temporary write failure"):
            await editor.execute(command="undo_edit", path=str(path))

    assert path.read_text(encoding="utf-8") == "edited"
    await editor.execute(command="undo_edit", path=str(path))
    assert path.read_text(encoding="utf-8") == "original"
    with pytest.raises(ToolError, match="No edit history"):
        await editor.execute(command="undo_edit", path=str(path))


@pytest.mark.asyncio
async def test_successful_undos_restore_edits_in_reverse_order(tmp_path, monkeypatch):
    path = tmp_path / "example.txt"
    path.write_text("first", encoding="utf-8")
    editor = StrReplaceEditor()
    operator = LocalFileOperator()
    monkeypatch.setattr(StrReplaceEditor, "_get_operator", lambda self: operator)
    for old, new in [("first", "second"), ("second", "third")]:
        await editor.execute(
            command="str_replace", path=str(path), old_str=old, new_str=new
        )
    for expected in ["second", "first"]:
        await editor.execute(command="undo_edit", path=str(path))
        assert path.read_text(encoding="utf-8") == expected
