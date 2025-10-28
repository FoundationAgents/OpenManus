import os
import unittest
import time
import concurrent.futures

from agentbay import AgentBay
from agentbay.filesystem.filesystem import (
    BoolResult,
    DirectoryListResult,
    FileContentResult,
    FileInfoResult,
    FileSearchResult,
    MultipleFileContentResult,
)
from agentbay.session_params import CreateSessionParams

class TestFileSystemComprehensive(unittest.TestCase):
    """
    FileSystem Comprehensive Tests

    This test suite covers comprehensive file system operations including:
    1. File Basic Operations
    2. File Information Management
    3. Batch File Operations
    4. File Edit and Move Operations
    5. Directory Management
    """

    @classmethod
    def setUpClass(cls):
        """Set up test environment before all tests."""
        # Get API key from environment
        cls.api_key = os.getenv("AGENTBAY_API_KEY")
        if not cls.api_key:
            raise unittest.SkipTest("AGENTBAY_API_KEY environment variable not set")

        # Initialize AgentBay client
        cls.agent_bay = AgentBay(cls.api_key)

        # Create a session
        print("Creating a new session for FileSystem comprehensive testing...")
        params = CreateSessionParams(
            image_id="linux_latest",
        )
        result = cls.agent_bay.create(params)
        if not result.success or not result.session:
            raise unittest.SkipTest("Failed to create session")

        cls.session = result.session
        cls.fs = cls.session.file_system
        print(f"Session created with ID: {cls.session.session_id}")

        # Create base tmp directory
        cls.fs.create_directory("/tmp")

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment after all tests."""
        print("Cleaning up: Deleting the session...")
        if hasattr(cls, "session"):
            try:
                result = cls.agent_bay.delete(cls.session)
                if result.success:
                    print("Session successfully deleted")
                else:
                    print(f"Warning: Error deleting session: {result.error_message}")
            except Exception as e:
                print(f"Warning: Error deleting session: {e}")

    def setUp(self):
        """Set up before each test."""
        # Test constants
        self.test_file_path = "/tmp/test_files.txt"
        self.multiline_file_path = "/tmp/test_multiline.txt"

        # Create 30KB test file with repeated content
        test_content = "hello world!!!\n" * 2000
        write_result = self.fs.write_file(self.test_file_path, test_content, "overwrite")
        self.assertTrue(write_result.success, "Failed to create test file")

    # 1. File Basic Operations Tests
    def test_1_1_file_reading_tests(self):
        """1.1 File Reading Tests - should successfully read file content"""
        result = self.fs.read_file(self.test_file_path)

        self.assertIsInstance(result, FileContentResult)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.request_id)
        self.assertNotEqual(result.request_id, "")
        self.assertIsNotNone(result.content)
        self.assertIn("hello world!!!", result.content)
        self.assertEqual(len(result.content), 30000)

    def test_1_1_file_content_pattern(self):
        """1.1 File Reading Tests - should return correct file content pattern"""
        result = self.fs.read_file(self.test_file_path)

        self.assertTrue(result.success)
        lines = result.content.split('\n')
        for line in lines:
            if line.strip() != "":
                self.assertEqual(line, "hello world!!!")

    def test_1_2_parameterized_file_reading_with_offset_length(self):
        """1.2 Parameterized File Reading Tests - should read specific bytes with offset and length parameters"""
        # Create multi-line test file
        multiline_content = "\n".join([f"Line {i + 1}: This is test content" for i in range(10)])
        write_result = self.fs.write_file(self.multiline_file_path, multiline_content, "overwrite")
        self.assertTrue(write_result.success)

        # Read from 3rd byte, 3 bytes (offset=2, length=3)
        result = self.fs.read_file(self.multiline_file_path, 2, 3)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.request_id)
        self.assertIsNotNone(result.content)
        self.assertLessEqual(len(result.content), 3)

        # Verify content is from 3rd byte
        full_content = self.fs.read_file(self.multiline_file_path)
        expected_content = full_content.content[2:5]  # bytes 2-4 (3 bytes)
        self.assertEqual(result.content, expected_content)

    def test_1_2_read_from_offset_to_end(self):
        """1.2 Parameterized File Reading Tests - should read from offset to end of file"""
        multiline_content = "\n".join([f"Line {i + 1}: This is test content" for i in range(10)])
        write_result = self.fs.write_file(self.multiline_file_path, multiline_content, "overwrite")
        self.assertTrue(write_result.success)

        # Read from 6th byte to end (offset=5, length=0)
        result = self.fs.read_file(self.multiline_file_path, 5, 0)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.request_id)
        self.assertIsNotNone(result.content)

        # Verify reads from 6th byte to end
        full_content = self.fs.read_file(self.multiline_file_path)
        expected_content = full_content.content[5:]  # from 6th byte to end
        self.assertEqual(result.content, expected_content)

    def test_1_2_handle_large_offset_values(self):
        """1.2 Parameterized File Reading Tests - should handle large offset values correctly"""
        multiline_content = "\n".join([f"Line {i + 1}: This is test content" for i in range(10)])
        write_result = self.fs.write_file(self.multiline_file_path, multiline_content, "overwrite")
        self.assertTrue(write_result.success)

        # Test offset greater than file size
        result = self.fs.read_file(self.multiline_file_path, 1000)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.content)
        # Should return empty content since offset exceeds file size

    def test_1_2_handle_zero_length_parameter(self):
        """1.2 Parameterized File Reading Tests - should handle zero length parameter correctly"""
        multiline_content = "\n".join([f"Line {i + 1}: This is test content" for i in range(10)])
        write_result = self.fs.write_file(self.multiline_file_path, multiline_content, "overwrite")
        self.assertTrue(write_result.success)

        # Test length=0 should read from offset to end
        result = self.fs.read_file(self.multiline_file_path, 0, 0)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.content)

        # length=0 should read entire file
        full_content = self.fs.read_file(self.multiline_file_path)
        self.assertEqual(result.content, full_content.content)

    def test_1_3_write_file_with_different_modes(self):
        """1.3 File Writing Tests - should write file with different modes"""
        write_test_file_path = "/tmp/test_write.txt"
        test_content = "Hello, World!"

        # Test overwrite mode
        write_result = self.fs.write_file(write_test_file_path, test_content, "overwrite")
        self.assertTrue(write_result.success)
        self.assertIsNotNone(write_result.request_id)
        self.assertTrue(write_result.data)

        # Verify content
        read_result = self.fs.read_file(write_test_file_path)
        self.assertTrue(read_result.success)
        self.assertEqual(read_result.content, test_content)

        # Test append mode
        append_result = self.fs.write_file(write_test_file_path, "\nAppended content", "append")
        self.assertTrue(append_result.success)

        read_result2 = self.fs.read_file(write_test_file_path)
        self.assertIn(test_content, read_result2.content)
        self.assertIn("Appended content", read_result2.content)

    def test_1_3_validate_write_mode_parameter(self):
        """1.3 File Writing Tests - should validate write mode parameter"""
        write_test_file_path = "/tmp/test_write.txt"
        result = self.fs.write_file(write_test_file_path, "content", "invalid_mode")
        print(f"Write result: {result.__dict__}")
        self.assertFalse(result.success)
        self.assertIn("Invalid", result.error_message)

    def test_1_4_handle_large_file_operations(self):
        """1.4 Large File Tests - should handle large file operations with automatic chunking"""
        large_content = "Large content line. " * 3000
        large_file_path = "/tmp/large_test.txt"

        # Write large file (automatic chunking)
        write_result = self.fs.write_file(large_file_path, large_content)
        self.assertTrue(write_result.success)

        # Read large file (automatic chunking)
        read_result = self.fs.read_file(large_file_path)
        self.assertTrue(read_result.success)
        self.assertEqual(read_result.content, large_content)

    # 2. File Information Management Tests
    def test_2_get_file_info_correctly(self):
        """2. File Information Management - should get file info correctly"""
        info_test_file = "/tmp/info_test.txt"
        write_result = self.fs.write_file(info_test_file, "", "overwrite")
        self.assertTrue(write_result.success)

        result = self.fs.get_file_info(info_test_file)
        print(f"File info result: {result.__dict__}")
        self.assertIsInstance(result, FileInfoResult)
        self.assertTrue(result.success)
        self.assertEqual(result.file_info.get("size"), 0)
        self.assertFalse(result.file_info.get("isDirectory"))

    def test_2_list_directory_contents(self):
        """2. File Information Management - should list directory contents"""
        list_test_dir = "/tmp/list_test"
        self.fs.create_directory(list_test_dir)
        self.fs.write_file(f"{list_test_dir}/file1.txt", "content1", "overwrite")
        self.fs.create_directory(f"{list_test_dir}/subdir1")

        result = self.fs.list_directory(list_test_dir)
        self.assertIsInstance(result, DirectoryListResult)
        self.assertTrue(result.success)
        self.assertGreater(len(result.entries), 0)

    # 3. Batch File Operations Tests
    def test_3_read_multiple_files_correctly(self):
        """3. Batch File Operations - should read multiple files correctly"""
        files = ["/tmp/batch1.txt", "/tmp/batch2.txt", "/tmp/batch3.txt"]
        contents = ["Content 1", "", "Content 3"]

        # Create multiple files
        for i, file_path in enumerate(files):
            self.fs.write_file(file_path, contents[i], "overwrite")

        result = self.fs.read_multiple_files(files)
        self.assertIsInstance(result, MultipleFileContentResult)
        self.assertTrue(result.success)
        self.assertEqual(result.contents[files[0]], contents[0])
        self.assertEqual(result.contents[files[1]], contents[1])
        self.assertEqual(result.contents[files[2]], contents[2])

    def test_3_search_files_correctly(self):
        """3. Batch File Operations - should search files correctly"""
        search_test_dir = "/tmp/search_test"
        self.fs.create_directory(search_test_dir)
        self.fs.write_file(f"{search_test_dir}/test1.txt", "content", "overwrite")
        self.fs.write_file(f"{search_test_dir}/test2.log", "log", "overwrite")

        result1 = self.fs.search_files(search_test_dir, "test1.txt")
        self.assertTrue(result1.success)
        self.assertIsNotNone(result1.matches)

        result2 = self.fs.search_files(search_test_dir, "", ["test2.log"])
        self.assertTrue(result2.success)
        self.assertIsNotNone(result2.matches)

    # 4. File Edit and Move Operations Tests
    def test_4_edit_file_with_find_replace(self):
        """4. File Edit and Move Operations - should edit file with find-replace"""
        edit_path = "/tmp/edit_test.txt"
        initial_content = "This is old1 text with old2 content."
        self.fs.write_file(edit_path, initial_content, "overwrite")

        edits = [
            {"oldText": "old1", "newText": "new1"},
            {"oldText": "old2", "newText": "new2"}
        ]

        result = self.fs.edit_file(edit_path, edits, False)
        self.assertIsInstance(result, BoolResult)
        self.assertTrue(result.success)

        read_result = self.fs.read_file(edit_path)
        self.assertIn("new1", read_result.content)
        self.assertIn("new2", read_result.content)

    def test_4_move_file_correctly(self):
        """4. File Edit and Move Operations - should move file correctly"""
        source_path = "/tmp/move_source.txt"
        dest_path = "/tmp/move_dest.txt"
        content_to_move = "Content to move"

        self.fs.write_file(source_path, content_to_move, "overwrite")

        result = self.fs.move_file(source_path, dest_path)
        self.assertIsInstance(result, BoolResult)
        self.assertTrue(result.success)

        read_result = self.fs.read_file(dest_path)
        self.assertTrue(read_result.success)
        self.assertEqual(read_result.content, content_to_move)

    # 5. Directory Management Tests
    def test_5_create_directory_successfully(self):
        """5. Directory Management - should create directory successfully"""
        dir_path = "/tmp/new_directory"

        result = self.fs.create_directory(dir_path)
        self.assertIsInstance(result, BoolResult)
        self.assertTrue(result.success)

        info_result = self.fs.get_file_info(dir_path)
        self.assertTrue(info_result.success)
        self.assertTrue(info_result.file_info.get("isDirectory"))

    def test_5_create_nested_directories(self):
        """5. Directory Management - should create nested directories"""
        nested_path = "/tmp/level1/level2/level3"

        self.fs.create_directory("/tmp/level1")
        self.fs.create_directory("/tmp/level1/level2")
        result = self.fs.create_directory(nested_path)

        self.assertTrue(result.success)

    # 6. Error Handling Tests
    def test_6_handle_non_existent_file_operations(self):
        """6. Error Handling - should handle non-existent file operations"""
        non_existent_path = "/tmp/non_existent.txt"

        read_result = self.fs.read_file(non_existent_path)
        print(f"Read result: {read_result.__dict__}")
        self.assertFalse(read_result.success)
        self.assertIsNotNone(read_result.error_message)

        info_result = self.fs.get_file_info(non_existent_path)
        print(f"Info result: {info_result.__dict__}")
        self.assertFalse(info_result.success)
        self.assertIsNotNone(info_result.error_message)

    def test_6_handle_invalid_parameters(self):
        """6. Error Handling - should handle invalid parameters"""
        empty_path_result = self.fs.read_file("")
        print(f"Empty path read result: {empty_path_result.__dict__}")
        self.assertFalse(empty_path_result.success)
        self.assertIsNotNone(empty_path_result.error_message)

    # 7. Performance and Boundary Tests
    def test_7_handle_1mb_file_efficiently(self):
        """7. Performance and Boundary Tests - should handle 1MB file efficiently"""
        large_path = "/tmp/1mb_test.txt"
        large_content = "Performance test content line. " * 35000  # ~1MB

        write_start = time.time()
        write_result = self.fs.write_file(large_path, large_content)
        write_time = time.time() - write_start

        self.assertTrue(write_result.success)
        self.assertLess(write_time, 30)  # Should complete within 30 seconds

        read_start = time.time()
        read_result = self.fs.read_file(large_path)
        read_time = time.time() - read_start

        self.assertTrue(read_result.success)
        self.assertEqual(read_result.content, large_content)
        self.assertLess(read_time, 30)

        print(f"Performance: Write={write_time:.2f}s, Read={read_time:.2f}s")

    def test_7_handle_concurrent_operations(self):
        """7. Performance and Boundary Tests - should handle concurrent operations"""
        def write_file_task(index):
            file_path = f"/tmp/concurrent_{index}.txt"
            content = f"Concurrent content {index}"
            return self.fs.write_file(file_path, content, "overwrite")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(write_file_task, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        for result in results:
            self.assertTrue(result.success)
            self.assertIsNotNone(result.request_id)

    # 8. Path Length Boundary Tests
    def test_8_handle_normal_path_lengths(self):
        """8. Path Length Boundary Tests - should handle normal path lengths"""
        normal_path = "/tmp/normal_path_test.txt"

        write_result = self.fs.write_file(normal_path, "content", "overwrite")
        self.assertTrue(write_result.success)

        read_result = self.fs.read_file(normal_path)
        self.assertTrue(read_result.success)
        self.assertEqual(read_result.content, "content")

    def test_8_handle_long_paths_within_limits(self):
        """8. Path Length Boundary Tests - should handle long paths within limits"""
        long_dir_name = "long_directory_name_" + "x" * 50
        long_file_name = "long_file_name_" + "y" * 50 + ".txt"
        long_path = f"/tmp/{long_dir_name}/{long_file_name}"

        self.fs.create_directory(f"/tmp/{long_dir_name}")

        write_result = self.fs.write_file(long_path, "long path content", "overwrite")
        if write_result.success:
            read_result = self.fs.read_file(long_path)
            self.assertTrue(read_result.success)
            self.assertEqual(read_result.content, "long path content")

    def test_8_handle_paths_with_special_characters(self):
        """8. Path Length Boundary Tests - should handle paths with special characters"""
        space_path = "/tmp/file with spaces.txt"

        write_result = self.fs.write_file(space_path, "space content", "overwrite")
        if write_result.success:
            read_result = self.fs.read_file(space_path)
            self.assertTrue(read_result.success)
            self.assertEqual(read_result.content, "space content")

    # 9. File Content Boundary Tests
    def test_9_handle_empty_file_content(self):
        """9. File Content Boundary Tests - should handle empty file content"""
        empty_path = "/tmp/empty_test.txt"

        write_result = self.fs.write_file(empty_path, "", "overwrite")
        self.assertTrue(write_result.success)

        read_result = self.fs.read_file(empty_path)
        self.assertTrue(read_result.success)
        self.assertEqual(read_result.content, "")

        info_result = self.fs.get_file_info(empty_path)
        self.assertTrue(info_result.success)
        self.assertEqual(info_result.file_info.get("size"), 0)

    def test_9_handle_single_long_line_content(self):
        """9. File Content Boundary Tests - should handle single long line content"""
        long_line_path = "/tmp/long_line_test.txt"
        long_line = "x" * 10000  # 10KB single line

        write_result = self.fs.write_file(long_line_path, long_line, "overwrite")
        self.assertTrue(write_result.success)

        read_result = self.fs.read_file(long_line_path)
        self.assertTrue(read_result.success)
        self.assertEqual(read_result.content, long_line)
        self.assertEqual(len(read_result.content), 10000)

    def test_9_handle_multiline_content_with_special_characters(self):
        """9. File Content Boundary Tests - should handle multiline content with special characters"""
        special_path = "/tmp/special_chars_test.txt"
        special_content = """Line 1: Normal text
Line 2: Special chars !@#$%^&*()
Line 3: Unicode: Hello World 🌍
Line 4: Quotes: "double" 'single'
Line 5: Newlines and tabs:
\t"""

        write_result = self.fs.write_file(special_path, special_content, "overwrite")
        self.assertTrue(write_result.success)

        read_result = self.fs.read_file(special_path)
        self.assertTrue(read_result.success)
        self.assertEqual(read_result.content, special_content)
        self.assertIn("Hello World", read_result.content)
        self.assertIn("🌍", read_result.content)

    # 10. Extreme Scenario Tests
    def test_10_handle_multiple_files_in_directory(self):
        """10. Extreme Scenario Tests - should handle multiple files in directory"""
        many_files_dir = "/tmp/many_files_test"
        self.fs.create_directory(many_files_dir)

        def create_file_task(index):
            file_path = f"{many_files_dir}/file_{index}.txt"
            content = f"Content {index}"
            return self.fs.write_file(file_path, content, "overwrite")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_file_task, i) for i in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        for result in results:
            self.assertTrue(result.success)

        list_result = self.fs.list_directory(many_files_dir)
        self.assertTrue(list_result.success)
        self.assertEqual(len(list_result.entries), 20)

    def test_10_handle_deep_directory_nesting(self):
        """10. Extreme Scenario Tests - should handle deep directory nesting"""
        current_path = "/tmp"
        for i in range(1, 11):
            current_path += f"/level{i}"
            result = self.fs.create_directory(current_path)
            self.assertTrue(result.success)

        deep_file_path = f"{current_path}/deep_file.txt"
        write_result = self.fs.write_file(deep_file_path, "Deep content", "overwrite")
        self.assertTrue(write_result.success)

        read_result = self.fs.read_file(deep_file_path)
        self.assertTrue(read_result.success)
        self.assertEqual(read_result.content, "Deep content")

    # 11. Data Integrity Tests
    def test_11_maintain_data_integrity_across_operations(self):
        """11. Data Integrity Tests - should maintain data integrity across operations"""
        integrity_path = "/tmp/integrity_test.txt"
        original_content = "Original integrity test content with special chars: äöüß"

        # Write -> Read -> Edit -> Read -> Move -> Read
        self.fs.write_file(integrity_path, original_content, "overwrite")

        read_result = self.fs.read_file(integrity_path)
        self.assertEqual(read_result.content, original_content)

        edits = [{"oldText": "Original", "newText": "Modified"}]
        self.fs.edit_file(integrity_path, edits, False)

        read_result = self.fs.read_file(integrity_path)
        self.assertIn("Modified", read_result.content)
        self.assertIn("äöüß", read_result.content)

        moved_path = "/tmp/integrity_moved.txt"
        self.fs.move_file(integrity_path, moved_path)

        final_result = self.fs.read_file(moved_path)
        self.assertTrue(final_result.success)
        self.assertIn("Modified", final_result.content)
        self.assertIn("äöüß", final_result.content)

        print("Data integrity test completed successfully")

if __name__ == "__main__":
    unittest.main()
