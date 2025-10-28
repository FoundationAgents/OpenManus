import pytest
from agentbay import AgentBay
from agentbay.session import Session
from agentbay.model.response import SessionResult


class TestAgentBayGet:
    """Unit tests for AgentBay.get method."""

    def test_get_empty_session_id(self):
        """Test get with empty session ID."""
        agentbay = AgentBay(api_key="test-api-key")

        result = agentbay.get("")

        assert isinstance(result, SessionResult)
        assert not result.success
        assert "session_id is required" in result.error_message

    def test_get_none_session_id(self):
        """Test get with None session ID."""
        agentbay = AgentBay(api_key="test-api-key")

        result = agentbay.get(None)

        assert isinstance(result, SessionResult)
        assert not result.success
        assert "session_id is required" in result.error_message

    def test_get_whitespace_session_id(self):
        """Test get with whitespace-only session ID."""
        agentbay = AgentBay(api_key="test-api-key")

        result = agentbay.get("   ")

        assert isinstance(result, SessionResult)
        assert not result.success
        assert "session_id is required" in result.error_message

    def test_get_method_exists(self):
        """Test that get method exists and has correct signature."""
        agentbay = AgentBay(api_key="test-api-key")

        # Verify method exists
        assert hasattr(agentbay, "get")
        assert callable(getattr(agentbay, "get"))

    def test_get_returns_session_result_type(self):
        """Test that get method returns SessionResult."""
        agentbay = AgentBay(api_key="test-api-key")

        # Check the method exists and is callable
        get_method = getattr(agentbay, "get", None)
        assert get_method is not None
        assert callable(get_method)

        # Test with invalid input to verify it returns SessionResult
        result = agentbay.get("")
        assert isinstance(result, SessionResult)

    def test_get_error_message_format(self):
        """Test error message formatting for various invalid inputs."""
        agentbay = AgentBay(api_key="test-api-key")

        test_cases = [
            ("", "session_id is required"),
            (None, "session_id is required"),
            ("   ", "session_id is required"),
        ]

        for session_id, expected_error in test_cases:
            result = agentbay.get(session_id)
            assert isinstance(result, SessionResult)
            assert not result.success
            assert expected_error in result.error_message


class TestAgentBayGetValidation:
    """Validation tests for AgentBay.get method."""

    def test_get_requires_api_key(self):
        """Test that AgentBay requires an API key."""
        import os
        # Temporarily remove environment variable
        old_api_key = os.environ.get("AGENTBAY_API_KEY")
        if old_api_key:
            del os.environ["AGENTBAY_API_KEY"]

        try:
            with pytest.raises(ValueError):
                AgentBay(api_key="")
        finally:
            # Restore environment variable if it existed
            if old_api_key:
                os.environ["AGENTBAY_API_KEY"] = old_api_key

    def test_get_interface_compliance(self):
        """Test that get method has the expected interface."""
        agentbay = AgentBay(api_key="test-key")

        # Method should exist
        assert hasattr(agentbay, "get")

        # Method should be callable
        get_method = getattr(agentbay, "get")
        assert callable(get_method)


def test_get_documentation():
    """Test that get method is properly documented."""
    agentbay = AgentBay(api_key="test-key")

    get_method = getattr(agentbay, "get", None)
    assert get_method is not None

    # Method should have docstring
    assert get_method.__doc__ is not None
    assert len(get_method.__doc__.strip()) > 0

