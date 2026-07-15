"""
Tests for OpenManus MCP Server components.

Run with: pytest tests/ -v
"""

import json
import os
import sys
import tempfile
from pathlib import Path


# Add the server module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_file(temp_dir):
    """Create a temporary file for testing."""
    filepath = os.path.join(temp_dir, "test_file.txt")
    with open(filepath, "w") as f:
        f.write("test content")
    yield filepath


@pytest.fixture
def task_manager():
    """Create a TaskManager instance for testing."""
    from openmanus_mcp_server.server import TaskManager

    return TaskManager(output_base_dir=tempfile.mkdtemp())


@pytest.fixture
def openmanus_agent():
    """Create an OpenManusAgent instance for testing."""
    from openmanus_mcp_server.server import OpenManusAgent

    return OpenManusAgent()


# ============================================================================
# TaskManager Tests
# ============================================================================


class TestTaskManager:
    """Tests for the TaskManager class."""

    def test_create_task(self, task_manager):
        """Test creating a task."""
        task = task_manager.create_task(
            task_name="Test Task",
            description="A test task",
            max_steps=10,
            model="gpt-4o",
        )
        assert task.task_id.startswith("task_")
        assert task.task_name == "Test Task"
        assert task.description == "A test task"
        assert task.max_steps == 10
        assert task.model == "gpt-4o"
        assert task.status.value == "pending"
        assert task.output_dir is not None

    def test_get_task(self, task_manager):
        """Test getting a task by ID."""
        task = task_manager.create_task("Test", "Test description")
        retrieved = task_manager.get_task(task.task_id)
        assert retrieved is not None
        assert retrieved.task_id == task.task_id

    def test_get_nonexistent_task(self, task_manager):
        """Test getting a nonexistent task."""
        retrieved = task_manager.get_task("task_nonexistent")
        assert retrieved is None

    def test_list_tasks(self, task_manager):
        """Test listing all tasks."""
        task_manager.create_task("Task 1", "Description 1")
        task_manager.create_task("Task 2", "Description 2")
        tasks = task_manager.list_tasks()
        assert len(tasks) == 2

    def test_update_status(self, task_manager):
        """Test updating task status."""
        from openmanus_mcp_server.server import TaskStatus

        task = task_manager.create_task("Test", "Test")
        task_manager.update_status(task.task_id, TaskStatus.RUNNING)
        assert task.status == TaskStatus.RUNNING

    def test_update_status_completed(self, task_manager):
        """Test updating task status to completed."""
        from openmanus_mcp_server.server import TaskStatus

        task = task_manager.create_task("Test", "Test")
        task_manager.update_status(task.task_id, TaskStatus.COMPLETED)
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None

    def test_update_progress(self, task_manager):
        """Test updating task progress."""
        task = task_manager.create_task("Test", "Test")
        task_manager.update_progress(task.task_id, 5, 10)
        assert task.progress == 5
        assert task.total_steps == 10

    def test_set_result(self, task_manager):
        """Test setting task result."""
        task = task_manager.create_task("Test", "Test")
        task_manager.set_result(task.task_id, "Success!")
        assert task.result == "Success!"

    def test_set_error(self, task_manager):
        """Test setting task error."""
        task = task_manager.create_task("Test", "Test")
        task_manager.set_error(task.task_id, "Something went wrong")
        assert task.error == "Something went wrong"

    def test_cancel_task(self, task_manager):
        """Test cancelling a task."""
        from openmanus_mcp_server.server import TaskStatus

        task = task_manager.create_task("Test", "Test")
        result = task_manager.cancel_task(task.task_id)
        assert result is True
        assert task.status == TaskStatus.CANCELLED
        assert task.completed_at is not None

    def test_cancel_nonexistent_task(self, task_manager):
        """Test cancelling a nonexistent task."""
        result = task_manager.cancel_task("task_nonexistent")
        assert result is False

    def test_delete_task(self, task_manager):
        """Test deleting a task."""
        task = task_manager.create_task("Test", "Test")
        result = task_manager.delete_task(task.task_id)
        assert result is True
        assert task_manager.get_task(task.task_id) is None

    def test_delete_nonexistent_task(self, task_manager):
        """Test deleting a nonexistent task."""
        result = task_manager.delete_task("task_nonexistent")
        assert result is False

    def test_task_to_dict(self, task_manager):
        """Test converting task to dictionary."""
        task = task_manager.create_task("Test", "Test")
        d = task.to_dict()
        assert d["task_id"] == task.task_id
        assert d["task_name"] == "Test"
        assert d["status"] == "pending"
        assert "created_at" in d
        assert "completed_at" in d


# ============================================================================
# Security Utility Tests
# ============================================================================


class TestSecurityUtilities:
    """Tests for security utility functions."""

    def test_resolve_path_safely_valid_path(self, task_manager):
        """Test resolving a valid path."""
        from openmanus_mcp_server.server import resolve_path_safely

        result = resolve_path_safely("/tmp/test.txt")
        assert result is not None
        assert str(result).endswith("test.txt")

    def test_resolve_path_safely_traversal(self, task_manager):
        """Test that path traversal is blocked."""
        # Set allowed dirs to /tmp only
        from openmanus_mcp_server.server import ALLOWED_WORKSPACES, resolve_path_safely

        original = ALLOWED_WORKSPACES.copy()
        try:
            ALLOWED_WORKSPACES.clear()
            ALLOWED_WORKSPACES.append("/tmp")
            # Try to access /etc/passwd
            result = resolve_path_safely("/etc/passwd")
            assert result is None
        finally:
            ALLOWED_WORKSPACES.clear()
            ALLOWED_WORKSPACES.extend(original)

    def test_resolve_path_safely_relative(self, task_manager):
        """Test resolving a relative path."""
        from openmanus_mcp_server.server import resolve_path_safely

        result = resolve_path_safely("./server.py")
        assert result is not None

    def test_sanitize_git_args_safe(self):
        """Test sanitizing safe git arguments."""
        from openmanus_mcp_server.server import sanitize_git_args

        result = sanitize_git_args("--oneline -n 5")
        assert result == ["--oneline", "-n", "5"]

    def test_sanitize_git_args_dangerous(self):
        """Test blocking dangerous git arguments."""
        from openmanus_mcp_server.server import sanitize_git_args

        result = sanitize_git_args("log; rm -rf /")
        assert ";" not in result
        assert "rm" not in result

    def test_sanitize_git_args_empty(self):
        """Test sanitizing empty arguments."""
        from openmanus_mcp_server.server import sanitize_git_args

        result = sanitize_git_args("")
        assert result == []


# ============================================================================
# OpenManusAgent Tests
# ============================================================================


class TestOpenManusAgent:
    """Tests for the OpenManusAgent class."""

    def test_execute_task(self, openmanus_agent):
        """Test executing a task."""
        result = openmanus_agent.execute_task("Test task", max_steps=5)
        assert "completed" in result.lower()

    def test_get_task_status(self, openmanus_agent):
        """Test getting task status."""
        result = openmanus_agent.get_task_status("task_nonexistent")
        assert "not found" in result.lower()

    def test_cancel_task(self, openmanus_agent):
        """Test cancelling a task."""
        result = openmanus_agent.cancel_task("task_nonexistent")
        assert "not found" in result.lower() or "cancelled" in result.lower()

    def test_list_tasks(self, openmanus_agent):
        """Test listing tasks."""
        openmanus_agent.execute_task("Test task 1")
        openmanus_agent.execute_task("Test task 2")
        result = openmanus_agent.list_tasks()
        tasks = json.loads(result)
        assert len(tasks) == 2

    def test_read_output_nonexistent(self, openmanus_agent):
        """Test reading output from nonexistent task."""
        result = openmanus_agent.read_output("task_nonexistent", "file.txt")
        assert "not found" in result.lower()


# ============================================================================
# Browser Helper Function Tests
# ============================================================================


class TestBrowserHelpers:
    """Tests for browser helper functions."""

    def test_extract_text_from_html(self):
        """Test extracting text from HTML."""
        from openmanus_mcp_server.server import _extract_text_from_html

        html = "<html><body><p>Hello <b>World</b></p></body></html>"
        text = _extract_text_from_html(html)
        assert "Hello" in text
        assert "World" in text

    def test_extract_text_from_html_with_script(self):
        """Test that script content is excluded."""
        from openmanus_mcp_server.server import _extract_text_from_html

        html = (
            "<html><body><script>alert('xss')</script><p>Safe content</p></body></html>"
        )
        text = _extract_text_from_html(html)
        assert "alert" not in text
        assert "Safe content" in text

    def test_get_page_title(self):
        """Test extracting page title."""
        from openmanus_mcp_server.server import _get_page_title

        html = "<html><head><title>Test Page</title></head><body></body></html>"
        title = _get_page_title(html)
        assert title == "Test Page"

    def test_get_page_title_no_title(self):
        """Test extracting page title when none exists."""
        from openmanus_mcp_server.server import _get_page_title

        html = "<html><body>No title</body></html>"
        title = _get_page_title(html)
        assert title == "No title"

    def test_extract_clickable_elements(self):
        """Test extracting clickable elements."""
        from openmanus_mcp_server.server import _extract_clickable_elements

        html = '<html><body><a href="https://example.com">Link</a><button>Button</button></body></html>'
        elements = _extract_clickable_elements(html)
        assert len(elements) >= 2

    def test_extract_clickable_elements_empty(self):
        """Test extracting clickable elements from empty HTML."""
        from openmanus_mcp_server.server import _extract_clickable_elements

        elements = _extract_clickable_elements("<html><body></body></html>")
        assert elements == []


# ============================================================================
# TaskOutput Tests
# ============================================================================


class TestTaskOutput:
    """Tests for the TaskOutput dataclass."""

    def test_task_output_creation(self):
        """Test creating a TaskOutput."""
        from openmanus_mcp_server.server import TaskOutput

        output = TaskOutput(type="text", text="Hello")
        assert output.type == "text"
        assert output.text == "Hello"
        assert output.data is None
        assert output.uri is None

    def test_task_output_with_all_fields(self):
        """Test creating a TaskOutput with all fields."""
        from openmanus_mcp_server.server import TaskOutput

        output = TaskOutput(
            type="image",
            text="img",
            data="base64data",
            uri="http://example.com/img.png",
        )
        assert output.type == "image"
        assert output.text == "img"
        assert output.data == "base64data"
        assert output.uri == "http://example.com/img.png"


# ============================================================================
# TaskStatus Enum Tests
# ============================================================================


class TestTaskStatus:
    """Tests for the TaskStatus enum."""

    def test_all_statuses_exist(self):
        """Test all status values exist."""
        from openmanus_mcp_server.server import TaskStatus

        assert hasattr(TaskStatus, "PENDING")
        assert hasattr(TaskStatus, "RUNNING")
        assert hasattr(TaskStatus, "COMPLETED")
        assert hasattr(TaskStatus, "FAILED")
        assert hasattr(TaskStatus, "CANCELLED")

    def test_status_values(self):
        """Test status enum values."""
        from openmanus_mcp_server.server import TaskStatus

        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"


# ============================================================================
# Health Check Tests
# ============================================================================


class TestHealthCheck:
    """Tests for the health check functionality."""

    def test_get_health_status(self, openmanus_agent):
        """Test getting health status."""
        from openmanus_mcp_server.server import get_health_status

        status = get_health_status()
        assert status["status"] == "healthy"
        assert "server" in status
        assert "tasks" in status
        assert "subscriptions" in status
        assert "browser" in status
        assert "timestamp" in status

    def test_health_status_server_info(self, openmanus_agent):
        """Test health status server info."""
        from openmanus_mcp_server.server import get_health_status

        status = get_health_status()
        assert status["server"]["name"] == "openmanus-mcp-server"
        assert status["server"]["version"] == "1.0.0"
        assert "uptime_seconds" in status["server"]
        assert "uptime_human" in status["server"]

    def test_health_status_task_counts(self, openmanus_agent):
        """Test health status task counts."""
        from openmanus_mcp_server.server import get_health_status

        # Create some tasks
        openmanus_agent.execute_task("Test task 1")
        openmanus_agent.execute_task("Test task 2")
        status = get_health_status()
        assert status["tasks"]["total"] >= 2
        assert status["tasks"]["completed"] >= 2

    def test_health_status_browser_state(self, openmanus_agent):
        """Test health status browser state."""
        from openmanus_mcp_server.server import get_health_status

        status = get_health_status()
        assert "page_loaded" in status["browser"]
        assert "current_url" in status["browser"]

    def test_format_uptime(self):
        """Test uptime formatting."""
        from openmanus_mcp_server.server import _format_uptime

        # Test seconds
        assert "1s" in _format_uptime(1)
        # Test minutes
        assert "1m" in _format_uptime(61)
        # Test hours
        assert "1h" in _format_uptime(3661)
        # Test days
        assert "1d" in _format_uptime(86401)


# ============================================================================
# Resource Subscription Tests
# ============================================================================


class TestResourceSubscription:
    """Tests for resource subscription functionality."""

    def test_subscribe_to_resource(self):
        """Test subscribing to a resource."""
        from openmanus_mcp_server.server import subscribe_to_resource

        result = subscribe_to_resource("openmanus://config", "client_1")
        assert "Subscribed" in result

    def test_unsubscribe_from_resource(self):
        """Test unsubscribing from a resource."""
        from openmanus_mcp_server.server import (
            subscribe_to_resource,
            unsubscribe_from_resource,
        )

        subscribe_to_resource("openmanus://config", "client_1")
        result = unsubscribe_from_resource("openmanus://config", "client_1")
        assert "Unsubscribed" in result

    def test_list_subscriptions_all(self):
        """Test listing all subscriptions."""
        import json

        from openmanus_mcp_server.server import (
            list_subscriptions,
            subscribe_to_resource,
        )

        subscribe_to_resource("openmanus://config", "client_1")
        subscribe_to_resource("openmanus://config", "client_2")
        result = list_subscriptions()
        data = json.loads(result)
        assert "openmanus://config" in data
        assert data["openmanus://config"]["count"] == 2

    def test_list_subscriptions_filter(self):
        """Test listing subscriptions filtered by URI."""
        import json

        from openmanus_mcp_server.server import (
            list_subscriptions,
            subscribe_to_resource,
        )

        subscribe_to_resource("openmanus://config", "client_1")
        result = list_subscriptions("openmanus://config")
        data = json.loads(result)
        assert data["resource"] == "openmanus://config"
        assert data["count"] == 1

    def test_unsubscribe_removes_empty(self):
        """Test that unsubscribing removes empty subscription sets."""
        from openmanus_mcp_server.server import (
            _resource_subscribers,
            subscribe_to_resource,
            unsubscribe_from_resource,
        )

        len(_resource_subscribers)
        subscribe_to_resource("openmanus://test", "client_1")
        unsubscribe_from_resource("openmanus://test", "client_1")
        # The subscription should be cleaned up
        assert "openmanus://test" not in _resource_subscribers


# ============================================================================
# Task Output Tests
# ============================================================================


class TestTaskOutput:
    """Tests for task output file generation."""

    def test_execute_task_creates_report(self, openmanus_agent, temp_dir):
        """Test that execute_task creates a report file."""
        task = openmanus_agent.task_manager.create_task(
            "Test Report", "Test task with code review", output_dir=temp_dir
        )
        result = openmanus_agent._simulate_task_execution(task)
        assert "completed" in result.lower()
        report_path = Path(temp_dir) / "report.md"
        assert report_path.exists()
        content = report_path.read_text()
        assert "Test Report" in content

    def test_execute_task_creates_summary(self, openmanus_agent, temp_dir):
        """Test that execute_task creates a summary.json file."""
        task = openmanus_agent.task_manager.create_task(
            "Test Summary", "Test task with file operations", output_dir=temp_dir
        )
        openmanus_agent._simulate_task_execution(task)
        summary_path = Path(temp_dir) / "summary.json"
        assert summary_path.exists()
        import json

        summary = json.loads(summary_path.read_text())
        assert summary["status"] == "completed"
        assert "analysis" in summary

    def test_execute_task_keyword_code(self, openmanus_agent, temp_dir):
        """Test keyword detection for code-related tasks."""
        task = openmanus_agent.task_manager.create_task(
            "Code Review", "Review the code for bugs", output_dir=temp_dir
        )
        openmanus_agent._simulate_task_execution(task)
        report_path = Path(temp_dir) / "report.md"
        content = report_path.read_text()
        assert "Code Analysis" in content

    def test_execute_task_keyword_search(self, openmanus_agent, temp_dir):
        """Test keyword detection for search-related tasks."""
        task = openmanus_agent.task_manager.create_task(
            "Web Search", "Search the web for information", output_dir=temp_dir
        )
        openmanus_agent._simulate_task_execution(task)
        report_path = Path(temp_dir) / "report.md"
        content = report_path.read_text()
        assert "Web Research" in content

    def test_execute_task_keyword_git(self, openmanus_agent, temp_dir):
        """Test keyword detection for git-related tasks."""
        task = openmanus_agent.task_manager.create_task(
            "Git Task", "Commit changes and push to remote", output_dir=temp_dir
        )
        openmanus_agent._simulate_task_execution(task)
        report_path = Path(temp_dir) / "report.md"
        content = report_path.read_text()
        assert "Git Operations" in content

    def test_execute_task_general(self, openmanus_agent, temp_dir):
        """Test general task detection when no keywords match."""
        task = openmanus_agent.task_manager.create_task(
            "General Task", "Do something unrelated", output_dir=temp_dir
        )
        openmanus_agent._simulate_task_execution(task)
        report_path = Path(temp_dir) / "report.md"
        content = report_path.read_text()
        assert "General Task" in content


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for the server components."""

    def test_full_task_lifecycle(self, openmanus_agent):
        """Test the full task lifecycle."""
        # Create and execute task
        result = openmanus_agent.execute_task("Integration test task", max_steps=10)

        # Parse task ID from result
        assert "completed" in result.lower()

        # Get status
        status = openmanus_agent.get_task_status("task_nonexistent")
        assert "not found" in status.lower()

        # List tasks
        tasks = json.loads(openmanus_agent.list_tasks())
        assert len(tasks) >= 1

    def test_task_manager_with_custom_output_dir(self, temp_dir):
        """Test TaskManager with custom output directory."""
        from openmanus_mcp_server.server import TaskManager

        tm = TaskManager(output_base_dir=temp_dir)
        task = tm.create_task("Test", "Test")
        assert task.output_dir.startswith(temp_dir)

    def test_multiple_tasks_different_models(self, openmanus_agent):
        """Test creating tasks with different models."""
        task1 = openmanus_agent.execute_task("Task 1", model="gpt-4o")
        task2 = openmanus_agent.execute_task("Task 2", model="claude-3-opus")

        tasks = json.loads(openmanus_agent.list_tasks())
        models = [t["model"] for t in tasks]
        assert "gpt-4o" in models
        assert "claude-3-opus" in models

    def test_health_check_integration(self, openmanus_agent):
        """Test health check as part of integration."""
        from openmanus_mcp_server.server import get_health_status

        openmanus_agent.execute_task("Integration health test")
        status = get_health_status()
        assert status["status"] == "healthy"
        assert status["tasks"]["total"] >= 1


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_task_manager_output_dir_creation(self, temp_dir):
        """Test that output directory is created if it doesn't exist."""
        from openmanus_mcp_server.server import TaskManager

        new_dir = os.path.join(temp_dir, "new_output_dir")
        tm = TaskManager(output_base_dir=new_dir)
        assert os.path.exists(new_dir)

    def test_task_id_uniqueness(self, task_manager):
        """Test that task IDs are unique."""
        task1 = task_manager.create_task("Task 1", "Test")
        task2 = task_manager.create_task("Task 2", "Test")
        assert task1.task_id != task2.task_id

    def test_task_progress_boundary(self, task_manager):
        """Test task progress at boundaries."""
        task = task_manager.create_task("Test", "Test")
        task_manager.update_progress(task.task_id, 0, 10)
        assert task.progress == 0
        task_manager.update_progress(task.task_id, 10, 10)
        assert task.progress == 10

    def test_cancel_completed_task(self, task_manager):
        """Test cancelling an already completed task."""
        from openmanus_mcp_server.server import TaskStatus

        task = task_manager.create_task("Test", "Test")
        task_manager.update_status(task.task_id, TaskStatus.COMPLETED)
        result = task_manager.cancel_task(task.task_id)
        assert result is True  # Should still return True even if already completed

    def test_empty_task_description(self, openmanus_agent):
        """Test handling empty task description."""
        task = openmanus_agent.task_manager.create_task(
            "", "Empty task name", output_dir=tempfile.mkdtemp()
        )
        result = openmanus_agent._simulate_task_execution(task)
        assert "completed" in result.lower()

    def test_very_long_task_description(self, openmanus_agent, temp_dir):
        """Test handling very long task descriptions."""
        long_desc = "x" * 10000
        task = openmanus_agent.task_manager.create_task(
            long_desc[:50], long_desc, output_dir=temp_dir
        )
        result = openmanus_agent._simulate_task_execution(task)
        assert "completed" in result.lower()

    def test_special_characters_in_path(self, task_manager):
        """Test handling special characters in paths."""
        from openmanus_mcp_server.server import resolve_path_safely

        result = resolve_path_safely("/tmp/test file (1).txt")
        assert result is not None

    def test_delete_and_recreate_task(self, task_manager):
        """Test deleting and recreating a task."""
        task = task_manager.create_task("Test", "Test")
        task_manager.delete_task(task.task_id)
        new_task = task_manager.create_task("New Test", "New Test")
        assert new_task.task_id != task.task_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
