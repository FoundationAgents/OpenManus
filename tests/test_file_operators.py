import os
from pathlib import Path

import pytest
import pytest_asyncio

from app.sandbox.core.sandbox import DockerSandbox, SandboxSettings
from app.tool.file_operators import FileOperator, LocalFileOperator, SandboxFileOperator


@pytest_asyncio.fixture(scope="module")
async def sandbox_instance():
    """Creates a single sandbox instance for all sandbox tests."""
    sandbox = DockerSandbox(
        SandboxSettings(
            image="python:3.12-slim",
            work_dir="/workspace",
            memory_limit="1g",
            cpu_limit=0.5,
            network_enabled=True,
        )
    )
    await sandbox.create()
    try:
        yield sandbox
    finally:
        await sandbox.cleanup()


@pytest_asyncio.fixture(params=["local", "sandbox"])
async def file_operator(request, sandbox_instance) -> FileOperator:
    """Parametrized fixture to test both file operators with initialized environment."""
    if request.param == "local":
        return LocalFileOperator()
    elif request.param == "sandbox":
        op = SandboxFileOperator()
        op.sandbox_client.sandbox = sandbox_instance
        return op


@pytest.mark.asyncio
async def test_write_and_read_file(file_operator: FileOperator):
    """Tests writing to and reading from a file."""
    path = "test_file_ops.txt"
    content = "Hello, test!"

    await file_operator.write_file(path, content)
    read_back = await file_operator.read_file(path)

    assert read_back.strip() == content

    await file_operator.delete(path)


@pytest.mark.asyncio
async def test_create_and_delete_directory(file_operator: FileOperator):
    """Tests directory creation and deletion."""
    path = "test_dir"

    await file_operator.create_directory(path)
    assert await file_operator.exists(path)
    assert await file_operator.is_directory(path)

    await file_operator.delete(path)
    assert not await file_operator.exists(path)


@pytest.mark.asyncio
async def test_rename_file(file_operator: FileOperator):
    """Tests renaming a file."""
    src = "original.txt"
    dst = "renamed.txt"

    await file_operator.write_file(src, "Test content")
    await file_operator.rename(src, dst)

    assert await file_operator.exists(dst)
    assert not await file_operator.exists(src)

    await file_operator.delete(dst)


@pytest.mark.asyncio
async def test_delete_file_and_directory(file_operator: FileOperator):
    """Tests deletion of both file and empty directory."""
    file_path = "test_delete.txt"
    dir_path = "test_delete_dir"

    # Create and delete file
    await file_operator.write_file(file_path, "To be deleted")
    assert await file_operator.exists(file_path)
    await file_operator.delete(file_path)
    assert not await file_operator.exists(file_path)

    # Create and delete directory
    await file_operator.create_directory(dir_path)
    assert await file_operator.exists(dir_path)
    await file_operator.delete(dir_path)
    assert not await file_operator.exists(dir_path)


@pytest.mark.asyncio
async def test_delete_non_empty_directory(file_operator: FileOperator):
    """Tests that deleting a non-empty directory raises an error."""
    dir_path = "non_empty_dir"
    file_path = f"{dir_path}/file_in_dir.txt"

    # Create directory and a file inside it
    await file_operator.create_directory(dir_path)
    await file_operator.write_file(file_path, "Content inside directory")

    # Attempt to delete the non-empty directory
    with pytest.raises(
        Exception
    ):  # Replace Exception with the specific exception if known
        await file_operator.delete(dir_path)

    # Cleanup
    await file_operator.delete(file_path)
    await file_operator.delete(dir_path)


@pytest.mark.asyncio
async def test_create_directory_with_missing_parent(file_operator: FileOperator):
    """Tests that creating a directory with a missing parent succeeds."""
    nested_path = "missing_parent_dir/child_dir"

    await file_operator.create_directory(nested_path)
    assert await file_operator.exists(nested_path)
    assert await file_operator.is_directory(nested_path)

    # Cleanup
    await file_operator.delete(nested_path)
    await file_operator.delete("missing_parent_dir")


@pytest.mark.asyncio
async def test_delete_file_with_inexact_name(file_operator: FileOperator):
    """Tests that deleting a file with an inexact name (e.g., using a wildcard) raises an error."""
    file_path = "test_inexact_delete.txt"

    # Create the file
    await file_operator.write_file(file_path, "Content to delete")

    # Attempt to delete using an inexact name
    with pytest.raises(
        Exception
    ):  # Replace Exception with the specific exception if known
        await file_operator.delete("test_inexact_*")

    # Cleanup
    await file_operator.delete(file_path)
