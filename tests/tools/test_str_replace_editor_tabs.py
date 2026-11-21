"""Regression tests for tab handling in ``StrReplaceEditor``.

Editing a file must only change the matched text: the rest of the file has to be
written back byte for byte, including its tab indentation.
"""

from pathlib import Path

import pytest


# ``app.config`` needs config/config.toml (with a daytona section) to import; create
# a throw-away one so the suite runs on a fresh checkout without a local config.
_CONFIG = Path(__file__).resolve().parents[2] / "config" / "config.toml"
if not _CONFIG.exists():
    _CONFIG.write_text(
        '[llm]\nmodel = "test"\nbase_url = "http://localhost"\napi_key = "test"\n'
        '\n[daytona]\ndaytona_api_key = "test"\n',
        encoding="utf-8",
    )

from app.exceptions import ToolError  # noqa: E402
from app.tool.str_replace_editor import StrReplaceEditor  # noqa: E402


TABBED = "def f():\n\tif True:\n\t\treturn 1\n\treturn 2\n"


@pytest.fixture
def editor() -> StrReplaceEditor:
    return StrReplaceEditor()


@pytest.fixture
def tabbed_file(tmp_path: Path) -> Path:
    path = tmp_path / "indented.py"
    path.write_text(TABBED, encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_str_replace_keeps_untouched_tabs(editor, tabbed_file):
    await editor.execute(
        command="str_replace",
        path=str(tabbed_file),
        old_str="\treturn 2",
        new_str="\treturn 3",
    )

    assert tabbed_file.read_text(encoding="utf-8") == (
        "def f():\n\tif True:\n\t\treturn 1\n\treturn 3\n"
    )


@pytest.mark.asyncio
async def test_insert_keeps_untouched_tabs(editor, tabbed_file):
    await editor.execute(
        command="insert", path=str(tabbed_file), insert_line=1, new_str="\tpass"
    )

    assert tabbed_file.read_text(encoding="utf-8") == (
        "def f():\n\tpass\n\tif True:\n\t\treturn 1\n\treturn 2\n"
    )


@pytest.mark.asyncio
async def test_undo_edit_restores_original_tabs(editor, tabbed_file):
    await editor.execute(
        command="str_replace",
        path=str(tabbed_file),
        old_str="\treturn 2",
        new_str="\treturn 3",
    )
    await editor.execute(command="undo_edit", path=str(tabbed_file))

    assert tabbed_file.read_text(encoding="utf-8") == TABBED


@pytest.mark.asyncio
async def test_str_replace_still_accepts_space_indented_old_str(editor, tabbed_file):
    """A request that indents with spaces instead of tabs keeps working."""
    await editor.execute(
        command="str_replace",
        path=str(tabbed_file),
        old_str="        return 2",
        new_str="\treturn 3",
    )

    assert tabbed_file.read_text(encoding="utf-8") == (
        "def f():\n\tif True:\n\t\treturn 1\n\treturn 3\n"
    )


@pytest.mark.asyncio
async def test_str_replace_rejects_duplicate_matches(editor, tmp_path: Path):
    path = tmp_path / "dup.py"
    path.write_text("x = 1\nx = 1\n", encoding="utf-8")

    with pytest.raises(ToolError, match="Multiple occurrences"):
        await editor.execute(
            command="str_replace", path=str(path), old_str="x = 1", new_str="x = 2"
        )

    assert path.read_text(encoding="utf-8") == "x = 1\nx = 1\n"


@pytest.mark.asyncio
async def test_str_replace_reports_missing_old_str(editor, tabbed_file):
    with pytest.raises(ToolError, match="did not appear verbatim"):
        await editor.execute(
            command="str_replace",
            path=str(tabbed_file),
            old_str="nope",
            new_str="other",
        )
