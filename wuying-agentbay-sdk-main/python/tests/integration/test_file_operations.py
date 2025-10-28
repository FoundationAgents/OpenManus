import os
import unittest
import time

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

class TestFileOperations(unittest.TestCase):
    """
    File Operations Integration Tests

    This test suite covers file operations functionality including:
    1. File System CRUD Operations
    2. Directory creation and listing
    3. File writing, reading, editing
    4. Large file operations
    5. File moving and deletion
    6. Edge cases and special conditions
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

        # Create a session for testing
        print("Creating a new session for File operations testing...")
        session_params = CreateSessionParams()
        session_params.image_id = 'linux_latest'

        result = cls.agent_bay.create(session_params)
        if not result.success or not result.session:
            raise unittest.SkipTest("Failed to create session")

        cls.session = result.session
        print(f"Session created with ID: {cls.session.get_session_id()}")

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
        pass

    def test_file_system_crud_operations_workflow(self):
        """File System CRUD Operations - should perform complete file system operations workflow"""
        # Step 3: File system retrieval
        file_system = self.session.file_system
        self.assertIsNotNone(file_system)

        # Step 4: Directory creation
        create_dir_result = file_system.create_directory('/tmp/user')
        self.assertTrue(create_dir_result.success)

        # Step 5: Directory listing
        list_result = file_system.list_directory('/tmp')
        self.assertTrue(list_result.success)
        self.assertIsNotNone(list_result.entries)
        self.assertIsInstance(list_result.entries, list)
        self.assertGreater(len(list_result.entries), 0)
        print(f'List directory result: {list_result}')

        for entry in list_result.entries:
            print(f'Entry: {entry}, Is Directory: {entry.get("isDirectory", False)}')
            if entry.get('name') == 'user':
                self.assertTrue(entry.get('isDirectory', False))

        user_dir = next((entry for entry in list_result.entries if entry.get('name') == 'user'), None)
        self.assertIsNotNone(user_dir)
        self.assertTrue(user_dir.get('isDirectory', False))

        # Step 6: File writing
        test_content = 'hello world!!!'
        write_result = file_system.write_file('/tmp/user/test.txt', test_content, 'overwrite')
        self.assertTrue(write_result.success)

        # Step 7: File reading
        read_result = file_system.read_file('/tmp/user/test.txt')
        self.assertTrue(read_result.success)
        self.assertEqual(read_result.content, test_content)

        # Step 8: File editing
        edits = [{
            'oldText': 'hello world!!!',
            'newText': 'This line has been edited.'
        }]
        edit_result = file_system.edit_file('/tmp/user/test.txt', edits)
        self.assertTrue(edit_result.success)

        # Verify edit
        edited_result = file_system.read_file('/tmp/user/test.txt')
        self.assertTrue(edited_result.success)
        self.assertEqual(edited_result.content, 'This line has been edited.')

        # Step 9: File info retrieval
        file_info_result = file_system.get_file_info('/tmp/user/test.txt')
        self.assertTrue(file_info_result.success)
        print(f'File info: {file_info_result.file_info}')
        self.assertIsNotNone(file_info_result.file_info)
        self.assertGreater(file_info_result.file_info.get('size', 0), 0)

        # Step 10: Large file writing (62KB, automatic chunking)
        large_content = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. ' * 1134  # Approximately 62KB
        self.assertGreater(len(large_content), 60000)

        write_large_result = file_system.write_file('/tmp/user/large_context.txt', large_content)
        print(f'Write large file result: {write_large_result}')
        self.assertTrue(write_large_result.success)

        # Step 11: Large file reading (automatic chunking)
        large_read_result = file_system.read_file('/tmp/user/large_context.txt')
        self.assertTrue(large_read_result.success)
        self.assertEqual(large_read_result.content, large_content)
        self.assertGreater(len(large_read_result.content), 60000)

        # Step 12: File moving
        move_result = file_system.move_file('/tmp/user/test.txt', '/tmp/test.txt')
        self.assertTrue(move_result.success)

        # Verify move operation
        source_read_result = file_system.read_file('/tmp/user/test.txt')
        self.assertFalse(source_read_result.success)

        moved_read_result = file_system.read_file('/tmp/test.txt')
        self.assertTrue(moved_read_result.success)
        self.assertEqual(moved_read_result.content, 'This line has been edited.')

        # Step 13: Multiple files reading
        multiple_files = ['/tmp/user/large_context.txt', '/tmp/test.txt']
        multiple_results = file_system.read_multiple_files(multiple_files)
        self.assertTrue(multiple_results.success)
        self.assertIsNotNone(multiple_results.contents)
        self.assertIsInstance(multiple_results.contents, dict)
        self.assertEqual(len(multiple_results.contents), 2)

        # Step 14: Command executor retrieval
        command = self.session.command
        self.assertIsNotNone(command)

        # Step 15: File deletion via command
        delete_result = command.execute_command('rm /tmp/test.txt')
        self.assertTrue(delete_result.success)

        # Step 16: File search verification
        search_results = file_system.search_files('/tmp', 'test.txt')
        print(f'Search results: {search_results}')
        self.assertTrue(search_results.success)

        # Verify test.txt is not in results
        deleted_file = next((file for file in search_results.matches if 'test.txt' in file), None)
        self.assertIsNone(deleted_file)

        # Verify large_context.txt is still there
        search_large_results = file_system.search_files('/tmp', 'large_context.txt')
        large_file = next((file for file in search_large_results.matches if 'large_context.txt' in file), None)
        print(f'Large file search result: {large_file}')
        self.assertIsNotNone(large_file)
        self.assertIn('large_context.txt', large_file)

    def test_file_system_edge_cases_and_special_conditions(self):
        """Edge Cases and Special Conditions - should handle edge cases and special conditions"""
        file_system = self.session.file_system

        # Ensure directory exists
        create_dir_result = file_system.create_directory('/tmp/user')
        self.assertTrue(create_dir_result.success)

        # Edge case: Empty file creation and reading
        write_empty_result = file_system.write_file('/tmp/user/empty.txt', '', 'overwrite')
        print(f'Write empty file result: {write_empty_result}')
        self.assertTrue(write_empty_result.success)

        empty_read_result = file_system.read_file('/tmp/user/empty.txt')
        self.assertTrue(empty_read_result.success)
        self.assertEqual(empty_read_result.content, '')

        # Edge case: File with special characters in name
        special_file_name = '/tmp/user/特殊文件名-test@#$.txt'
        special_content = 'Content with 中文 and special chars: !@#$%^&*()'

        write_special_result = file_system.write_file(special_file_name, special_content, 'overwrite')
        self.assertTrue(write_special_result.success)

        special_read_result = file_system.read_file(special_file_name)
        self.assertTrue(special_read_result.success)
        self.assertEqual(special_read_result.content, special_content)

        # Edge case: Deep directory structure
        create_deep_dir_result = file_system.create_directory('/tmp/user/deep/nested/structure')
        self.assertTrue(create_deep_dir_result.success)

        write_deep_result = file_system.write_file('/tmp/user/deep/nested/structure/deep.txt', 'deep content', 'overwrite')
        self.assertTrue(write_deep_result.success)

if __name__ == "__main__":
    unittest.main()
