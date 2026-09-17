from types import SimpleNamespace

import pytest

from app.config import DaytonaSettings
from app.sandbox.core.sandbox import DockerSandbox


def test_daytona_configuration_is_optional():
    settings = DaytonaSettings()

    assert settings.daytona_api_key is None


@pytest.fixture
def sandbox_without_docker():
    sandbox = DockerSandbox.__new__(DockerSandbox)
    sandbox.config = SimpleNamespace(work_dir="/workspace")
    return sandbox


def test_sandbox_resolves_relative_paths_inside_work_directory(
    sandbox_without_docker,
):
    assert (
        sandbox_without_docker._safe_resolve_path("nested/output.txt")
        == "/workspace/nested/output.txt"
    )


@pytest.mark.parametrize(
    "path", ["/etc/passwd", "../outside.txt", "nested/../../outside.txt"]
)
def test_sandbox_rejects_paths_outside_work_directory(
    sandbox_without_docker, path
):
    with pytest.raises(ValueError, match="within the sandbox work directory"):
        sandbox_without_docker._safe_resolve_path(path)
