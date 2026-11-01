import pytest

from app.utils.files_utils import clean_path


@pytest.mark.parametrize(
    ("path", "workspace_path", "expected"),
    [
        ("/workspace-other/file.py", "/workspace", "workspace-other/file.py"),
        ("workspace2/file.py", "/workspace", "workspace2/file.py"),
        ("/workspace/workspace/file.py", "/workspace", "workspace/file.py"),
        ("/custom/root/workspace/file.py", "/custom/root", "workspace/file.py"),
        ("/custom/root-other/file.py", "/custom/root", "custom/root-other/file.py"),
        ("/workspace/file.py", "/workspace", "file.py"),
        ("workspace/file.py", "/workspace", "file.py"),
        ("/workspace", "/workspace", ""),
        ("/custom/root/file.py", "/custom/root", "file.py"),
        ("workspace/file.py", "/custom/root", "file.py"),
        ("relative/file.py", "/workspace", "relative/file.py"),
        ("file.py", "/workspace", "file.py"),
        ("/workspace//file.py", "/workspace", "file.py"),
        ("/workspace/file.py", "/workspace/", "file.py"),
        ("/custom/root/file.py", "/custom/root/", "file.py"),
        ("/custom/root//file.py", "/custom/root//", "file.py"),
        ("/workspace", "/workspace/", ""),
        ("/custom/root", "/custom/root//", ""),
        ("/workspace/workspace/file.py", "/workspace/", "workspace/file.py"),
        ("/custom/root/workspace/file.py", "/custom/root/", "workspace/file.py"),
        ("/relative/file.py", "/", "relative/file.py"),
        ("/relative/file.py", "", "relative/file.py"),
    ],
)
def test_workspace_prefix_matches_complete_components(path, workspace_path, expected):
    assert clean_path(path, workspace_path) == expected
