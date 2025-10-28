"""
Example demonstrating how to use the Get API to retrieve a session by its ID.

This example shows:
1. Creating a session
2. Retrieving the session using the Get API
3. Using the session for operations
4. Cleaning up resources
"""

import os
from agentbay import AgentBay


def main():
    # Get API key from environment variable
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        raise ValueError("AGENTBAY_API_KEY environment variable is not set")

    # Initialize AgentBay client
    agentbay = AgentBay(api_key=api_key)

    # For demonstration, first create a session
    print("Creating a session...")
    create_result = agentbay.create()
    if not create_result.success:
        raise RuntimeError(f"Failed to create session: {create_result.error_message}")

    session_id = create_result.session.session_id
    print(f"Created session with ID: {session_id}")

    # Retrieve the session by ID using Get API
    print("\nRetrieving session using Get API...")
    get_result = agentbay.get(session_id)
    
    if not get_result.success:
        raise RuntimeError(f"Failed to get session: {get_result.error_message}")
    
    session = get_result.session

    # Display session information
    print("Successfully retrieved session:")
    print(f"  Session ID: {session.session_id}")
    print(f"  Request ID: {get_result.request_id}")

    # The session object can be used for further operations
    # For example, you can execute commands, work with files, etc.
    print("\nSession is ready for use")

    # Clean up: Delete the session when done
    print("\nCleaning up...")
    delete_result = session.delete()

    if delete_result.success:
        print(f"Session {session_id} deleted successfully")
    else:
        print(f"Failed to delete session {session_id}")


if __name__ == "__main__":
    main()

