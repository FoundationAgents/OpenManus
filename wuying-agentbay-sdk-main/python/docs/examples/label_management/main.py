#!/usr/bin/env python3
"""
Label Management Example

This example demonstrates how to use the label management features
of the Wuying AgentBay SDK.
"""

import os
import sys

from agentbay import AgentBay
from agentbay.exceptions import AgentBayError
from agentbay.session_params import CreateSessionParams


def main():
    # Get API key from environment variable or use a default value for testing
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        api_key = "akm-xxx"  # Replace with your actual API key for testing
        print(
            "Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for production use."
        )

    session1 = None
    session2 = None

    try:
        # Initialize the AgentBay client
        agent_bay = AgentBay(api_key=api_key)

        # Create a new session with labels (recommended approach)
        print("\nCreating a new session with labels...")
        params = CreateSessionParams(labels={
            "purpose": "demo",
            "feature": "label-management",
            "version": "1.0",
        })
        session_result = agent_bay.create(params)
        session1 = session_result.session
        print(f"Session created with ID: {session1.session_id}")
        print(f"Request ID: {session_result.request_id}")

        # Get labels for the session
        print("\nGetting labels for the session...")
        labels_result = session1.get_labels()
        print(f"Session labels: {labels_result.data}")
        print(f"Request ID: {labels_result.request_id}")

        # Create another session with different labels (recommended approach)
        print("\nCreating another session with different labels...")
        params = CreateSessionParams(labels={
            "purpose": "demo",
            "feature": "other-feature",
            "version": "2.0",
        })
        session_result = agent_bay.create(params)
        session2 = session_result.session
        print(f"Session created with ID: {session2.session_id}")
        print(f"Request ID: {session_result.request_id}")

        # Update labels for the second session
        print("\nUpdating labels for the second session...")
        set_labels_result = session2.set_labels(
            {
                "purpose": "demo",
                "feature": "label-management",
                "version": "2.0",
                "status": "active",
            }
        )
        print(f"Labels updated successfully: {set_labels_result.success}")
        print(f"Request ID: {set_labels_result.request_id}")

        # Get updated labels for the second session
        print("\nGetting updated labels for the second session...")
        labels_result = session2.get_labels()
        print(f"Updated session labels: {labels_result.data}")
        print(f"Request ID: {labels_result.request_id}")


        # List sessions by label
        print("\nListing sessions with purpose=demo and feature=label-management...")
        filtered_result = agent_bay.list(
            labels={"purpose": "demo", "feature": "label-management"},
            limit=100
        )
        session_ids = filtered_result.session_ids
        print(f"Found {len(session_ids)} matching sessions")
        print(f"Request ID: {filtered_result.request_id}")
        for i, session_id in enumerate(session_ids):
            print(f"Matching session {i + 1} ID: {session_id}")
            session_result = agent_bay.get(session_id)
            if session_result.success:
                labels_result = session_result.session.get_labels()
                print(f"Labels: {labels_result.data}")

        # Delete the sessions
        print("\nDeleting the sessions...")
        delete_result1 = agent_bay.delete(session1)
        print(
            f"Session {session1.session_id} deleted successfully: "
            f"{delete_result1.success}"
        )
        print(f"Request ID: {delete_result1.request_id}")
        session1 = None  # Clear reference to avoid deletion error

        delete_result2 = agent_bay.delete(session2)
        print(
            f"Session {session2.session_id} deleted successfully: "
            f"{delete_result2.success}"
        )
        print(f"Request ID: {delete_result2.request_id}")
        session2 = None  # Clear reference to avoid deletion error

    except AgentBayError as e:
        print(f"Error: {e}")

        try:
            if session1:
                agent_bay.delete(session1)
            if session2:
                agent_bay.delete(session2)
        except Exception as cleanup_error:
            print(f"Error during cleanup: {cleanup_error}")

        sys.exit(1)


if __name__ == "__main__":
    main() 