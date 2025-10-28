#!/usr/bin/env python3

import os

from agentbay import AgentBay,ContextSync,SyncPolicy
from agentbay.exceptions import AgentBayError
from agentbay.session_params import CreateSessionParams

def main():
    # Initialize the AgentBay client
    # You can provide the API key as a parameter or set the AGENTBAY_API_KEY
    # environment variable
    api_key = os.environ.get("AGENTBAY_API_KEY")
    if not api_key:
        api_key = "akm-xxx"  # Replace with your actual API key

    session = None
    try:
        agent_bay = AgentBay(api_key=api_key)

        # Example 1: List all contexts
        print("\nExample 1: Listing all contexts...")
        try:
            result = agent_bay.context.list()
            print(f"Request ID: {result.request_id}")
            if result.success:
                print(f"Found {len(result.contexts)} contexts:")
                for context in result.contexts:
                    print(
                        f"- {context.name} ({context.id}): state={context.state}, os={context.os_type}"
                    )
            else:
                print("Failed to list contexts")
        except AgentBayError as e:
            print(f"Error listing contexts: {e}")

        # Example 2: Get a context (create if it doesn't exist)
        print("\nExample 2: Getting a context (creating if it doesn't exist)...")
        context_name = "my-test-context"
        try:
            result = agent_bay.context.get(context_name, create=True)
            print(f"Request ID: {result.request_id}")
            if result.success and result.context:
                context = result.context
                print(f"Got context: {context.name} ({context.id})")
            else:
                print("Context not found and could not be created")
                return
        except AgentBayError as e:
            print(f"Error getting context: {e}")
            return

        # Example 3: Create a session with the context
        print("\nExample 3: Creating a session with the context...")
        try:
            params = CreateSessionParams(
                labels={"username": "alice", "project": "my-project"},
            )
            # Fix: context_syncs should be a list, not a single ContextSync object
            params.context_syncs = [ContextSync.new(
                context.id,
                "/tmp/shared",
                SyncPolicy.default()
            )]
            session_result = agent_bay.create(params)
            session = session_result.session
            print(f"Session created with ID: {session.session_id}")
            print(f"Request ID: {session_result.request_id}")
            print("Note: The create() method automatically monitored the context status")
            print("and only returned after all context operations were complete or reached maximum retries.")
        except AgentBayError as e:
            print(f"Error creating session: {e}")
            return

        # Example 4: Update the context
        print("\nExample 4: Updating the context...")
        try:
            context.name = "renamed-test-context"
            result = agent_bay.context.update(context)
            print(f"Request ID: {result.request_id}")
            if not result.success:
                print(f"Context update was not successful: {result.error_message}")
            else:
                print(f"Context updated successfully to: {context.name}")
        except AgentBayError as e:
            print(f"Error updating context: {e}")

        # Clean up
        print("\nCleaning up...")

        # Delete the session with context synchronization
        try:
            if session:
                print("Deleting the session with context synchronization...")
                delete_result = agent_bay.delete(session, sync_context=True)
                print(f"Session deletion request ID: {delete_result.request_id}")
                print(f"Session deletion success: {delete_result.success}")
                print("Note: The delete() method synchronized the context before session deletion")
                print("and monitored all context operations until completion.")
                session = None

                # Alternative method using session's delete method:
                # delete_result = session.delete(sync_context=True)
        except AgentBayError as e:
            print(f"Error deleting session: {e}")

        # Delete the context
        print("Deleting the context...")
        try:
            result = agent_bay.context.delete(context)
            print(f"Context deletion request ID: {result.request_id}")
            if result.success:
                print("Context deleted successfully")
            else:
                print(f"Failed to delete context: {result.error_message}")
        except AgentBayError as e:
            print(f"Error deleting context: {e}")

    except Exception as e:
        print(f"Error initializing AgentBay: {e}")
        if session:
            try:
                agent_bay.delete(session)
                print("Session deleted during cleanup")
            except AgentBayError as delete_error:
                print(f"Error deleting session during cleanup: {delete_error}")

if __name__ == "__main__":
    main()
