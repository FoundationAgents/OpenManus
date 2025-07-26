import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.manus import Manus
from app.schema import Message, Role, Function as FunctionCall, ToolCall
from app.tool.sandbox_python_executor import SandboxPythonExecutor # Corrected import
from app.tool.python_execute import PythonExecute # Corrected import
from app.tool.ask_human import AskHuman # Corrected import
from app.tool import Terminate # This one is fine
from app.config import config # For workspace path, if needed for file operations
# Removed incorrect import pytest_asyncio

# Ensure the test workspace directory exists if any file operations are done by tools
# For now, we mostly mock them.
# if not os.path.exists(config.workspace_root):
#     os.makedirs(config.workspace_root)

@pytest.fixture # Reverted to @pytest.fixture
async def manus_agent():
    """Fixture to create a Manus agent instance for testing."""
    _agent = None  # Define agent in a scope accessible by finally
    # Mock MCPClients and its methods to avoid actual server connections
    with patch('app.agent.manus.MCPClients', new_callable=MagicMock) as MockMCPClients:
        mock_mcp_instance = MockMCPClients.return_value
        mock_mcp_instance.connect_sse = AsyncMock()
        mock_mcp_instance.connect_stdio = AsyncMock()
        mock_mcp_instance.disconnect = AsyncMock()
        mock_mcp_instance.tools = [] # No MCP tools for these tests

        # Patch SANDBOX_CLIENT to avoid actual sandbox operations
        with patch('app.agent.manus.SANDBOX_CLIENT', new_callable=MagicMock) as MockSandboxClient:
            MockSandboxClient.run_command = AsyncMock(return_value={"exit_code": 0, "stdout": "", "stderr": ""})
            MockSandboxClient.read_file = AsyncMock(return_value="")
            MockSandboxClient.cleanup = AsyncMock()

            # Patch ChecklistManager to avoid file system dependencies
            with patch('app.agent.manus.ChecklistManager', new_callable=MagicMock) as MockChecklistManager:
                mock_checklist_instance = MockChecklistManager.return_value
                mock_checklist_instance._load_checklist = AsyncMock()
                mock_checklist_instance.get_tasks = MagicMock(return_value=[]) # No tasks by default
                mock_checklist_instance.are_all_tasks_complete = MagicMock(return_value=False)

                # Create and initialize Manus instance
                # Need to ensure LLM is also mocked if not done by default by Manus structure
                with patch('app.llm.LLM', new_callable=MagicMock) as MockLLM:
                    mock_llm_instance = MockLLM.return_value
                    mock_llm_instance.ask = AsyncMock(return_value="No specific LLM response needed for this flow")

                    _agent = await Manus.create(name="TestManus", system_prompt="Test System Prompt", next_step_prompt="Test Next Step")

                    # Mock the LLM's ask method to control tool calls
                    _agent.llm.ask = AsyncMock()

                    # Mock tools that might be called internally but aren't the focus
                    if _agent.available_tools.get_tool(Terminate.name):
                        _agent.available_tools.get_tool(Terminate.name).execute = AsyncMock(return_value={"status": "terminated"})

                    # Ensure critical tools for fallback are present and mockable if necessary
                    # PythonExecute and AskHuman are usually added by default.
                    # SandboxPythonExecutor is also added.
                    # We will mock their 'execute' methods directly in tests where needed.

    # Return the agent instance instead of yielding
    try:
        yield _agent
    finally:
        if _agent:
            await _agent.cleanup()


@pytest.mark.asyncio
async def test_sandbox_fallback_user_says_yes(manus_agent: Manus):
    """
    Test the sandbox fallback logic when SandboxPythonExecutor fails
    and the user consents to fallback via AskHuman.
    """
    agent = manus_agent # The fixture now directly provides the resolved agent
    initial_user_prompt = "Run this risky code"
    agent.memory.add_message(Message.user_message(initial_user_prompt))

    # 1. LLM decides to use SandboxPythonExecutor
    sandbox_tool_call_id = "sandbox_call_123"
    sandbox_args = {"code": "print('risky stuff')"}
    llm_response_for_sandbox = Message.assistant_message(
        content="Okay, I will run this code in the sandbox.",
        tool_calls=[
            ToolCall(id=sandbox_tool_call_id, function=FunctionCall(name=SandboxPythonExecutor.name, arguments=json.dumps(sandbox_args)))
        ]
    )
    agent.memory.add_message(llm_response_for_sandbox)
    agent.tool_calls = llm_response_for_sandbox.tool_calls # Manually set planned tool_calls for think()

    # 2. Mock SandboxPythonExecutor to fail with exit_code -2
    # We need to mock the 'execute' method of the *instance* of the tool
    sandbox_tool_instance = agent.available_tools.get_tool(SandboxPythonExecutor.name)
    sandbox_tool_instance.execute = AsyncMock(return_value={"exit_code": -2, "stdout": "", "stderr": "Sandbox creation failed"})

    # Call think once - it should execute SandboxPythonExecutor, which fails.
    # Then, it should detect the failure and plan an AskHuman call.
    await agent.think()

    # Verify SandboxPythonExecutor was called
    sandbox_tool_instance.execute.assert_called_once_with(**sandbox_args)

    # Verify AskHuman is planned
    assert len(agent.tool_calls) == 1
    ask_human_call = agent.tool_calls[0]
    assert ask_human_call.function.name == AskHuman.name
    ask_human_args = json.loads(ask_human_call.function.arguments)
    assert "A execução segura no sandbox falhou" in ask_human_args["inquire"]

    # Add the Assistant message that planned AskHuman (as agent.think() would)
    # And the Tool message for the AskHuman call itself (simulating ToolCallAgent.execute_tool)
    agent.memory.add_message(Message.assistant_message(content="Asking user about fallback", tool_calls=agent.tool_calls))

    # 3. Mock AskHuman to return "sim"
    ask_human_tool_instance = agent.available_tools.get_tool(AskHuman.name)
    ask_human_tool_instance.execute = AsyncMock(return_value="sim") # User says "sim"

    # Simulate the Tool message for AskHuman's result, and the User's "sim" message
    agent.memory.add_message(Message(role=Role.TOOL, name=AskHuman.name, tool_call_id=ask_human_call.id, content="sim"))
    agent.memory.add_message(Message.user_message("sim"))

    # Mock PythonExecute to verify it's called
    python_execute_tool_instance = agent.available_tools.get_tool(PythonExecute.name)
    python_execute_tool_instance.execute = AsyncMock(return_value={"exit_code": 0, "stdout": "Fallback success!", "stderr": ""})

    # Reset agent.tool_calls before the next think, as the AskHuman call is "done"
    agent.tool_calls = []

    # Call think again - it should now process the "sim" response and plan PythonExecute
    await agent.think()

    # Verify PythonExecute is planned and then called
    assert len(agent.tool_calls) == 1, f"Expected 1 tool call, got {len(agent.tool_calls)}: {agent.tool_calls}"
    python_execute_call = agent.tool_calls[0]
    assert python_execute_call.function.name == PythonExecute.name

    # Simulate execution of PythonExecute
    # In a real scenario, ToolCallAgent.execute_tool would do this.
    # For this test, we can directly check if it would be called with correct args.
    expected_fallback_args = {"code": sandbox_args["code"], "timeout": 120} # Assuming default timeout

    # The arguments in the planned tool_call should match
    assert json.loads(python_execute_call.function.arguments) == expected_fallback_args

    # To be absolutely sure it would be called by the loop, we can simulate one more step of execution
    # This part is more about testing the ToolCallAgent loop, but helps confirm manus's behavior
    agent.memory.add_message(Message.assistant_message(content="Fallback to PythonExecute", tool_calls=agent.tool_calls)) # LLM plans PythonExecute

    # This would be the actual execution by ToolCallAgent.execute_tool
    # result = await python_execute_tool_instance.execute(**json.loads(python_execute_call.function.arguments))
    # agent.memory.add_message(Message(role=Role.TOOL, name=PythonExecute.name, tool_call_id=python_execute_call.id, content=str(result)))

    # For this unit test, asserting that python_execute_tool_instance.execute was called correctly
    # after the second `think()` (which plans it) is the primary goal for `manus.think()` behavior.
    # The actual call would happen in the agent loop. Here we check the plan.
    # So, let's mock the LLM to not interfere and run think() again to see if it *would* execute.
    # This is a bit convoluted. A better way is to check the state *after* the think() that plans PythonExecute.

    # The `agent.think()` call above *planned* the PythonExecute.
    # We've already asserted the plan is correct.
    # Now, let's ensure the state variables for fallback are cleared.
    assert agent._pending_fallback_tool_call is None
    assert agent._last_ask_human_for_fallback_id is None
    assert agent._fallback_attempted_for_tool_call_id == sandbox_tool_call_id

    # To directly test the execution part of the if block, we'd need to manually call python_execute_tool_instance.execute
    # or rely on the `think` method to eventually cause its execution if no other tools are planned.
    # The current test setup primarily tests if `think` correctly *plans* the fallback.
    # Let's ensure PythonExecute's execute mock was indeed called by some part of the agent logic
    # if we were to simulate the execution loop more fully.
    # For now, checking the plan is sufficient for this unit test's scope.
    # If we were to make agent.think() also execute the tool if it's the *only* one,
    # then python_execute_tool_instance.execute.assert_called_once_with(**expected_fallback_args) would be here.
    # However, think() only plans. The ToolCallAgent loop executes.

    # Final check: The memory should show the sequence of events.
    # User -> Assistant (Sandbox) -> Tool (Sandbox Fail) -> Assistant (AskHuman) -> Tool (AskHuman "sim") -> User ("sim") -> Assistant (PythonExecute)
    assert agent.memory.messages[-1].role == Role.ASSISTANT
    assert agent.memory.messages[-1].role == Role.ASSISTANT
    # The final assistant message in this flow, after user says "sim", should be the one planning PythonExecute
    assert agent.memory.messages[-1].content == f"Ok, tentando executar o código diretamente usando '{PythonExecute.name}'. Lembre-se dos riscos de segurança."
    # Tool calls should not be in this particular message but planned for next turn by think().
    # The previous think() call set self.tool_calls.
    # The message we are checking here is the one *before* PythonExecute is planned by the last `think()` call.
    # Let's re-verify the sequence.
    # User -> LLM plans Sandbox -> Tool (Sandbox Fail) -> LLM plans AskHuman -> Tool (AskHuman result "sim") + User msg "sim" -> Manus.think() processes "sim"
    # After processing "sim", Manus.think() itself adds an assistant message and plans PythonExecute.

    # The state *after* the think() that processes "sim":
    # agent.memory.messages should have the "Ok, tentando executar..." message.
    # agent.tool_calls should have the PythonExecute call.

    # The message added by the fallback logic when user says "sim"
    sim_response_assistant_message = next(m for m in reversed(agent.memory.messages) if m.role == Role.ASSISTANT and "Ok, tentando executar" in m.content)
    assert sim_response_assistant_message is not None

    # The tool call planned by the think() that processed "sim"
    assert agent.tool_calls is not None
    assert len(agent.tool_calls) == 1
    assert agent.tool_calls[0].function.name == PythonExecute.name
    assert json.loads(agent.tool_calls[0].function.arguments) == expected_fallback_args

    # logger.info("test_sandbox_fallback_user_says_yes completed successfully.")


@pytest.mark.asyncio
async def test_sandbox_fallback_user_says_no(manus_agent: Manus):
    """
    Test the sandbox fallback logic when SandboxPythonExecutor fails
    and the user responds "não" to the fallback request.
    """
    agent = manus_agent
    initial_user_prompt = "Run this other risky code"
    agent.memory.add_message(Message.user_message(initial_user_prompt))

    # 1. LLM decides to use SandboxPythonExecutor
    sandbox_tool_call_id = "sandbox_call_456"
    sandbox_args = {"code": "print('very risky stuff')"}
    llm_response_for_sandbox = Message.assistant_message(
        content="Okay, I will run this code in the sandbox.",
        tool_calls=[
            ToolCall(id=sandbox_tool_call_id, function=FunctionCall(name=SandboxPythonExecutor.name, arguments=json.dumps(sandbox_args)))
        ]
    )
    agent.memory.add_message(llm_response_for_sandbox)
    agent.tool_calls = llm_response_for_sandbox.tool_calls

    # 2. Mock SandboxPythonExecutor to fail
    sandbox_tool_instance = agent.available_tools.get_tool(SandboxPythonExecutor.name)
    sandbox_tool_instance.execute = AsyncMock(return_value={"exit_code": -2, "stdout": "", "stderr": "Sandbox creation failed again"})

    await agent.think() # Executes SandboxPythonExecutor (fails), then plans AskHuman

    # Verify AskHuman is planned
    assert len(agent.tool_calls) == 1
    ask_human_call = agent.tool_calls[0]
    assert ask_human_call.function.name == AskHuman.name

    # Add Assistant message that planned AskHuman & Tool message for AskHuman's execution
    agent.memory.add_message(Message.assistant_message(content="Asking user about fallback again", tool_calls=agent.tool_calls))

    # 3. Mock AskHuman to return "não"
    ask_human_tool_instance = agent.available_tools.get_tool(AskHuman.name)
    ask_human_tool_instance.execute = AsyncMock(return_value="não")

    # Simulate Tool message for AskHuman's result, and User's "não" message
    agent.memory.add_message(Message(role=Role.TOOL, name=AskHuman.name, tool_call_id=ask_human_call.id, content="não"))
    agent.memory.add_message(Message.user_message("não"))

    # Mock PythonExecute to ensure it's NOT called
    python_execute_tool_instance = agent.available_tools.get_tool(PythonExecute.name)
    python_execute_tool_instance.execute = AsyncMock()

    agent.tool_calls = [] # Reset from AskHuman

    # Call think again - it should process the "não" response
    # LLM should be invoked after this to decide next step, no automatic PythonExecute.
    # For this test, we expect agent.tool_calls to be empty after this think(),
    # as the fallback logic itself doesn't plan further tools on "no".
    # The LLM would then be called by the main agent loop.

    # To simulate that no further specific tool is called by *this* part of logic,
    # we can mock the LLM to return no tool calls.
    agent.llm.ask = AsyncMock(return_value=Message.assistant_message(content="Okay, cancelling.")) # Simulate LLM deciding to do nothing else for now

    await agent.think()

    # Verify PythonExecute was NOT called
    python_execute_tool_instance.execute.assert_not_called()

    # Verify no tools are planned by the fallback logic itself.
    # The `think` method, after processing "no", returns True, and the outer loop would call LLM.
    # If LLM (mocked above) returns no tools, then self.tool_calls should be empty.
    assert not agent.tool_calls, f"Expected no tool calls, but got: {agent.tool_calls}"

    # Check that the agent acknowledged the "não"
    # The message "Entendido. A execução do script foi cancelada..." is added by manus.think directly.
    assert agent.memory.messages[-2].role == Role.ASSISTANT # The message before LLM's "Okay, cancelling."
    assert "Entendido. A execução do script foi cancelada" in agent.memory.messages[-2].content

    # Check fallback state variables
    assert agent._pending_fallback_tool_call is None
    assert agent._last_ask_human_for_fallback_id is None
    assert agent._fallback_attempted_for_tool_call_id == sandbox_tool_call_id

    # logger.info("test_sandbox_fallback_user_says_no completed successfully.")


@pytest.mark.asyncio
async def test_sandbox_fallback_invalid_args_for_python_execute(manus_agent: Manus):
    """
    Test fallback when user says "sim" but original call was file_path,
    which PythonExecute cannot directly handle.
    """
    agent = manus_agent
    agent.memory.add_message(Message.user_message("Run this script file."))

    sandbox_tool_call_id = "sandbox_file_call_789"
    # Original call uses file_path
    sandbox_args = {"file_path": "/workspace/somescript.py", "timeout": 60}
    llm_response_for_sandbox = Message.assistant_message(
        content="Okay, I will run this script file in the sandbox.",
        tool_calls=[
            ToolCall(id=sandbox_tool_call_id, function=FunctionCall(name=SandboxPythonExecutor.name, arguments=json.dumps(sandbox_args)))
        ]
    )
    agent.memory.add_message(llm_response_for_sandbox)
    agent.tool_calls = llm_response_for_sandbox.tool_calls

    sandbox_tool_instance = agent.available_tools.get_tool(SandboxPythonExecutor.name)
    sandbox_tool_instance.execute = AsyncMock(return_value={"exit_code": -2, "stdout": "", "stderr": "Sandbox creation failed for file exec"})

    await agent.think() # Sandbox fails, AskHuman planned

    assert len(agent.tool_calls) == 1
    ask_human_call = agent.tool_calls[0]
    assert ask_human_call.function.name == AskHuman.name

    agent.memory.add_message(Message.assistant_message(content="Asking about file fallback", tool_calls=agent.tool_calls))

    ask_human_tool_instance = agent.available_tools.get_tool(AskHuman.name)
    ask_human_tool_instance.execute = AsyncMock(return_value="sim")

    agent.memory.add_message(Message(role=Role.TOOL, name=AskHuman.name, tool_call_id=ask_human_call.id, content="sim"))
    agent.memory.add_message(Message.user_message("sim"))

    python_execute_tool_instance = agent.available_tools.get_tool(PythonExecute.name)
    python_execute_tool_instance.execute = AsyncMock() # Should NOT be called

    agent.tool_calls = []
    agent.llm.ask = AsyncMock(return_value=Message.assistant_message(content="LLM acknowledges file path issue."))

    await agent.think() # Processes "sim" for file_path case

    python_execute_tool_instance.execute.assert_not_called()

    # Agent should inform user about the issue with file_path
    # This message is added directly by the think method in this scenario
    assert agent.memory.messages[-2].role == Role.ASSISTANT
    assert "A execução direta alternativa (`PythonExecute`) requer o conteúdo do código, não o caminho do arquivo." in agent.memory.messages[-2].content

    # No tools should be planned by the fallback logic itself
    assert not agent.tool_calls, f"Expected no tool calls, but got: {agent.tool_calls}"

    assert agent._pending_fallback_tool_call is None
    assert agent._last_ask_human_for_fallback_id is None
    assert agent._fallback_attempted_for_tool_call_id == sandbox_tool_call_id
    # logger.info("test_sandbox_fallback_invalid_args_for_python_execute completed successfully.")


@pytest.mark.asyncio
async def test_sandbox_fallback_unrecognized_response(manus_agent: Manus):
    """
    Test fallback when user gives an unrecognized response to the fallback prompt.
    It should be handled as a "no".
    """
    agent = manus_agent
    agent.memory.add_message(Message.user_message("Run code with unclear fallback intent."))

    sandbox_tool_call_id = "sandbox_unclear_resp_001"
    sandbox_args = {"code": "print('unclear code')"}
    llm_response_for_sandbox = Message.assistant_message(
        content="Okay, I will run this unclear code in the sandbox.",
        tool_calls=[
            ToolCall(id=sandbox_tool_call_id, function=FunctionCall(name=SandboxPythonExecutor.name, arguments=json.dumps(sandbox_args)))
        ]
    )
    agent.memory.add_message(llm_response_for_sandbox)
    agent.tool_calls = llm_response_for_sandbox.tool_calls

    sandbox_tool_instance = agent.available_tools.get_tool(SandboxPythonExecutor.name)
    sandbox_tool_instance.execute = AsyncMock(return_value={"exit_code": -2, "stdout": "", "stderr": "Sandbox creation failed for unclear response test"})

    await agent.think() # Sandbox fails, AskHuman planned

    assert len(agent.tool_calls) == 1
    ask_human_call = agent.tool_calls[0]
    assert ask_human_call.function.name == AskHuman.name

    agent.memory.add_message(Message.assistant_message(content="Asking about unclear fallback", tool_calls=agent.tool_calls))

    ask_human_tool_instance = agent.available_tools.get_tool(AskHuman.name)
    unrecognized_response = "I'm not sure, maybe?"
    ask_human_tool_instance.execute = AsyncMock(return_value=unrecognized_response)

    agent.memory.add_message(Message(role=Role.TOOL, name=AskHuman.name, tool_call_id=ask_human_call.id, content=unrecognized_response))
    agent.memory.add_message(Message.user_message(unrecognized_response))

    python_execute_tool_instance = agent.available_tools.get_tool(PythonExecute.name)
    python_execute_tool_instance.execute = AsyncMock() # Should NOT be called

    agent.tool_calls = []
    # Mock LLM to show it would be called after this interaction
    agent.llm.ask = AsyncMock(return_value=Message.assistant_message(content="LLM acknowledging unrecognized response and cancellation."))

    await agent.think() # Processes unrecognized response

    python_execute_tool_instance.execute.assert_not_called()

    # Agent should inform user that the response was not recognized and it's treated as "no"
    # This message is added directly by the think method
    assert agent.memory.messages[-2].role == Role.ASSISTANT # Message before LLM's ack
    expected_message_snippet = f"Resposta '{unrecognized_response}' não reconhecida. Assumindo 'não' para a execução direta. A execução do script foi cancelada."
    assert expected_message_snippet in agent.memory.messages[-2].content

    # No tools should be planned by the fallback logic itself
    assert not agent.tool_calls, f"Expected no tool calls, but got: {agent.tool_calls}"

    assert agent._pending_fallback_tool_call is None
    assert agent._last_ask_human_for_fallback_id is None
    assert agent._fallback_attempted_for_tool_call_id == sandbox_tool_call_id
    # logger.info("test_sandbox_fallback_unrecognized_response completed successfully.")


# Remaining suggested tests (can be added if time permits or as follow-up):
# test_no_fallback_if_sandbox_succeeds
# test_no_fallback_if_other_tool_fails
# test_no_fallback_if_sandbox_fails_with_other_error_code

if __name__ == "__main__":
    # This allows running the test directly using `python tests/agent/test_manus_fallback.py`
    # For that, you might need to adjust python paths or run with `python -m pytest tests/agent/test_manus_fallback.py`
    pytest.main()
