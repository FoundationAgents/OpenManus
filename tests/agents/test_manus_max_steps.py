import pytest
import asyncio
from unittest import IsolatedAsyncioTestCase, mock
from unittest.mock import patch, AsyncMock, MagicMock, call 

from app.agent.manus import Manus
from app.agent.base import AgentState
from app.memory.base import Message
from app.schema import Role # Use this for Message roles
from app.llm.llm_client import LLMClient
from app.tool.ask_human import AskHuman
from app.config import config as app_config


# Ensure workspace_root is defined for tests, default if not in test config
if not hasattr(app_config, 'workspace_root') or not app_config.workspace_root:
    app_config.workspace_root = "test_workspace_manus_max_steps" 
    if not mock.os.path.exists(app_config.workspace_root): # Use mock.os for safety if os is patched
        mock.os.makedirs(app_config.workspace_root, exist_ok=True)


class TestManusMaxStepsInteraction(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_llm_client = AsyncMock(spec=LLMClient)
        self.mock_llm_client.chat_completion_async.return_value = Message(
            role=Role.ASSISTANT, content="LLM says proceed."
        )

        # Mock for AskHuman().execute
        self.mock_ask_human_execute = AsyncMock()

        # Patching AskHuman class to return a mock instance whose execute method is our AsyncMock
        # This ensures that when Manus's ToolCollection instantiates AskHuman, it gets this mock.
        self.ask_human_patcher = patch('app.agent.manus.AskHuman', new_callable=lambda: MagicMock(spec=AskHuman, execute=self.mock_ask_human_execute, name='MockedAskHumanInstance'))
        
        self.mocked_ask_human_class = self.ask_human_patcher.start()
        self.addCleanup(self.ask_human_patcher.stop)

        # Patch LLMClient where Manus imports/uses it
        self.llm_client_patcher = patch('app.agent.manus.LLMClient', return_value=self.mock_llm_client)
        self.mocked_llm_client_class = self.llm_client_patcher.start()
        self.addCleanup(self.llm_client_patcher.stop)
        
        # Create Manus instance. It will pick up the patched LLMClient and AskHuman.
        self.agent = await Manus.create()
        # Explicitly set agent's llm to the instance we can check calls on, though patching class should suffice
        self.agent.llm = self.mock_llm_client 
        self.agent.memory.clear()
        self.agent.current_step = 0
        self.agent.state = AgentState.IDLE # Ensure agent is IDLE before run

    async def asyncTearDown(self):
        pass

    async def test_pause_at_max_steps_and_correct_prompt(self):
        self.agent.max_steps = 3
        self.mock_ask_human_execute.return_value = "parar" # Stop after first check

        await self.agent.run(request="Test task for 3 steps then stop.")

        self.assertEqual(self.mock_ask_human_execute.call_count, 1)
        
        # Check current_step when AskHuman was called.
        # Manus.should_request_feedback is called when current_step is 3.
        # BaseAgent.run increments current_step *before* calling should_request_feedback.
        # So, the call to AskHuman via periodic_user_check_in happens effectively "at" step 3.
        # The prompt generated inside periodic_user_check_in uses self.current_step which would be 3.
        
        args, kwargs = self.mock_ask_human_execute.call_args_list[0]
        prompt_text = kwargs.get('inquire', args[0] if args else "") # inquire is a kwarg for AskHuman.execute

        self.assertIn("cycle of 3 steps", prompt_text)
        self.assertIn("total steps taken: 3", prompt_text)
        self.assertIn("continue for another 3 steps", prompt_text)
        self.assertIn("stop", prompt_text)
        self.assertIn("mudar:", prompt_text)
        
        self.assertEqual(self.agent.state, AgentState.IDLE) # USER_HALTED resets to IDLE
        # current_step is reset to 0 by BaseAgent when USER_HALTED
        self.assertEqual(self.agent.current_step, 0)


    async def test_continue_logic(self):
        self.agent.max_steps = 2
        # First call (step 2): continue. Second call (step 4): stop.
        self.mock_ask_human_execute.side_effect = ["continuar", "parar"]

        await self.agent.run(request="Test task for 2 cycles.")

        self.assertEqual(self.mock_ask_human_execute.call_count, 2)

        # Call 1 (at step 2)
        args1, kwargs1 = self.mock_ask_human_execute.call_args_list[0]
        prompt1_text = kwargs1.get('inquire', args1[0] if args1 else "")
        self.assertIn("total steps taken: 2", prompt1_text)
        self.assertIn("cycle of 2 steps", prompt1_text)

        # Call 2 (at step 4)
        args2, kwargs2 = self.mock_ask_human_execute.call_args_list[1]
        prompt2_text = kwargs2.get('inquire', args2[0] if args2 else "")
        self.assertIn("total steps taken: 4", prompt2_text)
        self.assertIn("cycle of 2 steps", prompt2_text)
        
        self.assertEqual(self.agent.state, AgentState.IDLE) # USER_HALTED resets to IDLE
        self.assertEqual(self.agent.current_step, 0) # Reset after USER_HALTED

    async def test_stop_logic(self):
        self.agent.max_steps = 3
        self.mock_ask_human_execute.return_value = "parar"

        initial_step_count = self.agent.current_step # Should be 0
        await self.agent.run(request="Test task, stop at first check.")
        
        self.assertEqual(self.mock_ask_human_execute.call_count, 1)
        
        # AskHuman is called when current_step IS max_steps (e.g. 3)
        # The prompt will reflect this.
        args, kwargs = self.mock_ask_human_execute.call_args_list[0]
        prompt_text = kwargs.get('inquire', args[0] if args else "")
        self.assertIn("total steps taken: 3", prompt_text)

        self.assertEqual(self.agent.state, AgentState.IDLE) # USER_HALTED leads to IDLE
        self.assertEqual(self.agent.current_step, 0) # current_step resets to 0

    async def test_mudar_logic(self):
        self.agent.max_steps = 2
        new_instruction = "new goal for the agent"
        # First call (step 2): mudar. Second call (step 4): stop.
        self.mock_ask_human_execute.side_effect = [f"mudar: {new_instruction}", "parar"]

        await self.agent.run(request="Test task with goal change.")

        self.assertEqual(self.mock_ask_human_execute.call_count, 2)

        # Check memory for the new instruction after the first interaction
        # The message from AskHuman (user's response) is added to memory by AskHuman tool itself,
        # or by the periodic_user_check_in logic.
        # In Manus.periodic_user_check_in: self.memory.add_message(Message.user_message(content=user_response_text))
        
        found_new_instruction = False
        for msg in self.agent.memory.messages:
            if msg.role == Role.USER and msg.content == f"mudar: {new_instruction}":
                found_new_instruction = True
                break
        self.assertTrue(found_new_instruction, "New instruction from 'mudar:' not found in agent memory.")

        # Call 1 (at step 2)
        args1, kwargs1 = self.mock_ask_human_execute.call_args_list[0]
        prompt1_text = kwargs1.get('inquire', args1[0] if args1 else "")
        self.assertIn("total steps taken: 2", prompt1_text)

        # Call 2 (at step 4)
        args2, kwargs2 = self.mock_ask_human_execute.call_args_list[1]
        prompt2_text = kwargs2.get('inquire', args2[0] if args2 else "")
        self.assertIn("total steps taken: 4", prompt2_text)

        self.assertEqual(self.agent.state, AgentState.IDLE) # Final state after "parar"
        self.assertEqual(self.agent.current_step, 0)

```
I've created a new file `tests/agents/test_manus_max_steps.py` because the original `test_manus.py` was quite focused on "ProactiveExecution" and was getting long. This provides better separation.

A few notes on the implementation:
-   **Patching `AskHuman`**: I'm patching `app.agent.manus.AskHuman` so that when `Manus`'s `ToolCollection` instantiates `AskHuman`, it gets a `MagicMock` whose `execute` method is my `AsyncMock`. This is a common and effective way to mock tools.
-   **`Role` enum**: Used `app.schema.Role` for message roles.
-   **`current_step` assertion**: In `BaseAgent.run`, `current_step` is incremented *before* `should_request_feedback` is called. So, if `max_steps = 3`, the check happens when `current_step` *is* 3. The prompt generated inside `periodic_user_check_in` will use this value.
-   **Final state `IDLE` and `current_step = 0`**: When `USER_HALTED`, `BaseAgent.run` resets the state to `IDLE` and `current_step` to `0`. The tests reflect this expected final state.
-   **`inquire` kwarg**: `AskHuman.execute` takes `inquire` as a keyword argument. The tests retrieve it using `kwargs.get('inquire', args[0] if args else "")`.

This structure and these tests should cover the required behaviors.
One adjustment: `app.memory.base.Message` and `app.agent.base.AgentState` were imported with corrected paths in my thoughts. I'll ensure these are right in the final code block. The `Role` import should be `from app.schema import Role`.

The file path should be `tests/agents/test_manus.py`, I need to add to the existing file, not create a new one. I will copy the existing content and append my new class and necessary imports.

Let's re-evaluate the file strategy. The prompt says "File to Modify: `tests/agents/test_manus.py`". So I must add to it.
I will copy the existing content of `tests/agents/test_manus.py` first, then append my new test class, ensuring imports are merged correctly.
It seems more appropriate to make a new file for organizational purposes, but the instructions are clear. I will append.

Final check of imports for the combined file:
`unittest.mock.call` will be needed.
`pytest` is not strictly used if sticking to `unittest.IsolatedAsyncioTestCase`.
`app.schema.Role` for `Message(role=Role.ASSISTANT, ...)`
`app.schema.AgentState` (already in `app.agent.base`) for `AgentState.IDLE` etc.
`app.schema.Message` (instead of `app.memory.base.Message`). Let me check `Manus` file for `Message` import.
`Manus.py` uses `from app.schema import Message, Role`. So `app.schema.Message` is correct.

The existing `TestManusProactiveExecution` uses `MessageRole`. I'll need to decide if I update that or use `Role` only in my new tests. It's better to be consistent. `MessageRole` might be an older enum. The `Manus.py` file uses `from app.schema import Message, Role`. So `Role` is the current one. I will update the existing test class's imports too for consistency if I touch them, but for now, I'll focus on adding the new class.
The existing tests use `from app.memory.base import Message, MessageRole`. I will use `from app.schema import Message, Role` for the new tests, as this seems to be the more current path used in `Manus` itself. This might mean the existing tests need an update later, but that's outside this task. For my new class, I'll use the schema path.

I will proceed with generating the combined file content.
