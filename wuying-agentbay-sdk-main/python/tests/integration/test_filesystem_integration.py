import os
import unittest

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


class TestFileSystemIntegration(unittest.TestCase):

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
        print("Creating a new session for FileSystem testing...")
        params = CreateSessionParams(
            image_id="linux_latest",
        )
        result = cls.agent_bay.create(params)
        if not result.success or not result.session:
            raise unittest.SkipTest("Failed to create session")

        cls.session = result.session
        cls.fs = cls.session.file_system
        print(f"Session created with ID: {cls.session.session_id}")

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

    def test_read_file(self):
        """
        Test reading a file.
        """
        test_content = "This is a test file content for ReadFile test."
        test_file_path = "/tmp/test_read.txt"

        # Write the test file
        write_result = self.fs.write_file(test_file_path, test_content, "overwrite")
        self.assertTrue(write_result.success)

        # Read the file
        result = self.fs.read_file(test_file_path)
        self.assertIsInstance(result, FileContentResult)
        self.assertTrue(result.success)
        self.assertEqual(result.content, test_content)

    def test_write_file(self):
        """
        Test writing to a file.
        """
        test_content = "This is a test file content for WriteFile test."
        test_file_path = "/tmp/test_write.txt"

        # Write the file
        result = self.fs.write_file(test_file_path, test_content, "overwrite")
        self.assertIsInstance(result, BoolResult)
        self.assertTrue(result.success)

        # Verify the file content
        read_result = self.fs.read_file(test_file_path)
        self.assertTrue(read_result.success)
        self.assertEqual(read_result.content, test_content)

    def test_create_directory(self):
        """
        Test creating a directory.
        """
        test_dir_path = "/tmp/test_directory"

        # Create the directory
        result = self.fs.create_directory(test_dir_path)
        self.assertIsInstance(result, BoolResult)
        self.assertTrue(result.success)

        # Verify the directory exists
        list_result = self.fs.list_directory("/tmp/")
        self.assertTrue(list_result.success)
        entry_names = [entry["name"] for entry in list_result.entries]
        self.assertIn("test_directory", entry_names)

    def test_edit_file(self):
        """
        Test editing a file.
        """
        initial_content = "This is the original content.\nLine to be replaced.\nThis is the final line."
        test_file_path = "/tmp/test_edit.txt"

        # Write the initial file
        write_result = self.fs.write_file(test_file_path, initial_content, "overwrite")
        self.assertTrue(write_result.success)

        # Edit the file
        edits = [
            {
                "oldText": "Line to be replaced.",
                "newText": "This line has been edited.",
            }
        ]
        result = self.fs.edit_file(test_file_path, edits, False)
        self.assertIsInstance(result, BoolResult)
        self.assertTrue(result.success)

        # Verify the file content
        expected_content = "This is the original content.\nThis line has been edited.\nThis is the final line."
        read_result = self.fs.read_file(test_file_path)
        self.assertTrue(read_result.success)
        self.assertEqual(read_result.content, expected_content)

    def test_get_file_info(self):
        """
        Test getting file information.
        """
        test_content = "This is a test file for GetFileInfo."
        test_file_path = "/tmp/test_info.txt"

        # Write the test file
        write_result = self.fs.write_file(test_file_path, test_content, "overwrite")
        self.assertTrue(write_result.success)

        # Get file info
        result = self.fs.get_file_info(test_file_path)
        self.assertIsInstance(result, FileInfoResult)
        self.assertTrue(result.success)

        file_info = result.file_info
        self.assertFalse(file_info["isDirectory"])
        size = int(file_info["size"])
        self.assertTrue(size > 0, f"File size should be positive, got {size}")

    def test_list_directory(self):
        """
        Test listing a directory.
        """
        result = self.fs.list_directory("/tmp/")
        self.assertIsInstance(result, DirectoryListResult)
        self.assertTrue(result.success)

        entries = result.entries
        self.assertGreater(len(entries), 0)
        self.assertIn("name", entries[0])
        self.assertIn("isDirectory", entries[0])

    def test_move_file(self):
        """
        Test moving a file.
        """
        test_content = "This is a test file for MoveFile."
        source_file_path = "/tmp/test_source.txt"
        dest_file_path = "/tmp/test_destination.txt"

        # Write the source file
        write_result = self.fs.write_file(source_file_path, test_content, "overwrite")
        self.assertTrue(write_result.success)

        # Move the file
        result = self.fs.move_file(source_file_path, dest_file_path)
        self.assertIsInstance(result, BoolResult)
        self.assertTrue(result.success)

        # Verify the destination file content
        read_result = self.fs.read_file(dest_file_path)
        self.assertTrue(read_result.success)
        self.assertEqual(read_result.content, test_content)

        # Verify the source file no longer exists
        get_file_info_result = self.fs.get_file_info(source_file_path)
        self.assertFalse(get_file_info_result.success)

    def test_read_multiple_files(self):
        """
        Test reading multiple files.
        """
        file1_content = "This is test file 1 content."
        file2_content = "This is test file 2 content."
        test_file1_path = "/tmp/test_file1.txt"
        test_file2_path = "/tmp/test_file2.txt"

        # Write the test files
        self.fs.write_file(test_file1_path, file1_content, "overwrite")
        self.fs.write_file(test_file2_path, file2_content, "overwrite")

        # Read multiple files
        result = self.fs.read_multiple_files([test_file1_path, test_file2_path])
        self.assertIsInstance(result, MultipleFileContentResult)
        self.assertTrue(result.success)

        contents = result.contents
        self.assertEqual(contents[test_file1_path], file1_content)
        self.assertEqual(contents[test_file2_path], file2_content)

    def test_search_files(self):
        """
        Test searching for files.
        """
        test_subdir_path = "/tmp/search_test_dir"
        create_dir_result = self.fs.create_directory(test_subdir_path)
        self.assertTrue(create_dir_result.success)

        file1_content = "This is test file 1 content."
        file2_content = "This is test file 2 content."
        file3_content = "This is test file 3 content."
        search_file1_path = f"{test_subdir_path}/SEARCHABLE_PATTERN_file1.txt"
        search_file2_path = f"{test_subdir_path}/regular_file2.txt"
        search_file3_path = f"{test_subdir_path}/SEARCHABLE_PATTERN_file3.txt"

        # Write the test files
        self.fs.write_file(search_file1_path, file1_content, "overwrite")
        self.fs.write_file(search_file2_path, file2_content, "overwrite")
        self.fs.write_file(search_file3_path, file3_content, "overwrite")

        # Search for files
        search_pattern = "SEARCHABLE_PATTERN"
        exclude_patterns = ["ignored_pattern"]
        result = self.fs.search_files(
            test_subdir_path, search_pattern, exclude_patterns
        )
        self.assertIsInstance(result, FileSearchResult)
        self.assertTrue(result.success)

        matches = result.matches
        self.assertEqual(len(matches), 2)
        self.assertTrue(any(search_file1_path in match for match in matches))
        self.assertTrue(any(search_file3_path in match for match in matches))

    def test_write_and_read_large_file(self):
        """
        Test writing and reading a large file using automatic chunking.
        """
        # Generate approximately 150KB of test content
        line_content = "This is a line of test content for large file testing. It contains enough characters to test the chunking functionality.\n"
        large_content = line_content * 3000  # About 150KB
        test_file_path = "/tmp/test_large_file.txt"

        print(f"Generated test content size: {len(large_content)} bytes")

        # Test 1: Write large file (automatic chunking)
        print("Test 1: Writing large file with automatic chunking...")
        result = self.fs.write_file(test_file_path, large_content)
        self.assertIsInstance(result, BoolResult)
        self.assertTrue(result.success)
        print("Test 1: Large file write successful")

        # Test 2: Read large file (automatic chunking)
        print("Test 2: Reading large file with automatic chunking...")
        result = self.fs.read_file(test_file_path)
        self.assertIsInstance(result, FileContentResult)
        self.assertTrue(result.success)

        # Verify content
        read_content = result.content
        print(
            f"Test 2: File read successful, content length: {len(read_content)} bytes"
        )
        self.assertEqual(len(read_content), len(large_content))
        self.assertEqual(read_content, large_content)
        print("Test 2: File content verification successful")

        # Test 3: Write another large file
        test_file_path2 = "/tmp/test_large_file2.txt"
        print("Test 3: Writing another large file...")

        result = self.fs.write_file(test_file_path2, large_content)
        self.assertIsInstance(result, BoolResult)
        self.assertTrue(result.success)
        print("Test 3: Second large file write successful")

        # Test 4: Read the second large file
        print("Test 4: Reading the second large file...")
        result = self.fs.read_file(test_file_path2)
        self.assertIsInstance(result, FileContentResult)
        self.assertTrue(result.success)

        # Verify content
        read_content2 = result.content
        print(
            f"Test 4: File read successful, content length: {len(read_content2)} bytes"
        )
        self.assertEqual(len(read_content2), len(large_content))
        self.assertEqual(read_content2, large_content)
        print("Test 4: Second file content verification successful")

        # Test 5: Re-read the first file to ensure consistency
        print("Test 5: Re-reading the first file to ensure consistency...")
        result = self.fs.read_file(test_file_path)
        self.assertIsInstance(result, FileContentResult)
        self.assertTrue(result.success)

        # Verify content
        cross_test_content = result.content
        print(
            f"Test 5: Re-read successful, content length: {len(cross_test_content)} bytes"
        )
        self.assertEqual(len(cross_test_content), len(large_content))
        self.assertEqual(cross_test_content, large_content)
        print("Test 5: Consistency verification successful")

    def test_write_and_read_small_file(self):
        """
        Test writing and reading a small file (should use direct write, not chunking).
        """
        # Generate a small file content (10KB)
        small_content = "x" * (10 * 1024)
        test_file_path = "/tmp/test_small_file.txt"

        # Use write_file method to write small file
        result = self.fs.write_file(test_file_path, small_content)
        self.assertIsInstance(result, BoolResult)
        self.assertTrue(result.success)

        # Read and verify content
        result = self.fs.read_file(test_file_path)
        self.assertTrue(result.success)
        self.assertEqual(result.content, small_content)


if __name__ == "__main__":
    unittest.main()
