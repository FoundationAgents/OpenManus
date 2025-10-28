import os
import sys
import unittest
import typing
from agentbay.session import Session
from agentbay.session_params import CreateSessionParams
from agentbay.exceptions import SessionError

from agentbay import AgentBay

# Add the parent directory to the path so we can import the agentbay package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_test_api_key():
    api_key = os.environ.get("AGENTBAY_API_KEY")
    if not api_key:
        api_key = "akm-xxx"  # Replace with your test API key
        print(
            "Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for testing."
        )
    return api_key


class TestSessionInfoAndLink(unittest.TestCase):
    """Integration test for session info and get_link APIs."""

    @classmethod
    def setUpClass(cls):
        api_key = get_test_api_key()
        cls.agent_bay = AgentBay(api_key=api_key)
        print("Creating a new session for info/link testing...")
        # Use browser_latest image for get_link compatibility
        params = CreateSessionParams(image_id="browser_latest")
        result = cls.agent_bay.create(params=params)
        cls.session = getattr(result, "session", None)
        print(f"Session created with ID: {getattr(cls.session, 'session_id', None)}")
        print(f"Request ID: {getattr(result, 'request_id', None)}")

    @classmethod
    def tearDownClass(cls):
        print("Cleaning up: Deleting the session...")
        try:
            if cls.session is not None:
                result = cls.agent_bay.delete(cls.session)
                print(
                    f"Session deleted. Success: {getattr(result, 'success', None)}, Request ID: {getattr(result, 'request_id', None)}"
                )
            else:
                print("No session to delete.")
        except Exception as e:
            print(f"Warning: Error deleting session: {e}")

    def test_info(self):
        """Test session.info() returns expected fields."""
        self.assertIsNotNone(self.session, "Session was not created successfully.")
        session: Session = typing.cast(Session, self.session)
        print("Calling session.info()...")
        result = session.info()
        self.assertTrue(result.success, "session.info() did not succeed")
        info = result.data
        print(f"SessionInfo: {info.__dict__}")
        self.assertTrue(hasattr(info, "session_id"))
        self.assertTrue(info.session_id)
        self.assertTrue(hasattr(info, "resource_url"))
        self.assertTrue(info.resource_url)
        self.assertTrue(hasattr(info, "ticket"))
        # ticket may be empty depending on backend, but should exist
        self.assertTrue(hasattr(info, "app_id"))
        self.assertTrue(hasattr(info, "auth_code"))
        self.assertTrue(hasattr(info, "connection_properties"))
        self.assertTrue(hasattr(info, "resource_id"))
        self.assertTrue(hasattr(info, "resource_type"))

    def test_get_link(self):
        """Test session.get_link() returns a valid URL."""
        self.assertIsNotNone(self.session, "Session was not created successfully.")
        session: Session = typing.cast(Session, self.session)
        print("Calling session.get_link()...")
        result = session.get_link()
        self.assertTrue(result.success, "session.get_link() did not succeed")
        url = result.data
        print(f"Session link URL: {url}")
        self.assertIsInstance(url, str)
        self.assertTrue(
            url.startswith("http") or url.startswith("wss") or url.startswith("ws"),
            "Returned link does not look like a URL",
        )

    def test_get_link_with_valid_port(self):
        """Test session.get_link() with valid port returns a valid URL."""
        self.assertIsNotNone(self.session, "Session was not created successfully.")
        session: Session = typing.cast(Session, self.session)
        print("Calling session.get_link()...")
        result = session.get_link()
        self.assertTrue(result.success, "session.get_link() did not succeed")
        url = result.data
        print(f"Session link URL: {url}")
        self.assertIsInstance(url, str)
        self.assertTrue(
            url.startswith("http") or url.startswith("wss") or url.startswith("ws"),
            "Returned link does not look like a URL",
        )

        # Test with port in valid range [30100, 30199]
        valid_ports = [30100, 30150, 30199]

        for port in valid_ports:
            with self.subTest(port=port):
                print(f"Calling session.get_link() with port {port}...")
                result = session.get_link(port=port)
                self.assertTrue(result.success, f"session.get_link(port={port}) did not succeed")
                url = result.data
                print(f"Session link URL with port {port}: {url}")
                self.assertIsInstance(url, str)
                self.assertTrue(
                    url.startswith("http") or url.startswith("wss") or url.startswith("ws"),
                    f"Returned link with port {port} does not look like a URL",
                )

    def test_get_link_with_invalid_port_below_range(self):
        """Test session.get_link() with port below valid range raises SessionError."""
        self.assertIsNotNone(self.session, "Session was not created successfully.")
        session: Session = typing.cast(Session, self.session)

        # Test with port below valid range
        invalid_port = 30099
        print(f"Calling session.get_link() with invalid port {invalid_port}...")

        try:
            result = session.get_link(port=invalid_port)
            # If we get here, no exception was raised
            print(f"ERROR: No exception was raised! Result: {result}")
            print(f"Result success: {result.success}")
            print(f"Result data: {result.data}")
            self.fail(f"Expected SessionError to be raised, but got result: {result}")
        except SessionError as e:
            # This is what we expect
            error_message = str(e)
            print(f"Expected SessionError raised: {error_message}")

            # Verify the error message matches the expected format (same as TypeScript version)
            expected_message = f"Invalid port value: {invalid_port}. Port must be an integer in the range [30100, 30199]."
            self.assertIn(expected_message, error_message)
        except Exception as e:
            # Some other exception was raised
            print(f"ERROR: Unexpected exception type: {type(e).__name__}")
            print(f"ERROR: Unexpected exception message: {str(e)}")
            self.fail(f"Expected SessionError, but got {type(e).__name__}: {str(e)}")

    def test_get_link_with_invalid_port_above_range(self):
        """Test session.get_link() with port above valid range raises SessionError."""
        self.assertIsNotNone(self.session, "Session was not created successfully.")
        session: Session = typing.cast(Session, self.session)

        # Test with port above valid range
        invalid_port = 30200
        print(f"Calling session.get_link() with invalid port {invalid_port}...")

        with self.assertRaises(SessionError) as context:
            session.get_link(port=invalid_port)

        error_message = str(context.exception)
        print(f"Expected SessionError raised: {error_message}")

        # Verify the error message matches the expected format (same as TypeScript version)
        expected_message = f"Invalid port value: {invalid_port}. Port must be an integer in the range [30100, 30199]."
        self.assertIn(expected_message, error_message)

    def test_get_link_with_invalid_port_non_integer(self):
        """Test session.get_link() with non-integer port raises SessionError."""
        self.assertIsNotNone(self.session, "Session was not created successfully.")
        session: Session = typing.cast(Session, self.session)

        # Test with non-integer port
        invalid_port = 30150.5
        print(f"Calling session.get_link() with non-integer port {invalid_port}...")

        with self.assertRaises(SessionError) as context:
            session.get_link(port=invalid_port)

        error_message = str(context.exception)
        print(f"Expected SessionError raised: {error_message}")

        # Verify the error message matches the expected format (same as TypeScript version)
        expected_message = f"Invalid port value: {invalid_port}. Port must be an integer in the range [30100, 30199]."
        self.assertIn(expected_message, error_message)
