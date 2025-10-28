"""Integration test for GetSession API"""
import os
import pytest
from agentbay import AgentBay


def test_get_session_api():
    """
    Integration test for GetSession API.
    Tests that the API correctly retrieves session information.
    """
    # Get API Key from environment
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        pytest.fail("AGENTBAY_API_KEY environment variable is not set")

    # Initialize AgentBay client
    agent_bay = AgentBay(api_key=api_key)

    # Create a session first
    print("Creating a new session for GetSession testing...")
    create_result = agent_bay.create()
    assert create_result.success, f"Failed to create session: {create_result.error_message}"
    session = create_result.session
    session_id = session.session_id
    print(f"Session created with ID: {session_id}")

    try:
        # Test GetSession API
        print("Testing GetSession API...")
        get_session_result = agent_bay.get_session(session_id)

        # Validate response
        assert get_session_result.request_id, "RequestID should not be empty"
        print(f"GetSession RequestID: {get_session_result.request_id}")

        assert get_session_result.http_status_code == 200, f"Expected HttpStatusCode 200, got {get_session_result.http_status_code}"
        assert get_session_result.code == "ok", f"Expected Code 'ok', got '{get_session_result.code}'"
        assert get_session_result.success, "Expected Success to be True"

        # Validate Data field
        assert get_session_result.data is not None, "Data field should not be None"
        assert get_session_result.data.session_id == session_id, f"Expected SessionID {session_id}, got {get_session_result.data.session_id}"
        print(f"Data.success: {get_session_result.data.success}")  # Print actual value
        # Note: Data.success may be False for normal sessions, only check if data is present
        assert get_session_result.data.app_instance_id, "AppInstanceID should not be empty"
        print(f"AppInstanceID: {get_session_result.data.app_instance_id}")
        assert get_session_result.data.resource_id, "ResourceID should not be empty"
        print(f"ResourceID: {get_session_result.data.resource_id}")

        # Validate new fields added from GetSession response
        print(f"VpcResource: {get_session_result.data.vpc_resource}")
        print(f"HttpPort: {get_session_result.data.http_port}")
        print(f"NetworkInterfaceIp: {get_session_result.data.network_interface_ip}")
        print(f"Token: {'***' if get_session_result.data.token else ''}")
        print(f"ResourceUrl: {get_session_result.data.resource_url}")

        # Test get() method which should populate session fields from GetSession
        print("\nTesting AgentBay.get() method...")
        get_result = agent_bay.get(session_id)
        assert get_result.success, f"get() should succeed: {get_result.error_message}"
        assert get_result.request_id, "get() should return request_id"
        print(f"get() RequestID: {get_result.request_id}")

        retrieved_session = get_result.session
        assert retrieved_session is not None, "Session should not be None"
        assert retrieved_session.session_id == session_id, f"Expected SessionID {session_id}, got {retrieved_session.session_id}"
        assert retrieved_session.is_vpc == get_session_result.data.vpc_resource, "Session.is_vpc should match GetSessionData.vpc_resource"
        assert retrieved_session.http_port == get_session_result.data.http_port, "Session.http_port should match GetSessionData.http_port"
        assert retrieved_session.network_interface_ip == get_session_result.data.network_interface_ip, "Session.network_interface_ip should match GetSessionData.network_interface_ip"
        assert retrieved_session.token == get_session_result.data.token, "Session.token should match GetSessionData.token"
        
        # resource_url will have different authcode on each call, so we only check that it's present
        assert retrieved_session.resource_url, "Session.resource_url should be present"
        assert "resourceId=" in retrieved_session.resource_url, "Session.resource_url should contain resourceId"
        print("AgentBay.get() method test passed")

        print("\nGetSession API test passed successfully")

    finally:
        # Clean up: Delete the session
        print("Cleaning up: Deleting the session...")
        delete_result = session.delete()
        if delete_result.success:
            print(f"Session {session_id} deleted successfully")
        else:
            print(f"Warning: Failed to delete session: {delete_result.error_message}")


if __name__ == "__main__":
    test_get_session_api()

