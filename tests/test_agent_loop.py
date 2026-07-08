"""Tests for the agent loop's pure-logic functions.

No LLM mocking required — these test structural control flow decisions,
stuck detection, phase transitions, and the terminate tool path.
"""
import hashlib
import pytest

from app.schema import AgentPhase, AgentState, Message, ToolCall, Function, Memory


# ---------------------------------------------------------------------------
# Stuck detection tests
# ---------------------------------------------------------------------------

class TestIsStuck:
    """Test BaseAgent.is_stuck() — the two-signal stuck detection."""

    def _make_agent(self):
        """Create a minimal BaseAgent subclass for testing."""
        from app.agent.base import BaseAgent

        class StubAgent(BaseAgent):
            name: str = "test"

            async def step(self, task):
                return "ok"

        return StubAgent(name="test")

    def test_empty_messages_not_stuck(self):
        agent = self._make_agent()
        assert agent.is_stuck() is False

    def test_single_message_not_stuck(self):
        agent = self._make_agent()
        agent.memory.add_message(Message.assistant_message("hello"))
        assert agent.is_stuck() is False

    def test_different_messages_not_stuck(self):
        agent = self._make_agent()
        agent.memory.add_message(Message.assistant_message("hello"))
        agent.memory.add_message(Message.assistant_message("world"))
        assert agent.is_stuck() is False

    def test_exact_duplicate_content_is_stuck(self):
        agent = self._make_agent()
        agent.memory.add_message(Message.assistant_message("I am stuck"))
        agent.memory.add_message(Message.assistant_message("I am stuck"))
        agent.memory.add_message(Message.assistant_message("I am stuck"))
        assert agent.is_stuck() is True

    def test_whitespace_variant_duplicate_is_stuck(self):
        """Content-hash signal should catch whitespace-variant duplicates."""
        agent = self._make_agent()
        agent.memory.add_message(Message.assistant_message("I am  stuck"))
        agent.memory.add_message(Message.assistant_message("I  am stuck"))
        agent.memory.add_message(Message.assistant_message("I am stuck"))
        assert agent.is_stuck() is True

    def test_case_variant_duplicate_is_stuck(self):
        """Content-hash normalizes to lowercase."""
        agent = self._make_agent()
        agent.memory.add_message(Message.assistant_message("I AM STUCK"))
        agent.memory.add_message(Message.assistant_message("i am stuck"))
        agent.memory.add_message(Message.assistant_message("I am Stuck"))
        assert agent.is_stuck() is True

    def test_tool_call_repetition_is_stuck(self):
        """Repeated identical tool-call signatures should trigger stuck."""
        agent = self._make_agent()
        tc = ToolCall(id="1", function=Function(name="bash", arguments='{"cmd": "ls"}'))
        for _ in range(3):
            msg = Message.from_tool_calls(
                content="Let me check",
                tool_calls=[tc],
            )
            agent.memory.add_message(msg)
        assert agent.is_stuck() is True

    def test_different_tool_calls_not_stuck(self):
        """Different tool call signatures should not trigger stuck."""
        agent = self._make_agent()
        for i in range(3):
            tc = ToolCall(
                id=str(i),
                function=Function(name="bash", arguments=f'{{"cmd": "cmd{i}"}}'),
            )
            msg = Message.from_tool_calls(content=f"Step {i}", tool_calls=[tc])
            agent.memory.add_message(msg)
        assert agent.is_stuck() is False

    def test_none_content_not_stuck(self):
        """Messages with None content should not crash stuck detection."""
        agent = self._make_agent()
        agent.memory.add_message(Message.assistant_message(None))
        agent.memory.add_message(Message.assistant_message(None))
        assert agent.is_stuck() is False


# ---------------------------------------------------------------------------
# ToolResult tests
# ---------------------------------------------------------------------------

class TestToolResult:
    """Test ToolResult.is_error, __add__, success_response, fail_response."""

    def test_success_result_not_error(self):
        from app.tool.base import ToolResult
        r = ToolResult(output="success")
        assert r.is_error is False

    def test_error_result_is_error(self):
        from app.tool.base import ToolResult
        r = ToolResult(error="something broke")
        assert r.is_error is True

    def test_nonzero_exit_code_is_error(self):
        from app.tool.base import ToolResult
        r = ToolResult(output="partial output", exit_code=1)
        assert r.is_error is True

    def test_zero_exit_code_no_error(self):
        from app.tool.base import ToolResult
        r = ToolResult(output="ok", exit_code=0)
        assert r.is_error is False

    def test_add_combines_output(self):
        from app.tool.base import ToolResult
        r1 = ToolResult(output="hello ")
        r2 = ToolResult(output="world")
        combined = r1 + r2
        assert combined.output == "hello world"

    def test_add_combines_errors(self):
        from app.tool.base import ToolResult
        r1 = ToolResult(error="err1")
        r2 = ToolResult(error="err2")
        combined = r1 + r2
        assert combined.error == "err1err2"

    def test_add_preserves_nonzero_exit_code(self):
        from app.tool.base import ToolResult
        r1 = ToolResult(output="ok", exit_code=0)
        r2 = ToolResult(output="fail", exit_code=127)
        combined = r1 + r2
        assert combined.exit_code == 127

    def test_add_merges_metadata(self):
        from app.tool.base import ToolResult
        r1 = ToolResult(output="a", metadata={"path": "/tmp/a"})
        r2 = ToolResult(output="b", metadata={"url": "http://example.com"})
        combined = r1 + r2
        assert combined.metadata["path"] == "/tmp/a"
        assert combined.metadata["url"] == "http://example.com"

    def test_str_representation_error(self):
        from app.tool.base import ToolResult
        r = ToolResult(error="broken pipe")
        assert str(r) == "Error: broken pipe"

    def test_str_representation_success(self):
        from app.tool.base import ToolResult
        r = ToolResult(output="file created")
        assert str(r) == "file created"


# ---------------------------------------------------------------------------
# Terminate tool tests
# ---------------------------------------------------------------------------

class TestTerminateTool:
    """Test Terminate.execute() with various status/summary combinations."""

    @pytest.mark.asyncio
    async def test_terminate_success(self):
        from app.tool.terminate import Terminate
        t = Terminate()
        result = await t.execute(status="success", summary="Task done")
        assert "success" in result
        assert "Task done" in result

    @pytest.mark.asyncio
    async def test_terminate_failure(self):
        from app.tool.terminate import Terminate
        t = Terminate()
        result = await t.execute(
            status="failure",
            summary="Could not complete",
            reason="API key missing",
        )
        assert "failure" in result
        assert "API key missing" in result

    @pytest.mark.asyncio
    async def test_terminate_minimal(self):
        from app.tool.terminate import Terminate
        t = Terminate()
        result = await t.execute(status="success")
        assert "success" in result

    @pytest.mark.asyncio
    async def test_terminate_with_reason(self):
        from app.tool.terminate import Terminate
        t = Terminate()
        result = await t.execute(
            status="failure",
            reason="Out of disk space",
        )
        assert "failure" in result
        assert "Out of disk space" in result


# ---------------------------------------------------------------------------
# PlanningTool lifecycle tests
# ---------------------------------------------------------------------------

class TestPlanningTool:
    """Test PlanningTool create/update/mark_step/get/delete lifecycle."""

    @pytest.mark.asyncio
    async def test_create_plan(self):
        from app.tool.planning import PlanningTool
        pt = PlanningTool()
        result = await pt.execute(
            command="create",
            plan_id="test-1",
            title="Test Plan",
            steps=["Step A", "Step B", "Step C"],
        )
        assert "test-1" in result.output
        assert "Test Plan" in result.output
        assert pt._current_plan_id == "test-1"

    @pytest.mark.asyncio
    async def test_get_plan(self):
        from app.tool.planning import PlanningTool
        pt = PlanningTool()
        await pt.execute(
            command="create",
            plan_id="test-2",
            title="Get Test",
            steps=["Step 1"],
        )
        result = await pt.execute(command="get", plan_id="test-2")
        assert "Get Test" in result.output

    @pytest.mark.asyncio
    async def test_mark_step_completed(self):
        from app.tool.planning import PlanningTool
        pt = PlanningTool()
        await pt.execute(
            command="create",
            plan_id="test-3",
            title="Mark Test",
            steps=["Do thing"],
        )
        result = await pt.execute(
            command="mark_step",
            plan_id="test-3",
            step_index=0,
            step_status="completed",
        )
        assert "[✓]" in result.output

    @pytest.mark.asyncio
    async def test_update_plan_preserves_status(self):
        from app.tool.planning import PlanningTool
        pt = PlanningTool()
        await pt.execute(
            command="create",
            plan_id="test-4",
            title="Update Test",
            steps=["Step A", "Step B"],
        )
        await pt.execute(
            command="mark_step",
            plan_id="test-4",
            step_index=0,
            step_status="completed",
        )
        # Update with same first step — status should be preserved
        await pt.execute(
            command="update",
            plan_id="test-4",
            steps=["Step A", "Step C"],
        )
        plan = pt.plans["test-4"]
        assert plan["step_statuses"][0] == "completed"
        assert plan["step_statuses"][1] == "not_started"

    @pytest.mark.asyncio
    async def test_delete_plan(self):
        from app.tool.planning import PlanningTool
        pt = PlanningTool()
        await pt.execute(
            command="create",
            plan_id="test-5",
            title="Delete Test",
            steps=["Step 1"],
        )
        result = await pt.execute(command="delete", plan_id="test-5")
        assert "deleted" in result.output
        assert "test-5" not in pt.plans

    @pytest.mark.asyncio
    async def test_create_duplicate_raises(self):
        from app.tool.planning import PlanningTool
        from app.exceptions import ToolError
        pt = PlanningTool()
        await pt.execute(
            command="create",
            plan_id="dup",
            title="First",
            steps=["Step 1"],
        )
        with pytest.raises(ToolError):
            await pt.execute(
                command="create",
                plan_id="dup",
                title="Second",
                steps=["Step 2"],
            )

    @pytest.mark.asyncio
    async def test_mark_step_invalid_index_raises(self):
        from app.tool.planning import PlanningTool
        from app.exceptions import ToolError
        pt = PlanningTool()
        await pt.execute(
            command="create",
            plan_id="idx",
            title="Index Test",
            steps=["Only step"],
        )
        with pytest.raises(ToolError):
            await pt.execute(
                command="mark_step",
                plan_id="idx",
                step_index=5,
                step_status="completed",
            )


# ---------------------------------------------------------------------------
# AgentPhase enum tests
# ---------------------------------------------------------------------------

class TestAgentPhase:
    """Test AgentPhase enum values and transitions."""

    def test_all_phases_exist(self):
        assert AgentPhase.PLAN.value == "PLAN"
        assert AgentPhase.ACT.value == "ACT"
        assert AgentPhase.OBSERVE.value == "OBSERVE"
        assert AgentPhase.VERIFY.value == "VERIFY"
        assert AgentPhase.DONE.value == "DONE"

    def test_phase_is_string_enum(self):
        assert isinstance(AgentPhase.PLAN, str)
        assert AgentPhase.PLAN == "PLAN"


# ---------------------------------------------------------------------------
# Exception hierarchy tests
# ---------------------------------------------------------------------------

class TestExceptions:
    """Test the typed exception classes."""

    def test_agent_loop_error_is_openmanus_error(self):
        from app.exceptions import AgentLoopError, OpenManusError
        e = AgentLoopError("loop broken")
        assert isinstance(e, OpenManusError)

    def test_verification_failed_carries_reason(self):
        from app.exceptions import VerificationFailed
        e = VerificationFailed("tests did not pass")
        assert e.reason == "tests did not pass"
        assert str(e) == "tests did not pass"

    def test_token_limit_exceeded_is_openmanus_error(self):
        from app.exceptions import TokenLimitExceeded, OpenManusError
        e = TokenLimitExceeded("too many tokens")
        assert isinstance(e, OpenManusError)


# ---------------------------------------------------------------------------
# _should_finish_execution tests
# ---------------------------------------------------------------------------

class TestShouldFinishExecution:
    """Test ToolCallAgent._should_finish_execution — the terminate gate."""

    def test_always_returns_true(self):
        """The terminate tool is the structural path — always honored."""
        from app.agent.toolcall import ToolCallAgent
        assert ToolCallAgent._should_finish_execution(name="terminate") is True
        assert ToolCallAgent._should_finish_execution(name="terminate", result="done") is True
        assert ToolCallAgent._should_finish_execution() is True


# ---------------------------------------------------------------------------
# Memory tests
# ---------------------------------------------------------------------------

class TestMemory:
    """Test Memory add/clear/get_recent."""

    def test_add_and_retrieve(self):
        mem = Memory()
        mem.add_message(Message.user_message("hello"))
        assert len(mem.messages) == 1
        assert mem.messages[0].content == "hello"

    def test_max_messages_enforced(self):
        mem = Memory(max_messages=3)
        for i in range(5):
            mem.add_message(Message.user_message(f"msg {i}"))
        assert len(mem.messages) == 3
        assert mem.messages[0].content == "msg 2"

    def test_clear(self):
        mem = Memory()
        mem.add_message(Message.user_message("hello"))
        mem.clear()
        assert len(mem.messages) == 0

    def test_get_recent(self):
        mem = Memory()
        for i in range(10):
            mem.add_message(Message.user_message(f"msg {i}"))
        recent = mem.get_recent_messages(3)
        assert len(recent) == 3
        assert recent[0].content == "msg 7"
