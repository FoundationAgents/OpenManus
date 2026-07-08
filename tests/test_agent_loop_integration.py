"""Integration tests for ToolCallAgent end-to-end loop with mock LLM responses.

Tests the full ReAct step() cycle, phase transitions, nudge mechanisms,
auto-termination after repeated no-tool turns, and tool retries.
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.agent.base import Task
from app.agent.toolcall import ToolCallAgent
from app.schema import AgentPhase, AgentState, Function, ToolCall


class MockLLMResponse:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class TestAgentLoopIntegration:
    @pytest.fixture
    def task(self):
        return Task(id="test_task_1")

    @pytest.fixture
    def agent(self):
        return ToolCallAgent(name="test_agent")

    @pytest.mark.asyncio
    async def test_full_step_cycle_to_terminate(self, agent, task):
        """Test a normal tool call step followed by termination."""
        # Turn 1: model calls a tool (e.g. bash)
        tc1 = ToolCall(
            id="call_1",
            function=Function(name="bash", arguments='{"command": "echo hello"}'),
        )
        # Turn 2: model calls terminate
        tc2 = ToolCall(
            id="call_2",
            function=Function(
                name="terminate",
                arguments='{"status": "success", "summary": "All done!"}',
            ),
        )

        mock_ask = AsyncMock(
            side_effect=[
                MockLLMResponse(content="Running command...", tool_calls=[tc1]),
                MockLLMResponse(content="Finishing up...", tool_calls=[tc2]),
            ]
        )

        with patch.object(agent.llm, "ask_tool", mock_ask), \
             patch.object(agent.llm, "format_messages", return_value=[]), \
             patch.object(agent.llm, "count_message_tokens", return_value=100):

            # Step 1: PLAN -> ACT -> OBSERVE
            obs1 = await agent.step(task)
            assert agent.phase == AgentPhase.OBSERVE
            assert agent.state == AgentState.IDLE

            # Step 2: PLAN -> ACT -> OBSERVE -> DONE (due to terminate tool)
            obs2 = await agent.step(task)
            assert agent.state == AgentState.FINISHED

    @pytest.mark.asyncio
    async def test_text_only_nudge_then_terminate(self, agent, task):
        """Test that a text-only response nudges the model instead of finishing."""
        tc_term = ToolCall(
            id="call_term",
            function=Function(
                name="terminate",
                arguments='{"status": "success", "summary": "Finished after nudge"}',
            ),
        )

        mock_ask = AsyncMock(
            side_effect=[
                MockLLMResponse(content="I am thinking about what to do next."),
                MockLLMResponse(content="OK terminating now.", tool_calls=[tc_term]),
            ]
        )

        with patch.object(agent.llm, "ask_tool", mock_ask), \
             patch.object(agent.llm, "format_messages", return_value=[]), \
             patch.object(agent.llm, "count_message_tokens", return_value=100):

            # Step 1: Model returns text only. Agent should nudge and NOT finish.
            obs1 = await agent.step(task)
            assert agent.state != AgentState.FINISHED
            assert agent._consecutive_no_tool_responses == 1
            # Check that the nudge message was added to memory
            last_msg = agent.memory.messages[-1]
            assert last_msg.role == "user"
            assert "You MUST either call a tool" in last_msg.content

            # Step 2: Model calls terminate after receiving the nudge.
            obs2 = await agent.step(task)
            assert agent.state == AgentState.FINISHED

    @pytest.mark.asyncio
    async def test_force_terminate_on_repeated_no_tool_responses(self, agent, task):
        """Test hard cap (_MAX_NO_TOOL_RETRIES = 3) on consecutive text-only responses."""
        mock_ask = AsyncMock(
            side_effect=[
                MockLLMResponse(content="Text response 1"),
                MockLLMResponse(content="Text response 2"),
                MockLLMResponse(content="Text response 3"),
            ]
        )

        with patch.object(agent.llm, "ask_tool", mock_ask), \
             patch.object(agent.llm, "format_messages", return_value=[]), \
             patch.object(agent.llm, "count_message_tokens", return_value=100):

            # Turn 1
            await agent.step(task)
            assert agent._consecutive_no_tool_responses == 1
            assert agent.state != AgentState.FINISHED

            # Turn 2
            await agent.step(task)
            assert agent._consecutive_no_tool_responses == 2
            assert agent.state != AgentState.FINISHED

            # Turn 3: hits max retries (3) and force-terminates with failure
            await agent.step(task)
            assert agent._consecutive_no_tool_responses == 3
            assert agent.state == AgentState.FINISHED
            assert agent.phase == AgentPhase.DONE

    @pytest.mark.asyncio
    async def test_tool_retry_on_error(self, agent, task):
        """Test that execute_tool retries when a tool returns ToolResult.is_error."""
        from app.tool.base import ToolResult

        tc = ToolCall(
            id="call_retry",
            function=Function(name="mock_tool", arguments='{"param": "failing"}'),
        )

        mock_tool_instance = AsyncMock()
        mock_tool_instance.can_retry = True
        mock_tool_instance.parallel_safe = False
        agent.available_tools.tool_map["mock_tool"] = mock_tool_instance

        mock_ask = AsyncMock(
            return_value=MockLLMResponse(content="Running failing tool", tool_calls=[tc])
        )

        # Mock available_tools.execute to fail on attempt 1, succeed on attempt 2
        mock_exec = AsyncMock(
            side_effect=[
                ToolResult(error="Command failed with exit code 1", exit_code=1),
                ToolResult(output="Success on retry!", exit_code=0),
            ]
        )

        with patch.object(agent.llm, "ask_tool", mock_ask), \
             patch.object(agent.llm, "format_messages", return_value=[]), \
             patch.object(agent.llm, "count_message_tokens", return_value=100), \
             patch.object(agent.available_tools, "execute", mock_exec):

            obs = await agent.step(task)
            # execute should have been called twice (1 initial + 1 retry)
            assert mock_exec.call_count == 2
            # The second call should include _error_context in tool_input
            second_call_args = mock_exec.call_args_list[1].kwargs.get("tool_input", {})
            assert "_error_context" in second_call_args
            assert "Command failed with exit code 1" in second_call_args["_error_context"]
            assert "Success on retry!" in obs
