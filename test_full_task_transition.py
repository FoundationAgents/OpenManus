import asyncio
import os
import json

from app.agent.manus import Manus
from app.schema import Message, Role, Function as FunctionCall, ToolCall, AgentState
from app.tool.checklist_tools import AddChecklistTaskTool, UpdateChecklistTaskTool, ViewChecklistTool, ResetCurrentTaskChecklistTool
from app.tool.ask_human import AskHuman
from app.config import config
from app.logger import logger

# --- Helper to print memory ---
def print_agent_memory(agent: Manus, log_tag: str):
    logger.info(f"--- Agent Memory ({log_tag}) ---")
    for i, msg in enumerate(agent.memory.messages):
        content_summary = str(msg.content)[:100] + "..." if msg.content and len(str(msg.content)) > 100 else str(msg.content)
        tc_summary = ""
        if msg.tool_calls:
            tc_names = [tc.function.name for tc in msg.tool_calls]
            tc_summary = f", Planned TCs: {tc_names}"
        logger.info(f"  Msg {i}: Role={msg.role}, Content='{content_summary}'{tc_summary}")
    logger.info(f"--- End Memory ({log_tag}) ---")

# --- Helper to print checklist ---
async def print_checklist_status(log_tag: str):
    logger.info(f"--- Checklist Status ({log_tag}) ---")
    view_tool = ViewChecklistTool()
    checklist_view_result = await view_tool.execute()
    logger.info(checklist_view_result.output if checklist_view_result else "Could not view checklist")
    logger.info(f"--- End Checklist ({log_tag}) ---")


async def simulate_tool_execution(agent: Manus):
    if not agent.tool_calls:
        logger.info("Simulate: No tool calls to execute.")
        return

    tool_call_to_execute = agent.tool_calls[0] # Assuming one tool call for simplicity in test
    tool_name = tool_call_to_execute.function.name
    tool_args = json.loads(tool_call_to_execute.function.arguments)

    logger.info(f"Simulate: Executing tool '{tool_name}' with args: {tool_args}")

    actual_tool = agent.available_tools.get_tool(tool_name)
    if not actual_tool:
        logger.error(f"Simulate: Tool '{tool_name}' not found in agent's available tools.")
        # Add error message to memory
        agent.memory.add_message(Message(role=Role.TOOL, name=tool_name, tool_call_id=tool_call_to_execute.id, content=f"Error: Tool '{tool_name}' not found."))
        return

    try:
        # For AskHuman, we need to provide a simulated user response
        if tool_name == AskHuman().name:
            # This simulation won't actually prompt, it's for testing the agent's reaction *after* AskHuman
            # In a real scenario, the main loop or test harness would provide input.
            # Here, we just simulate the tool returning what it was asked.
            simulated_user_response = tool_args.get("inquire", "Simulated empty response to AskHuman")
            tool_result_content = simulated_user_response
            logger.info(f"Simulate: AskHuman was called. For test purposes, returning the question as content: '{tool_result_content}'")
        else:
            execution_result_obj = await actual_tool.execute(**tool_args)
            if hasattr(execution_result_obj, 'output') and execution_result_obj.output is not None:
                tool_result_content = str(execution_result_obj.output)
            elif hasattr(execution_result_obj, 'error') and execution_result_obj.error is not None:
                tool_result_content = f"Error: {str(execution_result_obj.error)}"
            else:
                tool_result_content = str(execution_result_obj) # Fallback

        logger.info(f"Simulate: Tool '{tool_name}' executed. Result: {tool_result_content[:100]}...")
        agent.memory.add_message(Message(role=Role.TOOL, name=tool_name, tool_call_id=tool_call_to_execute.id, content=tool_result_content))
    except Exception as e:
        logger.error(f"Simulate: Error executing tool '{tool_name}': {e}", exc_info=True)
        agent.memory.add_message(Message(role=Role.TOOL, name=tool_name, tool_call_id=tool_call_to_execute.id, content=f"Error executing tool '{tool_name}': {e}"))

    agent.tool_calls = [] # Clear planned calls after execution


async def test_improvisation_and_new_task_flow():
    logger.info("--- Test: Improvisation and New Task Flow ---")
    agent = await Manus.create()

    # === Part 1: Initial Task & Improvisation ===
    logger.info("--- Part 1: Initial task and improvisation ---")
    agent.memory.add_message(Message.user_message("crie dados sinteticos que depois podem ser usados pra simular machine learning com aleatoriedade... gere uma boa amostra de dados"))
    agent.current_step = 1 # Simulate first step of a new run

    # 1a. First think (should trigger automatic reset if checklist existed, then plan decomposition)
    logger.info("Calling think() - Step 1a (Initial, expect auto-reset if needed, then decomp)")
    await agent.think()
    print_agent_memory(agent, "After Think 1a")
    await simulate_tool_execution(agent) # Execute reset (if planned) or first decomp step

    # 1b. Second think (if reset was done, now it should decompose. If no reset, continue decomp)
    agent.current_step +=1
    logger.info(f"Calling think() - Step 1b (current_step={agent.current_step}, expect decomp/AskHuman)")
    await agent.think()
    print_agent_memory(agent, "After Think 1b")

    # We expect AskHuman for parameters now or soon after decomposition
    max_decomp_steps = 5 # Allow a few steps for decomposition
    for i in range(max_decomp_steps):
        if agent.tool_calls and agent.tool_calls[0].function.name == AskHuman().name:
            logger.info(f"Agent planned AskHuman for params at decomp step {i+1}.")
            break
        await simulate_tool_execution(agent)
        agent.current_step += 1
        logger.info(f"Calling think() - Step 1b.{i+1} (current_step={agent.current_step}, decomp/AskHuman)")
        await agent.think()
        print_agent_memory(agent, f"After Think 1b.{i+1}")
    else: # Loop finished without AskHuman
        logger.error("Test Failed: Agent did not ask for parameters within expected decomposition steps.")
        await agent.cleanup()
        return

    # Simulate user responding "tanto faz..." to AskHuman
    # The AskHuman call is in agent.tool_calls from the previous think.
    # We need to simulate its execution and then add the user's response.
    await simulate_tool_execution(agent) # This "executes" AskHuman, adds its question to memory as TOOL role

    user_improvisation_response = "tanto fas tudo isso, capriche e improvite, o que eu quero saber mesmo é o T50"
    agent.memory.add_message(Message.user_message(user_improvisation_response))
    logger.info(f"Added user improvisation response: '{user_improvisation_response}'")
    print_agent_memory(agent, "After user improvisation response")

    # 1c. Think after "tanto faz" - Agent should use improvisation prompt
    agent.current_step +=1
    logger.info(f"Calling think() - Step 1c (current_step={agent.current_step}, after 'tanto faz')")
    await agent.think()
    print_agent_memory(agent, "After Think 1c - Improvisation")

    if agent.tool_calls and any(tc.function.name == AskHuman().name for tc in agent.tool_calls):
        logger.error("Test Failed (Part 1): Agent is STILL planning AskHuman after being told to improvise.")
    else:
        logger.info("Test Passed (Part 1): Agent did NOT plan AskHuman. Should proceed with assumed params.")
        # Check if agent's thought mentions assumed parameters (heuristic)
        last_assistant_msg = next((m for m in reversed(agent.memory.messages) if m.role == Role.ASSISTANT and m.content), None)
        if last_assistant_msg and ("parâmetros padrão" in last_assistant_msg.content.lower() or "vou assumir" in last_assistant_msg.content.lower() or "improvisar" in last_assistant_msg.content.lower()):
            logger.info("LLM thought indicates it will use default/assumed parameters.")
        else:
            logger.warning("LLM thought does not explicitly mention default/assumed parameters, but did not ask again.")


    # === Part 2: Simulate task completion and new directive during final check-in ===
    logger.info("\n--- Part 2: New task directive during final check-in ---")
    # Simulate completion of all checklist items for the improvised task
    # For this test, we'll just manually set the checklist to be complete.
    # In a real scenario, the agent would have executed tools to complete its improvised plan.
    logger.info("Simulating completion of all tasks for the improvised data generation...")
    # Create a dummy checklist file that LOOKS complete for _is_checklist_complete()
    # (This part is tricky without running the full agent loop to populate the checklist)
    # For now, let's assume the agent marks its improvised tasks as done.
    # We'll force agent.periodic_user_check_in(is_final_check=True)

    # To simulate is_final_check, we need _is_checklist_complete to return True
    # We can patch it for this part of the test, or ensure checklist is actually complete

    # Let's assume the agent has finished its improvised task.
    # We will manually trigger the conditions for periodic_user_check_in with is_final_check=True
    agent.current_step = agent.max_steps # Force a periodic check if it wasn't final
    agent._just_resumed_from_feedback = False # Ensure check_in can run

    # Patch _is_checklist_complete to True to force is_final_check path in periodic_user_check_in
    original_is_checklist_complete = agent._is_checklist_complete
    agent._is_checklist_complete = asyncio.coroutine(lambda: True)

    logger.info("Simulating periodic_user_check_in (is_final_check=True)...")
    # The user's response to this will be the new directive.
    # We need to mock AskHuman for periodic_user_check_in
    original_ask_human_execute = agent.available_tools.get_tool(AskHuman().name).execute
    async def mock_ask_human_for_final_check(*args, **kwargs):
        question = kwargs.get('inquire', "Question from periodic_user_check_in")
        logger.info(f"Mock AskHuman (final_check) was asked: '{question[:100]}...'")
        new_directive = "reescreva o checklist e refaça a sua organização pra executar a seguinte tarefa: analisar o arquivo dados_sinteticos.csv e treinar um modelo de regressão."
        logger.info(f"Mock AskHuman (final_check) returning user's new directive: '{new_directive}'")
        return new_directive
    agent.available_tools.get_tool(AskHuman().name).execute = mock_ask_human_for_final_check

    await agent.periodic_user_check_in(is_final_check=True)
    agent.available_tools.get_tool(AskHuman().name).execute = original_ask_human_execute # Restore
    agent._is_checklist_complete = original_is_checklist_complete # Restore

    print_agent_memory(agent, "After periodic_user_check_in with new directive")

    # 2a. Check state after periodic_user_check_in
    if not (agent._new_task_directive_received and agent.state == AgentState.RUNNING):
        logger.error(f"Test Failed (Part 2a): Agent did not correctly set flags/state after new directive. Flag: {agent._new_task_directive_received}, State: {agent.state}")
        await agent.cleanup()
        return
    logger.info("Test Passed (Part 2a): Agent correctly flagged new directive and set state to RUNNING.")

    # 2b. Call think() again. It should detect the flag and plan reset.
    agent.current_step +=1 # Simulate moving to next step cycle
    logger.info(f"Calling think() - Step 2b (current_step={agent.current_step}, after new directive flag)")
    await agent.think()
    print_agent_memory(agent, "After Think 2b - New Directive Reset")

    if agent.tool_calls and agent.tool_calls[0].function.name == ResetCurrentTaskChecklistTool().name:
        logger.info("Test Passed (Part 2b): Agent planned ResetCurrentTaskChecklistTool after new directive.")
        # Simulate execution of reset
        await simulate_tool_execution(agent)
        await print_checklist_status("After Reset for New Directive")

        # 2c. Call think() again. current_step should be 0 internally, then BaseAgent.run increments it to 1.
        # So, the "current_step == 1" logic for initial decomposition should now trigger.
        agent.current_step +=1 # This simulates BaseAgent.run incrementing
        logger.info(f"Calling think() - Step 2c (current_step={agent.current_step}, after reset, expecting new decomp)")
        await agent.think()
        print_agent_memory(agent, "After Think 2c - New Task Decomposition")
        if agent.tool_calls and agent.tool_calls[0].function.name == AddChecklistTaskTool().name:
            logger.info("Test Passed (Part 2c): Agent is now planning to add tasks for the new directive.")
        else:
            logger.error(f"Test Failed (Part 2c): Agent did not plan AddChecklistTaskTool for new directive. Planned: {agent.tool_calls}")
    else:
        logger.error(f"Test Failed (Part 2b): Agent did not plan ResetCurrentTaskChecklistTool. Planned: {agent.tool_calls}")

    await agent.cleanup()
    logger.info("Full flow test finished.")

if __name__ == "__main__":
    # Need to ensure the workspace/checklist_principal_tarefa.md might exist from previous partial runs
    # The script handles creating/resetting it as part of its flow.
    if not os.path.exists(config.workspace_root):
        os.makedirs(config.workspace_root)
    asyncio.run(test_improvisation_and_new_task_flow())
