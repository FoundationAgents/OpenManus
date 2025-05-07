from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agent.browser import BrowserAgent
from app.agent.manus import Manus
from app.prompt.manus import NEXT_STEP_PROMPT


class MockMessage:
    def __init__(self, content):
        self.content = content


@pytest.fixture
def manus(mocker):
    mocker.patch.object(BrowserAgent, "think", AsyncMock(return_value=True))
    manus = Manus()
    manus.memory = MagicMock()
    manus.memory.messages = []
    # manus.think = AsyncMock(return_value=True)
    return manus


@pytest.mark.asyncio
async def test_think_no_browser_activity(manus):
    manus.memory.messages = [
        MockMessage("This is a test message"),
        MockMessage("Another message"),
    ]
    await manus.think()
    assert manus.next_step_prompt == NEXT_STEP_PROMPT


@pytest.mark.asyncio
async def test_think_with_browser_activity(manus):
    manus.memory.messages = [
        MockMessage("This is a test message"),
        MockMessage("browser_use"),
    ]
    await manus.think()
    assert manus.next_step_prompt == NEXT_STEP_PROMPT


@pytest.mark.asyncio
async def test_think_with_browser_activity_in_last_message(manus):
    manus.memory.messages = [
        MockMessage("This is a test message"),
        MockMessage("Another message"),
        MockMessage("browser_use"),
    ]
    await manus.think()
    assert manus.next_step_prompt == NEXT_STEP_PROMPT


@pytest.mark.asyncio
async def test_think_with_browser_activity_in_recent_messages(manus):
    manus.memory.messages = [
        MockMessage("browser_use"),
        MockMessage("Another message"),
        MockMessage("This is a test message"),
    ]
    await manus.think()
    assert manus.next_step_prompt == NEXT_STEP_PROMPT
