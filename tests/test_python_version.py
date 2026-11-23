import runpy
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "version, expected_warning",
    [
        ((3, 10, 16, "final", 0), True),
        ((3, 11, 11, "final", 0), False),
        ((3, 12, 9, "final", 0), False),
        ((3, 13, 2, "final", 0), False),
        ((3, 14, 0, "final", 0), True),
    ],
)
def test_supported_python_version_warning(
    version, expected_warning, monkeypatch, capsys
):
    monkeypatch.setattr(sys, "version_info", version)

    runpy.run_path(str(Path(__file__).parents[1] / "app" / "__init__.py"))

    output = capsys.readouterr().out
    if expected_warning:
        assert "Unsupported Python version" in output
        assert "please use 3.11-3.13" in output
    else:
        assert output == ""
