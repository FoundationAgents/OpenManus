from unittest.mock import AsyncMock

import pytest
from pydantic import Field

from app.agent.base import AgentState, BaseAgent
from app.llm import LLM
from app.sandbox.client import SANDBOX_CLIENT
from app.schema import Memory, Role


class MockAgent(BaseAgent):
    name: str
    description: str | None = None

    system_prompt: str | None = None
    next_step_prompt: str | None = None

    llm: LLM = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE

    max_steps: int = 10
    current_step: int = 0

    async def step(self) -> str:
        return "Mock step result"


class MockFeaturedAgent(BaseAgent):
    name: str
    description: str | None = None

    system_prompt: str | None = None
    next_step_prompt: str | None = None

    llm: LLM = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE

    max_steps: int = 10
    current_step: int = 0

    __cnt = 0

    async def step(self) -> str:
        self.__cnt += 1
        if self.__cnt > 4:
            self.state = AgentState.FINISHED
        return "Mock step result {}".format((self.__cnt - 1) % 2)


@pytest.fixture
def mock_agent():
    return MockAgent(
        name="TestAgent",
        system_prompt="System prompt",
        next_step_prompt="Next step prompt",
    )


@pytest.fixture
def mock_featured_agent():
    return MockFeaturedAgent(
        name="TestAgent",
        system_prompt="System prompt",
        next_step_prompt="Next step prompt",
    )


@pytest.mark.asyncio
async def test_run_happy_path(mock_agent):
    mock_agent.step = AsyncMock(return_value="Mock step result")
    SANDBOX_CLIENT.cleanup = AsyncMock()
    result = await mock_agent.run()
    assert (
        result
        == """Step 1: Mock step result
Step 2: Mock step result
Step 3: Mock step result
Step 4: Mock step result
Step 5: Mock step result
Step 6: Mock step result
Step 7: Mock step result
Step 8: Mock step result
Step 9: Mock step result
Step 10: Mock step result
Terminated: Reached max steps (10)"""
    )
    assert mock_agent.current_step == 0
    assert mock_agent.state == AgentState.IDLE
    SANDBOX_CLIENT.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_run_with_request(mock_agent):
    mock_agent.step = AsyncMock(return_value="Mock step result")
    SANDBOX_CLIENT.cleanup = AsyncMock()
    result = await mock_agent.run(request="User request")
    assert (
        result
        == """Step 1: Mock step result
Step 2: Mock step result
Step 3: Mock step result
Step 4: Mock step result
Step 5: Mock step result
Step 6: Mock step result
Step 7: Mock step result
Step 8: Mock step result
Step 9: Mock step result
Step 10: Mock step result
Terminated: Reached max steps (10)"""
    )
    assert mock_agent.current_step == 0  # reset at max_steps
    assert mock_agent.state == AgentState.IDLE
    assert mock_agent.messages[0].role == Role.USER
    assert mock_agent.messages[0].content == "User request"
    SANDBOX_CLIENT.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_run_max_steps(mock_agent):
    mock_agent.step = AsyncMock(return_value="Mock step result")
    SANDBOX_CLIENT.cleanup = AsyncMock()
    mock_agent.max_steps = 2
    result = await mock_agent.run()
    assert (
        result
        == "Step 1: Mock step result\nStep 2: Mock step result\nTerminated: Reached max steps (2)"
    )
    assert mock_agent.current_step == 0
    assert mock_agent.state == AgentState.IDLE
    SANDBOX_CLIENT.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_run_agent_already_running(mock_agent):
    mock_agent.state = AgentState.RUNNING
    with pytest.raises(RuntimeError) as e:
        await mock_agent.run()
    assert str(e.value) == "Cannot run agent from state: AgentState.RUNNING"


@pytest.mark.asyncio
async def test_run_agent_stuck(mock_agent):
    mock_agent.step = AsyncMock(return_value="Stuck result")
    SANDBOX_CLIENT.cleanup = AsyncMock()
    mock_agent.duplicate_threshold = 1
    mock_agent.update_memory(Role.ASSISTANT, "Stuck result")
    mock_agent.update_memory(Role.ASSISTANT, "Stuck result")
    result = await mock_agent.run()
    assert "Observed duplicate responses" in mock_agent.next_step_prompt
    assert "Step 1: Stuck result" in result
    assert (
        mock_agent.current_step == 0
    )  # it will run 10 times and just reset the counter
    assert mock_agent.state == AgentState.IDLE
    SANDBOX_CLIENT.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_update_memory_happy_path(mock_agent):
    mock_agent.update_memory(Role.USER, "User message")
    assert mock_agent.messages[0].role == Role.USER
    assert mock_agent.messages[0].content == "User message"


@pytest.mark.asyncio
async def test_update_memory_unsupported_role(mock_agent):
    with pytest.raises(ValueError) as e:
        mock_agent.update_memory("unsupported", "Content")
    assert str(e.value) == "Unsupported message role: unsupported"


@pytest.mark.asyncio
async def test_is_stuck_not_enough_messages(mock_agent):
    assert not mock_agent.is_stuck()


@pytest.mark.asyncio
async def test_is_stuck_no_duplicates(mock_agent):
    mock_agent.update_memory(Role.ASSISTANT, "Unique result 1")
    mock_agent.update_memory(Role.ASSISTANT, "Unique result 2")
    assert not mock_agent.is_stuck()


@pytest.mark.asyncio
async def test_is_stuck_with_duplicates(mock_agent):
    mock_agent.update_memory(Role.ASSISTANT, "Duplicate result")
    mock_agent.update_memory(Role.ASSISTANT, "Duplicate result")
    mock_agent.update_memory(Role.ASSISTANT, "Duplicate result")
    assert mock_agent.is_stuck()


@pytest.mark.asyncio
async def test_is_stuck_different_roles(mock_agent):
    mock_agent.update_memory(Role.ASSISTANT, "First Message")
    mock_agent.update_memory(Role.ASSISTANT, "Duplicate result")
    mock_agent.update_memory(Role.USER, "Duplicate result")
    mock_agent.update_memory(Role.ASSISTANT, "Duplicate result")
    assert not mock_agent.is_stuck()


@pytest.mark.asyncio
async def test_auto_fix_weird_llm(mock_agent):
    class not_a_llm_object:
        a = "hello"
        b = "handsome"
        c = "manna" and "poem"

    mock_agent.llm = not_a_llm_object_instance = not_a_llm_object()

    mock_agent.initialize_agent()
    assert (
        isinstance(mock_agent.llm, LLM)
        and not_a_llm_object_instance is not mock_agent.llm
    )


@pytest.mark.asyncio
async def test_auto_fix_weird_memory(mock_agent):
    class not_a_memory_object:
        a = "not"
        b = "memory"
        c = "object"
        d = "absolutely"

    mock_agent.memory = not_a_memory_object_instance = not_a_memory_object()

    mock_agent.initialize_agent()

    assert isinstance(mock_agent.memory, Memory)
    assert not_a_memory_object_instance is not mock_agent.memory


@pytest.mark.asyncio
async def test_state_context_invalid_new_state(mock_agent):
    class not_a_state_object:
        a = "not"
        b = "state"
        c = "object"

    new_state = not_a_state_object()

    with pytest.raises(ValueError) as e:
        async with mock_agent.state_context(new_state):
            pass
    assert "Invalid state:" in str(e.value)


@pytest.mark.asyncio
async def test_state_context_raise_exception(mock_agent):
    prev_state = mock_agent.state
    with pytest.raises(RuntimeError) as e:
        async with mock_agent.state_context(AgentState.RUNNING):
            raise RuntimeError("Test exception 123123")
    # assert mock_agent.state == AgentState.ERROR
    assert str(e.value) == "Test exception 123123"
    assert mock_agent.state == prev_state


@pytest.mark.asyncio
async def test_run_with_request_featured_agent(mock_featured_agent):
    SANDBOX_CLIENT.cleanup = AsyncMock()
    result = await mock_featured_agent.run(request="User request")
    assert (
        result
        == """Step 1: Mock step result 0
Step 2: Mock step result 1
Step 3: Mock step result 0
Step 4: Mock step result 1
Step 5: Mock step result 0"""
    )
    assert mock_featured_agent.current_step == 5
    assert mock_featured_agent.state == AgentState.IDLE
    assert mock_featured_agent.messages[0].role == Role.USER
    assert mock_featured_agent.messages[0].content == "User request"
    SANDBOX_CLIENT.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_is_stuck_invalid_last_message(mock_agent):
    mock_agent.update_memory(Role.ASSISTANT, "First Message")
    mock_agent.update_memory(Role.ASSISTANT, "Duplicate result")
    mock_agent.update_memory(Role.USER, "Duplicate result")
    mock_agent.update_memory(Role.ASSISTANT, None)
    assert not mock_agent.is_stuck()


@pytest.mark.asyncio
async def test_agent_message_assignment(mock_agent):
    class test_messages_object:
        manna = "poem"

    a = test_messages_object()

    assert mock_agent.messages is not a

    mock_agent.messages = a

    assert mock_agent.messages is a
