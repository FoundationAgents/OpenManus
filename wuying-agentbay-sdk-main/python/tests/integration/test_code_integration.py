import os
import unittest

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams


class TestCodeIntegration(unittest.TestCase):
    """Integration tests for Code module."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_key = os.getenv("AGENTBAY_API_KEY")
        if not self.api_key:
            self.skipTest("AGENTBAY_API_KEY environment variable not set")

        self.agent_bay = AgentBay(api_key=self.api_key)
        params = CreateSessionParams(image_id='code_latest')
        # Use code_latest image for code execution tests
        session_result = self.agent_bay.create(params)
        self.session = session_result.session
        self.code = self.session.code

    def tearDown(self):
        """Clean up test fixtures."""
        if hasattr(self, "session"):
            self.session.delete()

    def test_run_code_python_success(self):
        """Test successful Python code execution."""
        code = '''
print("Hello, world!")
x = 1 + 1
print(x)
'''
        result = self.code.run_code(code, "python")

        print(f"Python code execution result: {result}")

        # Should have success, result, and request_id
        self.assertTrue(result.success)
        self.assertIsNotNone(result.result)
        self.assertIsNotNone(result.request_id)
        self.assertIn("Hello, world!", result.result)
        self.assertIn("2", result.result)

    def test_run_code_javascript_success(self):
        """Test successful JavaScript code execution."""
        code = '''
console.log("Hello, world!");
const x = 1 + 1;
console.log(x);
'''
        result = self.code.run_code(code, "javascript")

        print(f"JavaScript code execution result: {result}")

        # Should have success, result, and request_id
        self.assertTrue(result.success)
        self.assertIsNotNone(result.result)
        self.assertIsNotNone(result.request_id)
        self.assertIn("Hello, world!", result.result)
        self.assertIn("2", result.result)

    def test_run_code_unsupported_language(self):
        """Test code execution with unsupported language."""
        code = "print('Hello, world!')"
        language = "ruby"

        result = self.code.run_code(code, language)

        # Should return failure for unsupported language
        self.assertFalse(result.success)
        self.assertIn("Unsupported language", result.error_message)

    def test_3_2_complex_code_with_file_operations(self):
        """3.2 Complex Code with File Operations - should execute complex code with file operations"""
        # Step 1: Session creation
        session_params1 = CreateSessionParams(image_id='code_latest')
        session_params2 = CreateSessionParams(image_id='code_latest')

        session_result1 = self.agent_bay.create(session_params1)
        session_result2 = self.agent_bay.create(session_params2)

        self.assertTrue(session_result1.success)
        self.assertTrue(session_result2.success)

        session1 = session_result1.session
        session2 = session_result2.session

        code1 = session1.code
        code2 = session2.code

        # Step 7: Complex code test with file operations
        python_file_code = '''
import os
import json

# Create a test file
with open('/tmp/python_test.txt', 'w') as f:
    f.write('Python file operation test')

# Read the file
with open('/tmp/python_test.txt', 'r') as f:
    content = f.read()

result = {"operation": "file_write_read", "content": content, "file_exists": os.path.exists('/tmp/python_test.txt')}
print(json.dumps(result))
'''.strip()

        js_file_code = '''
const fs = require('fs');

// Create a test file
fs.writeFileSync('/tmp/js_test.txt', 'JavaScript file operation test');

// Read the file
const content = fs.readFileSync('/tmp/js_test.txt', 'utf8');

const result = {
  operation: "file_write_read",
  content: content,
  file_exists: fs.existsSync('/tmp/js_test.txt')
};
console.log(JSON.stringify(result));
'''.strip()

        python_file_result = code1.run_code(python_file_code, 'python')
        js_file_result = code2.run_code(js_file_code, 'javascript')

        self.assertTrue(python_file_result.success)
        self.assertTrue(js_file_result.success)

        self.assertIn('Python file operation test', python_file_result.result)
        self.assertIn('JavaScript file operation test', js_file_result.result)


    def test_3_2_code_execution_error_handling(self):
        """3.2 Code Execution Error Handling - should handle code execution errors gracefully"""
        # Step 1: Session creation
        session_params = CreateSessionParams(image_id='code_latest')

        session_result = self.agent_bay.create(session_params)
        self.assertTrue(session_result.success)
        session = session_result.session

        code = session.code

        # Test Python code with syntax error
        bad_python_code = '''
print("Hello"
# Missing closing parenthesis
'''.strip()

        bad_result = code.run_code(bad_python_code, 'python')
        self.assertFalse(bad_result.success)
        self.assertIsNotNone(bad_result.error_message)

        # Test code with runtime error
        runtime_error_code = '''
undefined_variable = nonexistent_variable + 1
print(undefined_variable)
'''.strip()

        runtime_result = code.run_code(runtime_error_code, 'python')
        self.assertFalse(runtime_result.success)
        self.assertIn('NameError', runtime_result.error_message)

if __name__ == "__main__":
    unittest.main()
