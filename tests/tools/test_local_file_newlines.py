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
    from app.tool.file_operators import LocalFileOperator
finally:
    if _CREATED_TEST_CONFIG:
        _CONFIG_PATH.unlink()


@pytest.mark.asyncio
@pytest.mark.parametrize("as_string", [False, True])
@pytest.mark.parametrize(
    "content", ["", "one\ntwo\n", "one\r\ntwo\r\n", "中文\n混合\r\n末尾\r"]
)
async def test_write_file_preserves_requested_newlines(tmp_path, content, as_string):
    path = tmp_path / "output.txt"
    operator = LocalFileOperator()

    await operator.write_file(str(path) if as_string else path, content)

    assert path.read_bytes() == content.encode("utf-8")
