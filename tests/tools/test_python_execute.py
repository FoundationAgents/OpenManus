from pathlib import Path

import pytest


@pytest.fixture(scope="module", autouse=True)
def _python_execute_config():
    config = Path(__file__).parents[2] / "config" / "config.toml"
    created = not config.exists()
    if created:
        config.write_text(
            '[llm]\nmodel="test"\nbase_url="http://localhost"\napi_key="test"\n'
            '\n[daytona]\ndaytona_api_key="test"\n',
            encoding="utf-8",
        )
    try:
        yield
    finally:
        if created:
            config.unlink()


@pytest.mark.asyncio
async def test_python_execute_runs_main_guard(tmp_path):
    from app.tool.python_execute import PythonExecute

    report = tmp_path / "report.txt"
    code = (
        "from pathlib import Path\nVALUE = 'report'\n"
        f"def main():\n    Path({str(report)!r}).write_text(VALUE, encoding='utf-8')\n"
        "    print(VALUE)\nif __name__ == '__main__':\n    main()"
    )
    result = await PythonExecute().execute(code=code, timeout=20)

    assert result == {"observation": "report\n", "success": True}
    assert report.read_text(encoding="utf-8") == "report"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code, expected",
    [
        ("print(__name__)", {"observation": "__main__\n", "success": True}),
        (
            "import math\nVALUE = 9\ndef calculate():\n    print(math.sqrt(VALUE))\ncalculate()",
            {"observation": "3.0\n", "success": True},
        ),
        (
            "raise ValueError('bad input')",
            {"observation": "bad input", "success": False},
        ),
        ("pass", {"observation": "", "success": True}),
    ],
)
async def test_python_execute_namespace_preserves_results(code, expected):
    from app.tool.python_execute import PythonExecute

    assert await PythonExecute().execute(code=code, timeout=20) == expected
