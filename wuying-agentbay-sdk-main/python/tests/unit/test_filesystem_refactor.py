import unittest
from unittest.mock import MagicMock, patch

from agentbay.filesystem.filesystem import (
    BoolResult,
    FileContentResult,
    FileInfoResult,
    FileSystem,
)
from agentbay.model import OperationResult


class DummySession:
    def __init__(self):
        self.api_key = "dummy_key"
        self.session_id = "dummy_session"
        self.client = MagicMock()

    def get_api_key(self):
        return self.api_key

    def get_session_id(self):
        return self.session_id

    def get_client(self):
        return self.client


class TestFileSystemRefactor(unittest.TestCase):
    """
    Test cases to verify the refactored FileSystem API behavior.
    These tests ensure that the new unified read_file and write_file methods
    work correctly with automatic chunking for large files.
    """

    def setUp(self):
        self.session = DummySession()
        self.fs = FileSystem(self.session)

    # Test internal chunk methods exist and work correctly
    @patch("agentbay.filesystem.filesystem.FileSystem._call_mcp_tool")
    def test_read_file_chunk_internal_method_exists(self, mock_call_mcp_tool):
        """
        Test that _read_file_chunk internal method exists and works correctly.
        """
        mock_result = OperationResult(
            request_id="request-123", success=True, data="chunk content"
        )
        mock_call_mcp_tool.return_value = mock_result

        # Test internal method exists
        self.assertTrue(hasattr(self.fs, '_read_file_chunk'))

        result = self.fs._read_file_chunk("/path/to/file.txt", 0, 100)
        self.assertIsInstance(result, FileContentResult)
        self.assertTrue(result.success)
        self.assertEqual(result.content, "chunk content")
        self.assertEqual(result.request_id, "request-123")

    @patch("agentbay.filesystem.filesystem.FileSystem._call_mcp_tool")
    def test_write_file_chunk_internal_method_exists(self, mock_call_mcp_tool):
        """
        Test that _write_file_chunk internal method exists and works correctly.
        """
        mock_result = OperationResult(
            request_id="request-123", success=True, data="True"
        )
        mock_call_mcp_tool.return_value = mock_result

        # Test internal method exists
        self.assertTrue(hasattr(self.fs, '_write_file_chunk'))

        result = self.fs._write_file_chunk("/path/to/file.txt", "content", "overwrite")
        self.assertIsInstance(result, BoolResult)
        self.assertTrue(result.success)
        self.assertTrue(result.data)
        self.assertEqual(result.request_id, "request-123")

    # Test new unified read_file method
    @patch("agentbay.filesystem.filesystem.FileSystem.get_file_info")
    @patch("agentbay.filesystem.filesystem.FileSystem._read_file_chunk")
    def test_read_file_small_file_direct_read(self, mock_read_chunk, mock_get_file_info):
        """
        Test that read_file handles small files efficiently (single chunk).
        """
        # Mock file info for small file (1KB)
        file_info_result = FileInfoResult(
            request_id="request-123",
            success=True,
            file_info={"size": 1024, "isDirectory": False},
        )
        mock_get_file_info.return_value = file_info_result

        # Mock single chunk read
        mock_read_chunk.return_value = FileContentResult(
            request_id="request-123-1", success=True, content="small file content"
        )

        result = self.fs.read_file("/path/to/small_file.txt")

        self.assertIsInstance(result, FileContentResult)
        self.assertTrue(result.success)
        self.assertEqual(result.content, "small file content")
        mock_get_file_info.assert_called_once_with("/path/to/small_file.txt")
        mock_read_chunk.assert_called_once_with("/path/to/small_file.txt", 0, 1024)

    @patch("agentbay.filesystem.filesystem.FileSystem.get_file_info")
    @patch("agentbay.filesystem.filesystem.FileSystem._read_file_chunk")
    def test_read_file_large_file_chunked_read(self, mock_read_chunk, mock_get_file_info):
        """
        Test that read_file handles large files with automatic chunking.
        """
        # Mock file info for large file (150KB)
        file_info_result = FileInfoResult(
            request_id="request-123",
            success=True,
            file_info={"size": 150 * 1024, "isDirectory": False},
        )
        mock_get_file_info.return_value = file_info_result

        # Mock chunked reads (3 chunks of 50KB each)
        mock_read_chunk.side_effect = [
            FileContentResult(request_id="request-123-1", success=True, content="chunk1"),
            FileContentResult(request_id="request-123-2", success=True, content="chunk2"),
            FileContentResult(request_id="request-123-3", success=True, content="chunk3"),
        ]

        result = self.fs.read_file("/path/to/large_file.txt")

        self.assertIsInstance(result, FileContentResult)
        self.assertTrue(result.success)
        self.assertEqual(result.content, "chunk1chunk2chunk3")
        mock_get_file_info.assert_called_once_with("/path/to/large_file.txt")
        self.assertEqual(mock_read_chunk.call_count, 3)

    @patch("agentbay.filesystem.filesystem.FileSystem.get_file_info")
    def test_read_file_empty_file(self, mock_get_file_info):
        """
        Test that read_file handles empty files correctly.
        """
        # Mock file info for empty file
        file_info_result = FileInfoResult(
            request_id="request-123",
            success=True,
            file_info={"size": 0, "isDirectory": False},
        )
        mock_get_file_info.return_value = file_info_result

        result = self.fs.read_file("/path/to/empty_file.txt")

        self.assertIsInstance(result, FileContentResult)
        self.assertTrue(result.success)
        self.assertEqual(result.content, "")
        mock_get_file_info.assert_called_once_with("/path/to/empty_file.txt")

    @patch("agentbay.filesystem.filesystem.FileSystem.get_file_info")
    def test_read_file_directory_error(self, mock_get_file_info):
        """
        Test that read_file returns error when path is a directory.
        """
        # Mock file info for directory
        file_info_result = FileInfoResult(
            request_id="request-123",
            success=True,
            file_info={"size": 0, "isDirectory": True},
        )
        mock_get_file_info.return_value = file_info_result

        result = self.fs.read_file("/path/to/directory")

        self.assertIsInstance(result, FileContentResult)
        self.assertFalse(result.success)
        self.assertIn("directory", result.error_message.lower())

    # Test new unified write_file method
    @patch("agentbay.filesystem.filesystem.FileSystem._write_file_chunk")
    def test_write_file_small_content_direct_write(self, mock_write_chunk):
        """
        Test that write_file handles small content efficiently (single chunk).
        """
        mock_write_chunk.return_value = BoolResult(
            request_id="request-123", success=True, data=True
        )

        small_content = "small content"
        result = self.fs.write_file("/path/to/file.txt", small_content)

        self.assertIsInstance(result, BoolResult)
        self.assertTrue(result.success)
        self.assertTrue(result.data)
        mock_write_chunk.assert_called_once_with("/path/to/file.txt", small_content, "overwrite")

    @patch("agentbay.filesystem.filesystem.FileSystem._write_file_chunk")
    def test_write_file_large_content_chunked_write(self, mock_write_chunk):
        """
        Test that write_file handles large content with automatic chunking.
        """
        mock_write_chunk.side_effect = [
            BoolResult(request_id="request-123-1", success=True, data=True),
            BoolResult(request_id="request-123-2", success=True, data=True),
            BoolResult(request_id="request-123-3", success=True, data=True),
        ]

        # Create content larger than default chunk size (50KB)
        large_content = "x" * (150 * 1024)  # 150KB content
        result = self.fs.write_file("/path/to/large_file.txt", large_content)

        self.assertIsInstance(result, BoolResult)
        self.assertTrue(result.success)
        self.assertTrue(result.data)

        # Should be called 3 times (first overwrite, then 2 appends)
        self.assertEqual(mock_write_chunk.call_count, 3)

        # Verify first call is overwrite
        first_call = mock_write_chunk.call_args_list[0]
        self.assertEqual(first_call[0][2], "overwrite")  # mode parameter

        # Verify subsequent calls are append
        for i in range(1, 3):
            call = mock_write_chunk.call_args_list[i]
            self.assertEqual(call[0][2], "append")  # mode parameter

    @patch("agentbay.filesystem.filesystem.FileSystem._write_file_chunk")
    def test_write_file_append_mode_small_content(self, mock_write_chunk):
        """
        Test that write_file respects append mode for small content.
        """
        mock_write_chunk.return_value = BoolResult(
            request_id="request-123", success=True, data=True
        )

        small_content = "append content"
        result = self.fs.write_file("/path/to/file.txt", small_content, "append")

        self.assertIsInstance(result, BoolResult)
        self.assertTrue(result.success)
        mock_write_chunk.assert_called_once_with("/path/to/file.txt", small_content, "append")

    @patch("agentbay.filesystem.filesystem.FileSystem._write_file_chunk")
    def test_write_file_append_mode_large_content(self, mock_write_chunk):
        """
        Test that write_file respects append mode for large content.
        """
        mock_write_chunk.side_effect = [
            BoolResult(request_id="request-123-1", success=True, data=True),
            BoolResult(request_id="request-123-2", success=True, data=True),
        ]

        # Create content larger than default chunk size
        large_content = "x" * (100 * 1024)  # 100KB content
        result = self.fs.write_file("/path/to/large_file.txt", large_content, "append")

        self.assertIsInstance(result, BoolResult)
        self.assertTrue(result.success)

        # Should be called 2 times, first with append mode
        self.assertEqual(mock_write_chunk.call_count, 2)

        # Verify first call uses the specified mode (append)
        first_call = mock_write_chunk.call_args_list[0]
        self.assertEqual(first_call[0][2], "append")  # mode parameter

        # Verify subsequent calls are also append
        second_call = mock_write_chunk.call_args_list[1]
        self.assertEqual(second_call[0][2], "append")  # mode parameter

    # Test error handling
    @patch("agentbay.filesystem.filesystem.FileSystem._write_file_chunk")
    def test_write_file_chunk_error_propagation(self, mock_write_chunk):
        """
        Test that write_file properly propagates errors from chunk operations.
        """
        mock_write_chunk.return_value = BoolResult(
            request_id="request-123",
            success=False,
            error_message="Write failed"
        )

        result = self.fs.write_file("/path/to/file.txt", "content")

        self.assertIsInstance(result, BoolResult)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Write failed")

    @patch("agentbay.filesystem.filesystem.FileSystem.get_file_info")
    def test_read_file_file_info_error_propagation(self, mock_get_file_info):
        """
        Test that read_file properly propagates errors from get_file_info.
        """
        mock_get_file_info.return_value = FileInfoResult(
            request_id="request-123",
            success=False,
            error_message="File not found"
        )

        result = self.fs.read_file("/path/to/nonexistent.txt")

        self.assertIsInstance(result, FileContentResult)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "File not found")

    # Test that old large file methods no longer exist (after refactor)
    def test_old_large_file_methods_removed(self):
        """
        Test that the old read_large_file and write_large_file methods are removed.
        This test should pass after the refactor is complete.
        """
        # These should not exist after refactor
        self.assertFalse(hasattr(self.fs, 'read_large_file'))
        self.assertFalse(hasattr(self.fs, 'write_large_file'))

    # Test default chunk size configuration
    def test_default_chunk_size_configuration(self):
        """
        Test that the default chunk size is properly configured.
        """
        expected_chunk_size = 50 * 1024  # 50KB
        self.assertEqual(self.fs.DEFAULT_CHUNK_SIZE, expected_chunk_size)


if __name__ == "__main__":
    unittest.main()
