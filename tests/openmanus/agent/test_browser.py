from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agent.browser import BrowserAgent
from app.tool import BrowserUseTool, Terminate, ToolCollection


@pytest.fixture
def browser_agent():
    agent = BrowserAgent()
    agent.available_tools = ToolCollection(BrowserUseTool(), Terminate())
    agent.memory = MagicMock()
    agent._current_base64_image = None
    return agent


# @pytest.mark.asyncio
# async def test_get_browser_state_success(browser_agent):
#     browser_tool = browser_agent.available_tools.get_tool(BrowserUseTool().name)
#     browser_tool.get_current_state = AsyncMock(
#         return_value=MagicMock(
#             error=None,
#             output='{"url": "http://example.com", "title": "Example", "pixels_above": 100, "pixels_below": 200, "tabs": ["Tab1"]}',
#         )
#     )
#     state = await browser_agent.get_browser_state()
#     assert state == {
#         "url": "http://example.com",
#         "title": "Example",
#         "pixels_above": 100,
#         "pixels_below": 200,
#         "tabs": ["Tab1"],
#     }


@pytest.mark.asyncio
async def test_get_browser_state_error(browser_agent, mocker):
    mocker.patch.object(
        BrowserUseTool,
        "get_current_state",
        AsyncMock(return_value=MagicMock(error="Error occurred")),
    )
    state = await browser_agent.get_browser_state()
    assert state is None


@pytest.mark.asyncio
async def test_get_browser_state_exception(browser_agent, mocker):
    mocker.patch.object(
        BrowserUseTool,
        "get_current_state",
        AsyncMock(side_effect=Exception("Exception occurred")),
    )
    state = await browser_agent.get_browser_state()
    assert state is None


# @pytest.mark.asyncio
# async def test_think_with_browser_state(browser_agent, mocker):
#     mocker.patch.object(
#         BrowserUseTool,
#         "get_current_state",
#         AsyncMock(
#             return_value=MagicMock(
#                 error=None,
#                 output='{"url": "http://example.com", "title": "Example", "pixels_above": 100, "pixels_below": 200, "tabs": ["Tab1"]}',
#             )
#         ),
#     )
#     browser_agent._current_base64_image = "base64_image_data"
#     browser_agent.memory.add_message = MagicMock()

#     think_result = await browser_agent.think()

#     expected_next_step_prompt = NEXT_STEP_PROMPT.format(
#         url_placeholder="\n   URL: http://example.com\n   Title: Example",
#         tabs_placeholder="\n   1 tab(s) available",
#         content_above_placeholder=" (100 pixels)",
#         content_below_placeholder=" (200 pixels)",
#         results_placeholder="",
#     )
#     assert browser_agent.next_step_prompt == expected_next_step_prompt
#     assert browser_agent.memory.add_message.called_with(
#         Message.user_message(
#             content="Current browser screenshot:",
#             base64_image="base64_image_data",
#         )
#     )
#     assert think_result is True


# @pytest.mark.asyncio
# async def test_think_without_browser_state(browser_agent, mocker):
#     mocker.patch.object(
#         BrowserUseTool,
#         "execute",
#         AsyncMock(return_value=MagicMock(error="Error occurred")),
#     )
#     mocker.patch.object(
#         LLM,
#         "ask_tool",
#         AsyncMock(return_value=ChatCompletionMessage.model_construct()),
#     )

#     think_result = await browser_agent.think()

#     expected_next_step_prompt = NEXT_STEP_PROMPT.format(
#         url_placeholder="",
#         tabs_placeholder="",
#         content_above_placeholder="",
#         content_below_placeholder="",
#         results_placeholder="",
#     )
#     assert browser_agent.next_step_prompt == expected_next_step_prompt
#     assert not browser_agent.memory.add_message.called
#     assert think_result is True


# @pytest.mark.asyncio
# async def test_handle_special_tool(browser_agent, mocker):
#     mocker.patch.object(
#         BrowserUseTool,
#         "cleanup",
#         AsyncMock(),
#     )
#     browser_agent._handle_special_tool = AsyncMock()

#     await browser_agent._handle_special_tool(Terminate().name, result="result")

#     assert browser_agent.available_tools.get_tool(BrowserUseTool().name).cleanup.called
#     assert browser_agent._handle_special_tool.called_with(Terminate().name, "result")


# @pytest.mark.asyncio
# async def test_handle_special_tool_not_special(browser_agent, mocker):
#     mocker.patch.object(
#         BrowserUseTool,
#         "cleanup",
#         AsyncMock(),
#     )
#     browser_agent._handle_special_tool = AsyncMock()

#     await browser_agent._handle_special_tool("NotSpecialTool", result="result")

#     assert not browser_agent.available_tools.get_tool(
#         BrowserUseTool().name
#     ).cleanup.called
#     assert not browser_agent._handle_special_tool.called_with(
#         "NotSpecialTool", "result"
#     )
