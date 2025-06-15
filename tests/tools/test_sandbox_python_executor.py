import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import os
import tempfile
import shutil

from app.tool.sandbox_python_executor import SandboxPythonExecutor
from app.sandbox.core.exceptions import SandboxTimeoutError
from app.config import config as app_config


class TestSandboxPythonExecutor(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Create a temporary directory to serve as the workspace for some tests
        self.test_dir = tempfile.mkdtemp()
        self.original_workspace_root = app_config.workspace_root
        app_config.workspace_root = self.test_dir

    def tearDown(self):
        # Restore original workspace_root and remove the temporary directory
        app_config.workspace_root = self.original_workspace_root
        shutil.rmtree(self.test_dir)

    @patch('app.tool.sandbox_python_executor.SANDBOX_CLIENT', new_callable=AsyncMock)
    async def test_successful_execution(self, mock_sandbox_client):
        """Test successful code execution."""
        tool = SandboxPythonExecutor()
        test_code = "print('Hello World')"
        test_timeout = 5

        # Configure mocks
        mock_sandbox_client.write_file.return_value = None  # write_file is async but returns None
        mock_sandbox_client.run_command.return_value = {
            "exit_code": 0,
            "stdout": "Hello World\n", # Python print adds a newline
            "stderr": ""
        }
        # Mock cleanup command
        mock_sandbox_client.run_command.side_effect = [
            {
                "exit_code": 0,
                "stdout": "Hello World\n",
                "stderr": ""
            }, # For actual command
            {"exit_code": 0, "stdout": "", "stderr": ""}  # For cleanup command rm -f
        ]


        expected_result = {
            "exit_code": 0,
            "stdout": "Hello World\n",
            "stderr": ""
        }

        result = await tool.execute(code=test_code, timeout=test_timeout)

        self.assertEqual(result, expected_result)
        mock_sandbox_client.write_file.assert_called_once()
        # Path in write_file call is dynamic (uuid), so check content and part of path
        args, kwargs = mock_sandbox_client.write_file.call_args
        self.assertTrue(args[0].startswith("temp_script_"))
        self.assertTrue(args[0].endswith(".py"))
        self.assertEqual(args[1], test_code)
        
        # Check run_command was called twice (once for script, once for cleanup)
        self.assertEqual(mock_sandbox_client.run_command.call_count, 2)
        
        # Check first call (script execution)
        args_run, kwargs_run = mock_sandbox_client.run_command.call_args_list[0]
        self.assertTrue(args_run[0].startswith("python temp_script_"))
        self.assertEqual(kwargs_run['timeout'], test_timeout)

        # Check second call (cleanup)
        args_cleanup, kwargs_cleanup = mock_sandbox_client.run_command.call_args_list[1]
        self.assertTrue(args_cleanup[0].startswith("rm -f temp_script_"))
        self.assertEqual(kwargs_cleanup['timeout'], 2)


    @patch('app.tool.sandbox_python_executor.SANDBOX_CLIENT', new_callable=AsyncMock)
    async def test_execution_with_stderr_and_exit_code(self, mock_sandbox_client):
        """Test execution that results in stderr and a non-zero exit code."""
        tool = SandboxPythonExecutor()
        test_code = "import sys; sys.stderr.write('Error: Something went wrong'); sys.exit(1)"
        test_timeout = 5

        mock_sandbox_client.write_file.return_value = None
        mock_sandbox_client.run_command.side_effect = [
            {
                "exit_code": 1,
                "stdout": "",
                "stderr": "Error: Something went wrong"
            },
            {"exit_code": 0, "stdout": "", "stderr": ""} # Cleanup
        ]
        

        expected_result = {
            "exit_code": 1,
            "stdout": "",
            "stderr": "Error: Something went wrong"
        }

        result = await tool.execute(code=test_code, timeout=test_timeout)

        self.assertEqual(result, expected_result)
        mock_sandbox_client.write_file.assert_called_once()
        self.assertEqual(mock_sandbox_client.run_command.call_count, 2)


    @patch('app.tool.sandbox_python_executor.SANDBOX_CLIENT', new_callable=AsyncMock)
    async def test_execution_timeout(self, mock_sandbox_client):
        """Test code execution that times out."""
        tool = SandboxPythonExecutor()
        test_code = "while True: pass"
        test_timeout = 1 # Short timeout for testing

        mock_sandbox_client.write_file.return_value = None
        # run_command for the script raises SandboxTimeoutError
        # The second call for cleanup should still be mocked if it's expected to run
        mock_sandbox_client.run_command.side_effect = [
            SandboxTimeoutError("Execution timed out"),
            {"exit_code": 0, "stdout": "", "stderr": ""} # Mock for cleanup
        ]

        expected_stderr = f"Execution timed out after {test_timeout} seconds.\nExecution timed out"
        expected_result = {
            "exit_code": 124, # Standard timeout exit code
            "stdout": "",
            "stderr": expected_stderr
        }

        result = await tool.execute(code=test_code, timeout=test_timeout)

        self.assertEqual(result, expected_result)
        mock_sandbox_client.write_file.assert_called_once()
        # run_command for the script itself should be called
        # The cleanup command might also be called depending on implementation details
        # (e.g. if timeout happens in `tool.execute` after `run_command` returns, or inside `run_command`)
        # Based on current `SandboxPythonExecutor`, cleanup is attempted in a finally block.
        self.assertEqual(mock_sandbox_client.run_command.call_count, 2)


    @patch('app.tool.sandbox_python_executor.SANDBOX_CLIENT', new_callable=AsyncMock)
    async def test_sandbox_write_file_error(self, mock_sandbox_client):
        """Test scenario where writing the script to sandbox fails."""
        tool = SandboxPythonExecutor()
        test_code = "print('This will not run')"
        
        mock_sandbox_client.write_file.side_effect = RuntimeError("Failed to write script to sandbox")
        # run_command should not be called if write_file fails.
        # However, cleanup rm -f might still be called.
        mock_sandbox_client.run_command.return_value = {"exit_code": 0, "stdout": "", "stderr": ""} # For cleanup

        expected_result = {
            "exit_code": 1, # General error code defined in the tool for this
            "stdout": "",
            "stderr": "Sandbox execution error: Failed to write script to sandbox"
        }
        # The tool's execute method has a broad try-except RuntimeError for sandbox operations
        # and sets exit_code to 1 for such errors.

        result = await tool.execute(code=test_code, timeout=5)

        self.assertEqual(result, expected_result)
        mock_sandbox_client.write_file.assert_called_once()
        # run_command for script execution should not be called.
        # run_command for cleanup *is* called due to the finally block in execute()
        mock_sandbox_client.run_command.assert_called_once() 


    @patch('app.tool.sandbox_python_executor.SANDBOX_CLIENT', new_callable=AsyncMock)
    async def test_sandbox_run_command_generic_error(self, mock_sandbox_client):
        """Test scenario where run_command fails with a generic RuntimeError."""
        tool = SandboxPythonExecutor()
        test_code = "print('Hello')"

        mock_sandbox_client.write_file.return_value = None
        # run_command for the script raises a generic RuntimeError
        # The second call for cleanup should still be mocked.
        mock_sandbox_client.run_command.side_effect = [
            RuntimeError("Generic sandbox failure"),
            {"exit_code": 0, "stdout": "", "stderr": ""} # For cleanup
        ]
        
        expected_result = {
            "exit_code": 1, # General error code
            "stdout": "",
            "stderr": "Sandbox execution error: Generic sandbox failure"
        }

        result = await tool.execute(code=test_code, timeout=5)

        self.assertEqual(result, expected_result)
        mock_sandbox_client.write_file.assert_called_once()
        self.assertEqual(mock_sandbox_client.run_command.call_count, 2)

    @patch('app.tool.sandbox_python_executor.SANDBOX_CLIENT', new_callable=AsyncMock)
    async def test_execute_file_path_non_existent(self, mock_sandbox_client):
        """Test execution with file_path when the file does not exist on host."""
        tool = SandboxPythonExecutor()
        non_existent_file = os.path.join(app_config.workspace_root, "non_existent_script.py")

        # Simulate sandbox being ready to avoid create() calls if not needed for path validation phase
        mock_sandbox_client.sandbox = MagicMock()
        mock_sandbox_client.sandbox.container = True # Indicates sandbox is 'running' for is_running()
        mock_sandbox_client.is_running.return_value = True


        expected_result = {
            "exit_code": -4, # As per current tool logic for host path errors
            "stdout": "",
            "stderr": f"Error: File not found on host: {non_existent_file}"
        }

        result = await tool.execute(file_path=non_existent_file, timeout=5)

        self.assertEqual(result, expected_result)
        mock_sandbox_client.is_running.assert_called_once() # ensure_sandbox_ready checks this
        mock_sandbox_client.create.assert_not_called() # Should not try to create if is_running is true
        mock_sandbox_client.copy_to.assert_not_called()
        # run_command for python execution should not be called.
        # It might be called for mkdir if ensure_sandbox_ready includes it and sandbox is not 'ready'
        # but here we mock sandbox as ready.
        # Check that run_command was not called with "python ..."
        python_execution_called = False
        for call_item in mock_sandbox_client.run_command.call_args_list:
            if call_item[0][0].startswith("python "):
                python_execution_called = True
                break
        self.assertFalse(python_execution_called, "Python execution should not be attempted for non-existent host file.")


    @patch('app.tool.sandbox_python_executor.SANDBOX_CLIENT', new_callable=AsyncMock)
    async def test_execute_file_path_outside_workspace(self, mock_sandbox_client):
        """Test execution with file_path that is outside the configured workspace."""
        tool = SandboxPythonExecutor()
        
        # Create a temporary file *outside* the configured workspace_root (self.test_dir)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp_file:
            tmp_file_path = tmp_file.name
            tmp_file.write("print('This should not run')")
        
        self.addCleanup(os.remove, tmp_file_path) # Ensure cleanup

        # Simulate sandbox being ready
        mock_sandbox_client.sandbox = MagicMock()
        mock_sandbox_client.sandbox.container = True 
        mock_sandbox_client.is_running.return_value = True

        expected_error_msg_part = "is outside the allowed workspace"
        expected_result = {
            "exit_code": -4, # Host path validation error
            "stdout": "",
            # The exact message might vary slightly based on how os.path.abspath and os.path.commonpath behave
            "stderr": f"Error: File path {os.path.abspath(tmp_file_path)} {expected_error_msg_part}" 
        }

        result = await tool.execute(file_path=tmp_file_path, timeout=5)

        # Construct expected error message based on actual abspath, as it might differ (e.g. /var/ vs /private/var on macOS)
        abs_tmp_file_path = os.path.abspath(tmp_file_path)
        expected_stderr = f"Error: File path {abs_tmp_file_path} is outside the allowed workspace {app_config.workspace_root}"
        
        self.assertEqual(result["exit_code"], expected_result["exit_code"])
        self.assertEqual(result["stdout"], expected_result["stdout"])
        self.assertTrue(expected_error_msg_part in result["stderr"])
        self.assertTrue(abs_tmp_file_path in result["stderr"])
        self.assertTrue(app_config.workspace_root in result["stderr"])


        mock_sandbox_client.is_running.assert_called_once()
        mock_sandbox_client.create.assert_not_called()
        mock_sandbox_client.copy_to.assert_not_called()
        
        python_execution_called = False
        for call_item in mock_sandbox_client.run_command.call_args_list:
            if call_item[0][0].startswith("python "):
                python_execution_called = True
                break
        self.assertFalse(python_execution_called, "Python execution should not be attempted for file outside workspace.")


if __name__ == '__main__':
    unittest.main()
```
