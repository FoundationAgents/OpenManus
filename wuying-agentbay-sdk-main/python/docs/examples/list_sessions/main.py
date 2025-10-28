"""
AgentBay List Sessions Example

This example demonstrates how to use the list() API to query sessions with filtering and pagination.

Features demonstrated:
1. List all sessions
2. List sessions with label filtering
3. List sessions with pagination
4. Handle pagination to retrieve all results

Usage:
    python main.py
"""

import os
import sys
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams


def main():
    # Get API key from environment variable
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        print("Error: AGENTBAY_API_KEY environment variable not set")
        print("Please set your API key: export AGENTBAY_API_KEY='your-api-key'")
        sys.exit(1)

    # Initialize AgentBay client
    agent_bay = AgentBay(api_key=api_key)
    print("✅ AgentBay client initialized")

    # Create some test sessions with labels for demonstration
    print("\n📝 Creating test sessions...")
    test_sessions = []

    try:
        # Create session 1 with labels
        params1 = CreateSessionParams(
            labels={
                "project": "list-demo",
                "environment": "dev",
                "owner": "demo-user",
            }
        )
        result1 = agent_bay.create(params1)
        if result1.success:
            test_sessions.append(result1.session)
            print(f"✅ Created session 1: {result1.session.session_id}")
            print(f"   Request ID: {result1.request_id}")

        # Create session 2 with labels
        params2 = CreateSessionParams(
            labels={
                "project": "list-demo",
                "environment": "staging",
                "owner": "demo-user",
            }
        )
        result2 = agent_bay.create(params2)
        if result2.success:
            test_sessions.append(result2.session)
            print(f"✅ Created session 2: {result2.session.session_id}")
            print(f"   Request ID: {result2.request_id}")

        # Create session 3 with labels
        params3 = CreateSessionParams(
            labels={
                "project": "list-demo",
                "environment": "prod",
                "owner": "demo-user",
            }
        )
        result3 = agent_bay.create(params3)
        if result3.success:
            test_sessions.append(result3.session)
            print(f"✅ Created session 3: {result3.session.session_id}")
            print(f"   Request ID: {result3.request_id}")

    except Exception as e:
        print(f"❌ Error creating test sessions: {e}")
        sys.exit(1)

    try:
        # Example 1: List all sessions (no filter)
        print("\n" + "=" * 60)
        print("Example 1: List all sessions (no filter)")
        print("=" * 60)

        result = agent_bay.list()
        if result.success:
            print(f"✅ Found {result.total_count} total sessions")
            print(f"📄 Showing {len(result.session_ids)} session IDs on this page")
            print(f"🔑 Request ID: {result.request_id}")
            print(f"📊 Max results per page: {result.max_results}")

            # Display first few sessions
            for i, session_id in enumerate(result.session_ids[:3], 1):
                print(f"   {i}. Session ID: {session_id}")
        else:
            print(f"❌ Error: {result.error_message}")

        # Example 2: List sessions with specific label
        print("\n" + "=" * 60)
        print("Example 2: List sessions filtered by project label")
        print("=" * 60)

        result = agent_bay.list(labels={"project": "list-demo"})
        if result.success:
            print(f"✅ Found {result.total_count} sessions with project='list-demo'")
            print(f"📄 Showing {len(result.session_ids)} session IDs on this page")
            print(f"🔑 Request ID: {result.request_id}")

            for i, session_id in enumerate(result.session_ids, 1):
                print(f"   {i}. Session ID: {session_id}")
        else:
            print(f"❌ Error: {result.error_message}")

        # Example 3: List sessions with multiple labels
        print("\n" + "=" * 60)
        print("Example 3: List sessions filtered by multiple labels")
        print("=" * 60)

        result = agent_bay.list(
            labels={
                "project": "list-demo",
                "environment": "dev",
            }
        )
        if result.success:
            print(
                f"✅ Found {result.total_count} sessions with project='list-demo' AND environment='dev'"
            )
            print(f"📄 Showing {len(result.session_ids)} session IDs")
            print(f"🔑 Request ID: {result.request_id}")

            for i, session_id in enumerate(result.session_ids, 1):
                print(f"   {i}. Session ID: {session_id}")
        else:
            print(f"❌ Error: {result.error_message}")

        # Example 4: List sessions with pagination
        print("\n" + "=" * 60)
        print("Example 4: List sessions with pagination (2 per page)")
        print("=" * 60)

        # Get first page
        result_page1 = agent_bay.list(labels={"project": "list-demo"}, page=1, limit=2)
        if result_page1.success:
            print(f"📄 Page 1:")
            print(f"   Total count: {result_page1.total_count}")
            print(f"   Session IDs on this page: {len(result_page1.session_ids)}")
            print(f"   Request ID: {result_page1.request_id}")

            for i, session_id in enumerate(result_page1.session_ids, 1):
                print(f"   {i}. Session ID: {session_id}")

            # Get second page if available
            if result_page1.next_token:
                print(f"\n   Has next page (token: {result_page1.next_token[:20]}...)")

                result_page2 = agent_bay.list(
                    labels={"project": "list-demo"}, page=2, limit=2
                )
                if result_page2.success:
                    print(f"\n📄 Page 2:")
                    print(f"   Session IDs on this page: {len(result_page2.session_ids)}")
                    print(f"   Request ID: {result_page2.request_id}")

                    for i, session_id in enumerate(result_page2.session_ids, 1):
                        print(f"   {i}. Session ID: {session_id}")
        else:
            print(f"❌ Error: {result_page1.error_message}")

        # Example 5: Retrieve all sessions across multiple pages
        print("\n" + "=" * 60)
        print("Example 5: Retrieve all session IDs with pagination loop")
        print("=" * 60)

        all_session_ids = []
        page = 1
        limit = 2

        while True:
            result = agent_bay.list(labels={"owner": "demo-user"}, page=page, limit=limit)

            if not result.success:
                print(f"❌ Error on page {page}: {result.error_message}")
                break

            print(f"📄 Page {page}: Found {len(result.session_ids)} session IDs")
            all_session_ids.extend(result.session_ids)

            # Break if no more pages
            if not result.next_token:
                break

            page += 1

        print(f"\n✅ Retrieved {len(all_session_ids)} total session IDs across {page} pages")
        for i, session_id in enumerate(all_session_ids, 1):
            print(f"   {i}. Session ID: {session_id}")

    finally:
        # Clean up: Delete test sessions
        print("\n" + "=" * 60)
        print("🧹 Cleaning up test sessions...")
        print("=" * 60)

        for session in test_sessions:
            try:
                delete_result = agent_bay.delete(session)
                if delete_result.success:
                    print(f"✅ Deleted session: {session.session_id}")
                    print(f"   Request ID: {delete_result.request_id}")
                else:
                    print(
                        f"❌ Failed to delete session {session.session_id}: {delete_result.error_message}"
                    )
            except Exception as e:
                print(f"❌ Error deleting session {session.session_id}: {e}")

    print("\n✨ Demo completed successfully!")


if __name__ == "__main__":
    main()

