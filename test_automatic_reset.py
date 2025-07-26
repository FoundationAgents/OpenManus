import asyncio
import os
import json # For FunctionCall arguments

from app.agent.manus import Manus
from app.schema import Message, Role, Function as FunctionCall, ToolCall # Corrected import
from app.tool.checklist_tools import ResetCurrentTaskChecklistTool, ViewChecklistTool
from app.agent.checklist_manager import ChecklistManager # To verify parsing
from app.config import config
from app.logger import logger # For capturing logs if needed

async def main():
    logger.info("Starting Test 1: Automatic Checklist Reset & Parsing")

    # Ensure workspace and initial checklist file exist (as setup by previous step)
    initial_checklist_path_str = str(config.workspace_root / "checklist_principal_tarefa.md")
    if not os.path.exists(initial_checklist_path_str):
        logger.error("TEST PRECONDITION FAILED: Initial checklist_principal_tarefa.md does not exist.")
        return

    with open(initial_checklist_path_str, 'r') as f:
        logger.info(f"Initial checklist content:\n{f.read()}")

    # 1. Instantiate Manus and give it a new prompt
    # Assuming Manus.create() and other setup is lightweight enough for this test script
    agent = await Manus.create()
    agent.memory.add_message(Message.user_message("Este é um prompt para uma tarefa completamente nova."))

    # agent.current_step will be 0 initially.
    # The ToolCallAgent.run() method increments current_step to 1 *before* the first call to self.step() (which calls think).
    # So, to simulate the state where manus.think() is called for the first time for a new task:
    agent.current_step = 1

    logger.info("Calling agent.think() for the first time with a new prompt...")
    await agent.think()

    # 2. Check if the first planned tool call is reset_current_task_checklist
    if not agent.tool_calls:
        logger.error("Test Failed: Agent did not plan any tool calls.")
        print_agent_memory(agent)
        return

    first_tool_call = agent.tool_calls[0]
    expected_tool_name = ResetCurrentTaskChecklistTool().name

    if first_tool_call.function.name == expected_tool_name:
        logger.info(f"Test Passed (Step 2a): Agent correctly planned '{expected_tool_name}' as the first action.")

        # 3. Simulate execution of reset_current_task_checklist
        logger.info(f"Simulating execution of '{expected_tool_name}'...")
        reset_tool = ResetCurrentTaskChecklistTool()
        reset_result = await reset_tool.execute()
        logger.info(f"Result of {expected_tool_name}: {reset_result.output if reset_result else 'No output'}")

        # Check if checklist file is now empty
        if os.path.exists(initial_checklist_path_str):
            with open(initial_checklist_path_str, 'r') as f:
                content_after_reset = f.read()
                if content_after_reset == "":
                    logger.info("Test Passed (Step 2b): Checklist file is empty after reset.")
                else:
                    logger.error(f"Test Failed (Step 2b): Checklist file is NOT empty. Content:\n'''{content_after_reset}'''")
        else:
            logger.error("Test Failed (Step 2b): Checklist file does not exist after reset (it should be empty).")

        # 4. Simulate view_checklist and check parsing
        # The agent's next step (after the reset tool call is processed by the main loop) would be to think again.
        # The prompt for Manus instructs it to call view_checklist after a reset.
        # We can simulate this part by directly using ChecklistManager.
        logger.info("Simulating ChecklistManager loading the (now empty) checklist...")
        checklist_manager = ChecklistManager()
        # Capture logs during _load_checklist to check for parsing warnings
        # This is a bit hacky for a test script, but serves the purpose.
        # A more robust way would be to use a custom log handler if this were a formal test suite.

        # Temporarily redirect logger to capture warnings (if possible, or check manually)
        # For this test, we'll rely on observing the logs printed by the script run.
        await checklist_manager._load_checklist()
        if not checklist_manager.tasks:
            logger.info("Test Passed (Step 2c): ChecklistManager loaded an empty task list.")
            # Check logs manually for "Could not parse checklist line" for the header if it was written.
            # Since reset_checklist writes an empty file, no header should be there, so no warning.
        else:
            logger.error(f"Test Failed (Step 2c): ChecklistManager loaded tasks: {checklist_manager.tasks}")

    else:
        logger.error(f"Test Failed (Step 2a): Expected first tool to be '{expected_tool_name}', but got '{first_tool_call.function.name}'.")
        print_agent_memory(agent)

    # Clean up agent
    await agent.cleanup()
    logger.info("Test 1 finished.")

def print_agent_memory(agent: Manus):
    logger.info("Current agent memory:")
    for i, msg in enumerate(agent.memory.messages):
        logger.info(f"Msg {i}: Role={msg.role}, Content='{str(msg.content)[:200]}...', ToolCalls={len(msg.tool_calls) if msg.tool_calls else 0}")
        if msg.tool_calls:
            for tc_idx, tc in enumerate(msg.tool_calls):
                logger.info(f"  ToolCall {tc_idx}: ID={tc.id}, Name={tc.function.name}, Args='{str(tc.function.arguments)[:100]}...'")


if __name__ == "__main__":
    asyncio.run(main())
