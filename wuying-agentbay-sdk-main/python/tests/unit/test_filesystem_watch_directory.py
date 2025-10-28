"""
Unit tests for watch_directory functionality in FileSystem module.
"""

import unittest
from unittest.mock import Mock, patch
import threading
import time
import json
from typing import List, Dict, Any

from agentbay.filesystem.filesystem import FileSystem, FileChangeEvent, FileChangeResult


class TestFileChangeEvent(unittest.TestCase):
    """Test FileChangeEvent class."""

    def test_file_change_event_init(self):
        """Test FileChangeEvent initialization."""
        event = FileChangeEvent(
            event_type="modify",
            path="/tmp/test.txt",
            path_type="file"
        )
        
        self.assertEqual(event.event_type, "modify")
        self.assertEqual(event.path, "/tmp/test.txt")
        self.assertEqual(event.path_type, "file")

    def test_file_change_event_repr(self):
        """Test FileChangeEvent string representation."""
        event = FileChangeEvent(
            event_type="create",
            path="/tmp/new_file.txt",
            path_type="file"
        )
        
        expected = "FileChangeEvent(event_type='create', path='/tmp/new_file.txt', path_type='file')"
        self.assertEqual(repr(event), expected)

    def test_file_change_event_to_dict(self):
        """Test FileChangeEvent to_dict method."""
        event = FileChangeEvent(
            event_type="delete",
            path="/tmp/deleted.txt",
            path_type="file"
        )
        
        expected_dict = {
            "eventType": "delete",
            "path": "/tmp/deleted.txt",
            "pathType": "file"
        }
        self.assertEqual(event.to_dict(), expected_dict)

    def test_file_change_event_from_dict(self):
        """Test FileChangeEvent from_dict class method."""
        data = {
            "eventType": "modify",
            "path": "/tmp/modified.txt",
            "pathType": "file"
        }
        
        event = FileChangeEvent.from_dict(data)
        
        self.assertEqual(event.event_type, "modify")
        self.assertEqual(event.path, "/tmp/modified.txt")
        self.assertEqual(event.path_type, "file")

    def test_file_change_event_from_dict_missing_fields(self):
        """Test FileChangeEvent from_dict with missing fields."""
        data = {"eventType": "create"}
        
        event = FileChangeEvent.from_dict(data)
        
        self.assertEqual(event.event_type, "create")
        self.assertEqual(event.path, "")
        self.assertEqual(event.path_type, "")


class TestFileChangeResult(unittest.TestCase):
    """Test FileChangeResult class."""

    def test_file_change_result_init(self):
        """Test FileChangeResult initialization."""
        events = [
            FileChangeEvent("create", "/tmp/file1.txt", "file"),
            FileChangeEvent("modify", "/tmp/file2.txt", "file")
        ]
        
        result = FileChangeResult(
            request_id="test-123",
            success=True,
            events=events,
            raw_data='[{"eventType":"create","path":"/tmp/file1.txt","pathType":"file"}]'
        )
        
        self.assertEqual(result.request_id, "test-123")
        self.assertTrue(result.success)
        self.assertEqual(len(result.events), 2)
        self.assertEqual(result.events[0].event_type, "create")
        self.assertEqual(result.events[1].event_type, "modify")

    def test_file_change_result_has_changes(self):
        """Test FileChangeResult has_changes method."""
        # Test with events
        events = [FileChangeEvent("create", "/tmp/file1.txt", "file")]
        result = FileChangeResult(success=True, events=events)
        self.assertTrue(result.has_changes())
        
        # Test without events
        result_empty = FileChangeResult(success=True, events=[])
        self.assertFalse(result_empty.has_changes())

    def test_file_change_result_get_modified_files(self):
        """Test FileChangeResult get_modified_files method."""
        events = [
            FileChangeEvent("create", "/tmp/file1.txt", "file"),
            FileChangeEvent("modify", "/tmp/file2.txt", "file"),
            FileChangeEvent("modify", "/tmp/dir1", "directory"),
            FileChangeEvent("delete", "/tmp/file3.txt", "file"),
            FileChangeEvent("modify", "/tmp/file4.txt", "file")
        ]
        
        result = FileChangeResult(success=True, events=events)
        modified_files = result.get_modified_files()
        
        expected = ["/tmp/file2.txt", "/tmp/file4.txt"]
        self.assertEqual(modified_files, expected)

    def test_file_change_result_get_created_files(self):
        """Test FileChangeResult get_created_files method."""
        events = [
            FileChangeEvent("create", "/tmp/file1.txt", "file"),
            FileChangeEvent("modify", "/tmp/file2.txt", "file"),
            FileChangeEvent("create", "/tmp/dir1", "directory"),
            FileChangeEvent("create", "/tmp/file3.txt", "file")
        ]
        
        result = FileChangeResult(success=True, events=events)
        created_files = result.get_created_files()
        
        expected = ["/tmp/file1.txt", "/tmp/file3.txt"]
        self.assertEqual(created_files, expected)

    def test_file_change_result_get_deleted_files(self):
        """Test FileChangeResult get_deleted_files method."""
        events = [
            FileChangeEvent("create", "/tmp/file1.txt", "file"),
            FileChangeEvent("delete", "/tmp/file2.txt", "file"),
            FileChangeEvent("delete", "/tmp/dir1", "directory"),
            FileChangeEvent("delete", "/tmp/file3.txt", "file")
        ]
        
        result = FileChangeResult(success=True, events=events)
        deleted_files = result.get_deleted_files()
        
        expected = ["/tmp/file2.txt", "/tmp/file3.txt"]
        self.assertEqual(deleted_files, expected)


class TestFileSystemWatchDirectory(unittest.TestCase):
    """Test FileSystem watch_directory functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.mock_session.get_api_key.return_value = "test-api-key"
        self.mock_session.get_session_id.return_value = "test-session-id"
        
        self.filesystem = FileSystem(self.mock_session)

    def test_get_file_change_success(self):
        """Test _get_file_change method with successful response."""
        # Mock successful response
        mock_result = Mock()
        mock_result.success = True
        mock_result.request_id = "test-123"
        mock_result.data = json.dumps([
            {"eventType": "create", "path": "/tmp/file1.txt", "pathType": "file"},
            {"eventType": "modify", "path": "/tmp/file2.txt", "pathType": "file"}
        ])
        
        self.filesystem._call_mcp_tool = Mock(return_value=mock_result)
        
        # Test the method
        result = self.filesystem._get_file_change("/tmp/test_dir")
        
        # Verify the call
        self.filesystem._call_mcp_tool.assert_called_once_with("get_file_change", {"path": "/tmp/test_dir"})
        
        # Verify the result
        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "test-123")
        self.assertEqual(len(result.events), 2)
        self.assertEqual(result.events[0].event_type, "create")
        self.assertEqual(result.events[0].path, "/tmp/file1.txt")
        self.assertEqual(result.events[1].event_type, "modify")
        self.assertEqual(result.events[1].path, "/tmp/file2.txt")

    def test_get_file_change_failure(self):
        """Test _get_file_change method with failed response."""
        # Mock failed response
        mock_result = Mock()
        mock_result.success = False
        mock_result.request_id = "test-456"
        mock_result.error_message = "Directory not found"
        mock_result.data = ""
        
        self.filesystem._call_mcp_tool = Mock(return_value=mock_result)
        
        # Test the method
        result = self.filesystem._get_file_change("/tmp/nonexistent")
        
        # Verify the result
        self.assertFalse(result.success)
        self.assertEqual(result.request_id, "test-456")
        self.assertEqual(result.error_message, "Directory not found")
        self.assertEqual(len(result.events), 0)

    def test_get_file_change_invalid_json(self):
        """Test _get_file_change method with invalid JSON response."""
        # Mock response with invalid JSON
        mock_result = Mock()
        mock_result.success = True
        mock_result.request_id = "test-789"
        mock_result.data = "invalid json data"
        
        self.filesystem._call_mcp_tool = Mock(return_value=mock_result)
        
        # Test the method
        result = self.filesystem._get_file_change("/tmp/test_dir")
        
        # Verify the result - should still succeed but with empty events
        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "test-789")
        self.assertEqual(len(result.events), 0)

    def test_watch_directory_basic(self):
        """Test basic watch_directory functionality."""
        callback_events = []
        
        def test_callback(events):
            callback_events.extend(events)
        
        # Mock _get_file_change to return some events
        mock_events = [FileChangeEvent("create", "/tmp/test.txt", "file")]
        mock_result = FileChangeResult(success=True, events=mock_events)
        
        self.filesystem._get_file_change = Mock(return_value=mock_result)
        
        # Start watching
        stop_event = threading.Event()
        thread = self.filesystem.watch_directory(
            path="/tmp/test_dir",
            callback=test_callback,
            interval=0.1,  # Very short interval for testing
            stop_event=stop_event
        )
        
        # Verify thread properties
        self.assertIsInstance(thread, threading.Thread)
        self.assertEqual(thread.stop_event, stop_event)
        self.assertTrue(thread.daemon)
        
        # Start the thread and let it run briefly
        thread.start()
        time.sleep(0.2)  # Let it run for a short time
        
        # Stop the thread
        stop_event.set()
        thread.join(timeout=1.0)
        
        # Verify callback was called with events
        self.assertGreater(len(callback_events), 0)
        self.assertEqual(callback_events[0].event_type, "create")
        self.assertEqual(callback_events[0].path, "/tmp/test.txt")

    def test_watch_directory_callback_exception(self):
        """Test watch_directory handles callback exceptions gracefully."""
        def failing_callback(events):
            raise Exception("Callback error")
        
        # Mock _get_file_change to return some events
        mock_events = [FileChangeEvent("create", "/tmp/test.txt", "file")]
        mock_result = FileChangeResult(success=True, events=mock_events)
        
        self.filesystem._get_file_change = Mock(return_value=mock_result)
        
        # Start watching
        stop_event = threading.Event()
        thread = self.filesystem.watch_directory(
            path="/tmp/test_dir",
            callback=failing_callback,
            interval=0.1,
            stop_event=stop_event
        )
        
        # Start the thread and let it run briefly
        thread.start()
        time.sleep(0.2)
        
        # Stop the thread - should not crash despite callback exception
        stop_event.set()
        thread.join(timeout=1.0)
        
        # Thread should have completed without crashing
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main() 