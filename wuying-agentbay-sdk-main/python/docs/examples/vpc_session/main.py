"""
Basic example of creating and using a VPC session.
This example demonstrates:
- Creating a VPC session with specific parameters
- Using FileSystem operations in a VPC session
- Using Command execution in a VPC session
- Proper session cleanup
"""

import os
import time
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

    # Create a VPC session
    print("Creating a VPC session...")
    params = CreateSessionParams(
        image_id="linux_latest",
        is_vpc=True,
        labels={
            "test-type": "vpc-basic-example",
            "purpose": "demonstration",
            "timestamp": str(int(time.time()))
        }
    )

    session_result = agent_bay.create(params)

    if not session_result.success:
        print(f"Failed to create VPC session: {session_result.error_message}")
        return

    session = session_result.session
    print(f"VPC session created successfully with ID: {session.session_id}")

    try:
        # Test FileSystem operations
        print("\n--- Testing FileSystem operations ---")
        test_file_path = "/tmp/vpc_example_test.txt"
        test_content = f"Hello from VPC session! Created at {time.strftime('%Y-%m-%d %H:%M:%S')}"

        # Write file
        write_result = session.file_system.write_file(test_file_path, test_content)
        if write_result.success:
            print("✓ File written successfully")
        else:
            print(f"⚠ File write failed: {write_result.error_message}")

        # Read file
        read_result = session.file_system.read_file(test_file_path)
        if read_result.success:
            print(f"✓ File read successfully. Content: {read_result.content}")
        else:
            print(f"⚠ File read failed: {read_result.error_message}")

        # Test Command operations
        print("\n--- Testing Command operations ---")

        # Get current user
        cmd_result = session.command.execute_command("whoami")
        if cmd_result.success:
            print(f"✓ Current user: {cmd_result.output.strip()}")
        else:
            print(f"⚠ Command execution failed: {cmd_result.error_message}")

        # List directory contents
        cmd_result = session.command.execute_command("ls -la /tmp")
        if cmd_result.success:
            print("✓ Directory listing successful")
            print(f"  Output:\n{cmd_result.output}")
        else:
            print(f"⚠ Directory listing failed: {cmd_result.error_message}")

    finally:
        # Clean up - delete the session
        print("\n--- Cleaning up ---")
        delete_result = agent_bay.delete(session)
        if delete_result.success:
            print("✓ VPC session deleted successfully")
        else:
            print(f"⚠ Failed to delete VPC session: {delete_result.error_message}")

if __name__ == "__main__":
    main()
