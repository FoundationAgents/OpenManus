import asyncio
import multiprocessing
import os

import psutil
import pytest

from app.tool.python_execute import PythonExecute


def _running(process):
    try:
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


@pytest.mark.parametrize("start_method", ["spawn", "fork"])
@pytest.mark.parametrize("ignore_sigterm", [False, True])
def test_timeout_cleans_detached_descendants(
    tmp_path, monkeypatch, start_method, ignore_sigterm
):
    if start_method not in multiprocessing.get_all_start_methods():
        pytest.skip(f"{start_method} is unavailable")
    if os.name != "posix":
        pytest.skip("Separate sessions and SIGTERM handlers require POSIX")

    context = multiprocessing.get_context(start_method)
    monkeypatch.setattr(multiprocessing, "Process", context.Process)
    monkeypatch.setattr(multiprocessing, "Manager", context.Manager)
    pid_file = tmp_path / "descendant.pid"
    grandchild_file = tmp_path / "grandchild.pid"
    grandchild_code = (
        "import os, signal, time; from pathlib import Path; "
        + ("signal.signal(signal.SIGTERM, signal.SIG_IGN); " if ignore_sigterm else "")
        + f"Path({str(grandchild_file)!r}).write_text(str(os.getpid())); "
        + "time.sleep(60)"
    )
    child_code = (
        "import os, signal, subprocess, sys, time; from pathlib import Path; "
        + ("signal.signal(signal.SIGTERM, signal.SIG_IGN); " if ignore_sigterm else "")
        + f"Path({str(pid_file)!r}).write_text(str(os.getpid())); "
        + f"subprocess.Popen([sys.executable, '-c', {grandchild_code!r}], "
        + "start_new_session=True); time.sleep(60)"
    )
    code = (
        "import signal, subprocess, sys, time\n"
        + ("signal.signal(signal.SIGTERM, signal.SIG_IGN)\n" if ignore_sigterm else "")
        + f"subprocess.Popen([sys.executable, '-c', {child_code!r}], "
        + "start_new_session=True)\ntime.sleep(60)"
    )
    processes = []
    existing_workers = {process.pid for process in multiprocessing.active_children()}
    try:
        result = asyncio.run(PythonExecute().execute(code, timeout=3))
        assert result == {
            "observation": "Execution timeout after 3 seconds",
            "success": False,
        }
        for path in (pid_file, grandchild_file):
            assert path.exists(), f"Test descendant did not start: {path.name}"
            try:
                processes.append(psutil.Process(int(path.read_text())))
            except psutil.NoSuchProcess:
                continue
        assert not any(_running(process) for process in processes)
        assert all(
            process.pid in existing_workers
            for process in multiprocessing.active_children()
        )
    finally:
        # Also clean up when this regression test runs against the old code.
        for path in (pid_file, grandchild_file):
            if path.exists():
                try:
                    process = psutil.Process(int(path.read_text()))
                    if _running(process):
                        process.kill()
                except psutil.NoSuchProcess:
                    pass


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("print('hello')", {"observation": "hello\n", "success": True}),
        (
            "raise ValueError('controlled error')",
            {"observation": "controlled error", "success": False},
        ),
    ],
)
def test_normal_execution_results_are_preserved(code, expected):
    assert asyncio.run(PythonExecute().execute(code)) == expected
