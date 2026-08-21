"""app/agent must not shadow the third-party mcp package on sys.path.

Running a file from app/agent/ (or adding that directory to PYTHONPATH, as
IDEs often do) made `from mcp import ClientSession` load app/agent/mcp.py
instead of the MCP SDK. That re-entered app.tool.mcp while it was still
initializing and raised:

    ImportError: cannot import name 'MCPClients' from partially initialized
    module 'app.tool.mcp' (most likely due to a circular import)
"""

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = REPO_ROOT / "app" / "agent"


def _run_with_agent_dir_on_path(code: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(AGENT_DIR), str(REPO_ROOT)])
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def test_mcp_spec_is_sdk_not_agent_module():
    result = _run_with_agent_dir_on_path(
        "import importlib.util\n"
        "from pathlib import Path\n"
        "spec = importlib.util.find_spec('mcp')\n"
        "assert spec is not None, 'mcp SDK is not installed'\n"
        "origin = Path(spec.origin).resolve()\n"
        f"agent_dir = Path({str(AGENT_DIR)!r}).resolve()\n"
        "assert not origin.is_relative_to(agent_dir), origin\n"
        "assert spec.submodule_search_locations is not None, origin\n"
    )
    assert result.returncode == 0, result.stderr


def test_mcp_sdk_import_when_agent_directory_is_on_sys_path():
    result = _run_with_agent_dir_on_path(
        "from mcp import ClientSession, StdioServerParameters"
    )
    assert result.returncode == 0, result.stderr
