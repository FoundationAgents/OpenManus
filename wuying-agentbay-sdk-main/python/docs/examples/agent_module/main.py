"""
Basic example of using the Agent module to execute tasks.
This example demonstrates:
- Creating a session with Agent capabilities
- Executing a simple task using natural language
- Handling task results
"""

import os
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams


def main():
    # Get API key from environment variable
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        print("Error: AGENTBAY_API_KEY environment variable not set")
        return

    # Initialize AgentBay client
    print("Initializing AgentBay client...")
    agent_bay = AgentBay(api_key=api_key)

    # Create a session
    print("Creating a new session...")
    params = CreateSessionParams()
    params.image_id = "windows_latest"
    session_result = agent_bay.create(params)

    if session_result.success:
        session = session_result.session
        print(f"Session created with ID: {session.session_id}")

        # Execute a task using the Agent
        task_description = "Calculate the square root of 144"
        print(f"Executing task: {task_description}")

        execution_result = session.agent.execute_task(task_description, max_try_times=5)

        if execution_result.success:
            print("Task completed successfully!")
            print(f"Task ID: {execution_result.task_id}")
            print(f"Task status: {execution_result.task_status}")
            print(f"Task result: {execution_result.task_result}")
        else:
            print(f"Task failed: {execution_result.error_message}")
            if execution_result.task_id:
                print(f"Task ID: {execution_result.task_id}")

        # Clean up - delete the session
        delete_result = agent_bay.delete(session)
        if delete_result.success:
            print("Session deleted successfully")
        else:
            print(f"Failed to delete session: {delete_result.error_message}")
    else:
        print(f"Failed to create session: {session_result.error_message}")


if __name__ == "__main__":
    main()
