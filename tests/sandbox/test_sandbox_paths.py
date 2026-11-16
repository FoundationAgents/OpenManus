"""Offline tests for path handling in DockerSandbox (no Docker daemon needed)."""

import asyncio
import io
import sys
import tarfile
import tempfile
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

for name in ("docker", "docker.errors", "docker.models", "docker.models.containers"):
    sys.modules.setdefault(name, MagicMock())
_cfg = ModuleType("app.config")
_cfg.SandboxSettings = MagicMock()
_cfg.PROJECT_ROOT = Path(tempfile.gettempdir())
sys.modules.setdefault("app.config", _cfg)
_NotFound = type("NotFound", (Exception,), {})
sys.modules["docker.errors"].NotFound = sys.modules["docker"].errors.NotFound = _NotFound

from app.sandbox.core.sandbox import DockerSandbox  # noqa: E402


def _tar_stream(*members):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, data in members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return iter([buf.getvalue()])


def _sandbox(stream):
    sb = object.__new__(DockerSandbox)
    sb.config = MagicMock(work_dir="/workspace")
    sb.container = MagicMock()
    sb.container.get_archive.return_value = (stream, {})
    return sb


def test_copy_from_rejects_tar_escape(tmp_path):
    dst = tmp_path / "out"
    dst.mkdir()
    sb = _sandbox(_tar_stream(("../evil.txt", b"x"), ("ok.txt", b"y")))

    with pytest.raises(RuntimeError):
        asyncio.run(sb.copy_from("/workspace/dir", str(dst)))

    assert not (tmp_path / "evil.txt").exists()


def test_copy_from_extracts_normal_directory(tmp_path):
    dst = tmp_path / "out"
    dst.mkdir()
    sb = _sandbox(_tar_stream(("dir/a.txt", b"hello")))

    asyncio.run(sb.copy_from("/workspace/dir", str(dst)))

    assert (dst / "dir" / "a.txt").read_bytes() == b"hello"


def test_write_file_quotes_parent_dir():
    sb = _sandbox(iter([]))
    sb.run_command = MagicMock(side_effect=lambda cmd: _done(cmd))
    sb.container.put_archive.return_value = True
    sb._create_tar_stream = MagicMock(side_effect=lambda *a, **k: _done(b""))

    asyncio.run(sb.write_file("sub;touch_pwned/f.txt", "data"))

    cmd = sb.run_command.call_args_list[0].args[0]
    assert cmd == "mkdir -p -- '/workspace/sub;touch_pwned'"


async def _done(value):
    return value
