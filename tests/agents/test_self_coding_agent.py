import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

from app.agent.self_coding_agent import SelfCodingAgent, AgentState
from app.llm.llm_client import LLMClient
from app.memory.base import Message, MessageRole
from app.tool.sandbox_python_executor import SandboxPythonExecutor
from app.config import AgentSettings, LLMSettings


class TestSelfCodingAgent(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Basic LLM settings for initialization, can be overridden by mocks
        self.llm_settings = LLMSettings(
            provider="openai", 
            api_key="test_key", 
            model="gpt-3.5-turbo"
        )
        self.agent_settings = AgentSettings(llm_settings=self.llm_settings)

    async def test_successful_first_attempt(self):
        agent = SelfCodingAgent()
        # It's important to mock the llm and sandbox_executor_tool on the instance
        agent.llm = AsyncMock(spec=LLMClient)
        agent.sandbox_executor_tool = AsyncMock(spec=SandboxPythonExecutor)

        # Mock LLM response for initial code generation
        agent.llm.chat_completion_async.return_value = Message(
            role=MessageRole.ASSISTANT, 
            content='```python\nprint("Hello World")\n```'
        )
        # Mock Sandbox execution result for successful execution
        agent.sandbox_executor_tool.execute.return_value = {
            "stdout": "Hello World", "stderr": "", "exit_code": 0
        }

        task_description = "Print Hello World"
        # Pass config to ensure llm is set up if not already mocked (though here it is)
        result = await agent.run(request=task_description, config=self.agent_settings)

        self.assertEqual(agent.state, AgentState.FINISHED)
        self.assertEqual(agent.current_correction_attempts, 0)
        self.assertIn("Code executed successfully.", result["response"])
        self.assertEqual(result["status"], AgentState.FINISHED.value)
        
        # Verify LLM was called once for initial generation
        agent.llm.chat_completion_async.assert_called_once() 
        # Verify Sandbox was called once
        agent.sandbox_executor_tool.execute.assert_called_once_with(
            code='print("Hello World")', timeout=agent.default_execution_timeout # Checks if default_timeout is used
        )

    async def test_correction_succeeds(self):
        agent = SelfCodingAgent()
        agent.llm = AsyncMock(spec=LLMClient)
        agent.sandbox_executor_tool = AsyncMock(spec=SandboxPythonExecutor)

        # Mock LLM responses: first faulty, then corrected
        agent.llm.chat_completion_async.side_effect = [
            Message(role=MessageRole.ASSISTANT, content='```python\nprint(unknown_var)\n```'), # Initial faulty code
            Message(role=MessageRole.ASSISTANT, content='```python\nprint("Corrected")\n```')    # Corrected code
        ]
        # Mock Sandbox execution results: first error, then success
        agent.sandbox_executor_tool.execute.side_effect = [
            {"stdout": "", "stderr": "NameError: name 'unknown_var' is not defined", "exit_code": 1}, # Execution of faulty code
            {"stdout": "Corrected", "stderr": "", "exit_code": 0}                                   # Execution of corrected code
        ]

        task_description = "Test correction mechanism"
        result = await agent.run(request=task_description, config=self.agent_settings)

        self.assertEqual(agent.state, AgentState.FINISHED)
        self.assertEqual(agent.current_correction_attempts, 1) # One correction attempt was made
        self.assertIn("Code executed successfully.", result["response"])
        self.assertEqual(result["status"], AgentState.FINISHED.value)

        self.assertEqual(agent.llm.chat_completion_async.call_count, 2) # Initial + 1 correction
        self.assertEqual(agent.sandbox_executor_tool.execute.call_count, 2)
        
        # Check sandbox calls arguments
        first_sandbox_call_args = agent.sandbox_executor_tool.execute.call_args_list[0]
        second_sandbox_call_args = agent.sandbox_executor_tool.execute.call_args_list[1]

        self.assertEqual(first_sandbox_call_args[1]['code'], 'print(unknown_var)')
        self.assertEqual(second_sandbox_call_args[1]['code'], 'print("Corrected")')


    async def test_max_correction_attempts_reached(self):
        # Configure agent instance specifically for this test
        agent = SelfCodingAgent(max_correction_attempts=2) 
        agent.llm = AsyncMock(spec=LLMClient)
        agent.sandbox_executor_tool = AsyncMock(spec=SandboxPythonExecutor)

        # Mock LLM to always return faulty code for all generation/correction attempts
        faulty_code_message = Message(role=MessageRole.ASSISTANT, content='```python\nprint(always_fails)\n```')
        agent.llm.chat_completion_async.return_value = faulty_code_message
        
        # Mock Sandbox to always return an error
        error_execution_result = {"stdout": "", "stderr": "Error", "exit_code": 1}
        agent.sandbox_executor_tool.execute.return_value = error_execution_result

        task_description = "Test max correction attempts"
        result = await agent.run(request=task_description, config=self.agent_settings)

        self.assertEqual(agent.state, AgentState.ERROR)
        self.assertEqual(agent.current_correction_attempts, 2) # Max attempts reached
        self.assertIn(f"Code execution failed after {agent.max_correction_attempts} attempts.", result["response"])
        self.assertEqual(result["status"], AgentState.ERROR.value)

        # LLM called for initial generation + 2 correction attempts (total 3)
        self.assertEqual(agent.llm.chat_completion_async.call_count, 1 + agent.max_correction_attempts)
        # Sandbox called for initial attempt + 2 correction attempts (total 3)
        self.assertEqual(agent.sandbox_executor_tool.execute.call_count, 1 + agent.max_correction_attempts)


    async def test_execution_timeout_handling(self):
        # Configure agent instance with specific timeout and fewer attempts for this test
        agent = SelfCodingAgent(max_correction_attempts=1, default_execution_timeout=5)
        agent.llm = AsyncMock(spec=LLMClient)
        agent.sandbox_executor_tool = AsyncMock(spec=SandboxPythonExecutor)

        # LLM returns code that would conceptually time out
        timeout_simulating_code = 'import time\ntime.sleep(10)' # The actual sleep won't run due to mock
        agent.llm.chat_completion_async.return_value = Message(
            role=MessageRole.ASSISTANT, 
            content=f'```python\n{timeout_simulating_code}\n```'
        )
        
        # Sandbox mock to simulate a timeout scenario for both attempts
        timeout_execution_result = {
            "stdout": "", 
            "stderr": f"Execution timed out after {agent.default_execution_timeout} seconds", 
            "exit_code": 124 # Standard exit code for timeout by `timeout` command
        }
        agent.sandbox_executor_tool.execute.return_value = timeout_execution_result
        
        task_description = "Test execution timeout"
        result = await agent.run(request=task_description, config=self.agent_settings)

        self.assertEqual(agent.state, AgentState.ERROR)
        # Initial attempt -> timeout -> current_correction_attempts becomes 1.
        # Since max_correction_attempts is 1, it fails after this.
        self.assertEqual(agent.current_correction_attempts, 1) 
        self.assertIn(f"Code execution failed after {agent.max_correction_attempts} attempts.", result["response"])
        # Check if the specific timeout message from the sandbox is in the agent's memory
        timeout_message_in_memory = False
        for msg in agent.memory.messages:
            if msg.role == MessageRole.SYSTEM and f"Execution timed out after {agent.default_execution_timeout} seconds" in msg.content:
                timeout_message_in_memory = True
                break
        self.assertTrue(timeout_message_in_memory, "Timeout message not found in agent memory")
        self.assertEqual(result["status"], AgentState.ERROR.value)

        # LLM called for initial generation + 1 correction attempt
        self.assertEqual(agent.llm.chat_completion_async.call_count, 1 + agent.max_correction_attempts)
        # Sandbox called for initial attempt + 1 correction attempt
        self.assertEqual(agent.sandbox_executor_tool.execute.call_count, 1 + agent.max_correction_attempts)
        
        # Check the timeout value passed to execute in all calls
        for call_args in agent.sandbox_executor_tool.execute.call_args_list:
            # call_args is a tuple (args, kwargs) or (kwargs) if no positional args.
            # We expect execute(code="...", timeout=...)
            self.assertEqual(call_args.kwargs['timeout'], 5)


if __name__ == '__main__':
    unittest.main()
