import asyncio
import os
from app.agent.manus import Manus
from app.config import config
from app.memory.base import Message # Corrected import
from app.schema import AgentState, Role # Corrected import

# Minimal configuration for the test
# This path needs to be accessible by the script when it runs.
# /app/ is the root of the repository where the app code resides.
config.workspace_root = "/app/manus_test_workspace"
os.makedirs(config.workspace_root, exist_ok=True)

# Create a dummy checklist file
checklist_path = os.path.join(config.workspace_root, "checklist_principal_tarefa.md")
with open(checklist_path, "w") as f:
    f.write("- Tarefa 1\n- Tarefa 2")

async def main():
    print("Instantiating Manus agent...")
    agent = None  # Define agent here for cleanup
    try:
        # Manus.create() is async and handles initialization
        agent = await Manus.create(
            memory_messages=[Message(role=Role.USER, content="Initial task for testing")],
            max_steps=5 # Set max_steps to trigger check-in logic if needed by should_request_feedback
        )
        agent.current_step = 5 # Align current_step with max_steps to trigger the check-in via should_request_feedback

        print("Manus agent instantiated.")
        print(f"Available tools: {[tool.name for tool in agent.available_tools]}")

        # Directly test periodic_user_check_in
        print("Calling periodic_user_check_in...")
        # Mock the AskHuman tool to prevent blocking
        original_ask_human_execute = agent.available_tools.get_tool("ask_human").execute
        async def mock_ask_human_execute(*args, **kwargs):
            print("Mock AskHuman called, returning 'continuar'")
            # Simulate adding user response to memory, as AskHuman tool might do
            agent.memory.add_message(Message(role=Role.USER, content="continuar"))
            return "continuar"
        agent.available_tools.get_tool("ask_human").execute = mock_ask_human_execute

        continue_execution = await agent.periodic_user_check_in()
        print(f"periodic_user_check_in call completed. Result: {continue_execution}")
        print(f"Agent state after check-in: {agent.state}")

        # Also test should_request_feedback which calls periodic_user_check_in
        print("Calling should_request_feedback...")
        agent._just_resumed_from_feedback = False # Reset flag
        agent.state = AgentState.RUNNING # Reset state
        should_pause = await agent.should_request_feedback()
        print(f"should_request_feedback call completed. Result: {should_pause}")
        print(f"Agent state after should_request_feedback: {agent.state}")

        print("Test completed successfully, no TypeError observed during StrReplaceEditor access.")

    except TypeError as e:
        if "cannot pickle 'socket' object" in str(e):
            print(f"TEST FAILED: Original TypeError was observed: {e}")
        else:
            print(f"TEST FAILED: An unexpected TypeError occurred: {e}")
            import traceback
            traceback.print_exc()
    except Exception as e:
        print(f"TEST FAILED: An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if agent:
            print("Cleaning up agent...")
            await agent.cleanup()
        # Clean up dummy workspace
        if os.path.exists(checklist_path):
            os.remove(checklist_path)
        # Check if manus_test_workspace exists and if it's empty before removing
        if os.path.exists(config.workspace_root):
            if not os.listdir(config.workspace_root):
                os.rmdir(config.workspace_root)
            else:
                # If not empty, perhaps remove the specific file created if it's known
                # For now, just log it.
                print(f"Workspace root {config.workspace_root} not empty, not removing directory.")
        else:
            print(f"Workspace root {config.workspace_root} does not exist, no need to remove.")


if __name__ == "__main__":
    asyncio.run(main())
