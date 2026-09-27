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
@pytest.mark.parametrize(
    "original, command, arguments, expected",
    [
        (
            "build:\n\techo old\n",
            "str_replace",
            {"old_str": "build:", "new_str": "release:"},
            "release:\n\techo old\n",
        ),
        (
            "build:\n\techo old\n",
            "str_replace",
            {"old_str": "\techo old", "new_str": "\techo new"},
            "build:\n\techo new\n",
        ),
        (
            "build:\n\techo old\n",
            "insert",
            {"insert_line": 2, "new_str": "\techo new"},
            "build:\n\techo old\n\techo new\n",
        ),
        (
            "plain text\n",
            "str_replace",
            {"old_str": "plain", "new_str": "changed"},
            "changed text\n",
        ),
    ],
)
async def test_edit_and_undo_preserve_tabs(
    tmp_path, monkeypatch, original, command, arguments, expected
):
    path = tmp_path / "Makefile"
    path.write_text(original, encoding="utf-8")
    editor = StrReplaceEditor()
    operator = LocalFileOperator()
    monkeypatch.setattr(StrReplaceEditor, "_get_operator", lambda self: operator)

    await editor.execute(command=command, path=str(path), **arguments)
    assert path.read_text(encoding="utf-8") == expected

    await editor.execute(command="undo_edit", path=str(path))
    assert path.read_text(encoding="utf-8") == original


@pytest.mark.asyncio
async def test_spaces_do_not_match_a_tab_in_verbatim_replacement(tmp_path, monkeypatch):
    path = tmp_path / "Makefile"
    original = "build:\n\techo old\n"
    path.write_text(original, encoding="utf-8")
    editor = StrReplaceEditor()
    operator = LocalFileOperator()
    monkeypatch.setattr(StrReplaceEditor, "_get_operator", lambda self: operator)

    with pytest.raises(ToolError, match="did not appear verbatim"):
        await editor.execute(
            command="str_replace",
            path=str(path),
            old_str="        echo old",
            new_str="        echo new",
        )

    assert path.read_text(encoding="utf-8") == original


@pytest.mark.asyncio
async def test_view_preserves_tabs_for_subsequent_verbatim_edits(tmp_path, monkeypatch):
    path = tmp_path / "Makefile"
    path.write_text("build:\n\techo old\n", encoding="utf-8")
    editor = StrReplaceEditor()
    operator = LocalFileOperator()
    monkeypatch.setattr(StrReplaceEditor, "_get_operator", lambda self: operator)

    output = await editor.execute(command="view", path=str(path))

    assert "     2\t\techo old" in output
