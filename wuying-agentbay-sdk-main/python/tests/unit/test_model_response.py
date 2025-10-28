import unittest
from unittest.mock import MagicMock

from agentbay.model import (
    ApiResponse,
    BoolResult,
    DeleteResult,
    OperationResult,
    SessionListResult,
    SessionResult,
    extract_request_id,
)


class TestApiResponse(unittest.TestCase):
    """Test the base ApiResponse class"""

    def test_api_response_initialization(self):
        """Test initialization of ApiResponse"""
        request_id = "test-request-id"
        response = ApiResponse(request_id)

        self.assertEqual(response.request_id, request_id)
        self.assertEqual(response.get_request_id(), request_id)


class TestSessionResult(unittest.TestCase):
    """Test the SessionResult class"""

    def test_session_result_initialization(self):
        """Test initialization of SessionResult"""
        request_id = "session-request-id"
        session = MagicMock()
        result = SessionResult(
            request_id, success=True, error_message="", session=session
        )

        self.assertEqual(result.request_id, request_id)
        self.assertTrue(result.success)
        self.assertEqual(result.session, session)


class TestSessionListResult(unittest.TestCase):
    """Test the SessionListResult class"""

    def test_session_list_result_initialization(self):
        """Test initialization of SessionListResult"""
        request_id = "session-list-request-id"
        session_ids = ["session-1", "session-2"]
        result = SessionListResult(
            request_id=request_id, success=True, session_ids=session_ids
        )

        self.assertEqual(result.request_id, request_id)
        self.assertEqual(len(result.session_ids), 2)
        self.assertEqual(result.session_ids, session_ids)

    def test_session_list_result_defaults(self):
        """Test default values of SessionListResult"""
        result = SessionListResult()

        self.assertEqual(result.request_id, "")
        self.assertFalse(result.success)
        self.assertEqual(result.session_ids, [])
        self.assertEqual(result.error_message, "")


class TestDeleteResult(unittest.TestCase):
    """Test the DeleteResult class"""

    def test_delete_result_initialization(self):
        """Test initialization of DeleteResult"""
        request_id = "delete-request-id"
        success = True
        error_message = ""
        result = DeleteResult(request_id, success, error_message)

        self.assertEqual(result.request_id, request_id)
        self.assertTrue(result.success)
        self.assertEqual(result.error_message, error_message)

    def test_delete_result_failure(self):
        """Test failure case of DeleteResult"""
        request_id = "delete-failed-id"
        success = False
        error_message = "Delete operation failed"
        result = DeleteResult(request_id, success, error_message)

        self.assertEqual(result.request_id, request_id)
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, error_message)


class TestOperationResult(unittest.TestCase):
    """Test the OperationResult class"""

    def test_operation_result_initialization(self):
        """Test initialization of OperationResult"""
        request_id = "operation-request-id"
        success = True
        data = {"key": "value"}
        error_message = ""
        result = OperationResult(request_id, success, data, error_message)

        self.assertEqual(result.request_id, request_id)
        self.assertTrue(result.success)
        self.assertEqual(result.data, data)
        self.assertEqual(result.error_message, error_message)

    def test_operation_result_defaults(self):
        """Test default values of OperationResult"""
        result = OperationResult()

        self.assertEqual(result.request_id, "")
        self.assertFalse(result.success)
        self.assertIsNone(result.data)
        self.assertEqual(result.error_message, "")


class TestBoolResult(unittest.TestCase):
    """Test the BoolResult class"""

    def test_bool_result_initialization(self):
        """Test initialization of BoolResult"""
        request_id = "bool-request-id"
        success = True
        data = True
        error_message = ""
        result = BoolResult(request_id, success, data, error_message)

        self.assertEqual(result.request_id, request_id)
        self.assertTrue(result.success)
        self.assertTrue(result.data)
        self.assertEqual(result.error_message, error_message)

    def test_bool_result_failure(self):
        """Test failure case of BoolResult"""
        request_id = "bool-failed-id"
        success = False
        data = None
        error_message = "Boolean operation failed"
        result = BoolResult(request_id, success, data, error_message)

        self.assertEqual(result.request_id, request_id)
        self.assertFalse(result.success)
        self.assertIsNone(result.data)
        self.assertEqual(result.error_message, error_message)


class TestExtractRequestId(unittest.TestCase):
    """Test the extract_request_id function"""

    def test_extract_request_id_success(self):
        """Test successfully extracting RequestId from a response"""
        response = MagicMock()
        response.to_map.return_value = {"body": {"RequestId": "extracted-request-id"}}

        request_id = extract_request_id(response)
        self.assertEqual(request_id, "extracted-request-id")

    def test_extract_request_id_missing(self):
        """Test handling case where RequestId is missing"""
        response = MagicMock()
        response.to_map.return_value = {"body": {}}

        request_id = extract_request_id(response)
        self.assertEqual(request_id, "")

    def test_extract_request_id_none_response(self):
        """Test handling None response"""
        request_id = extract_request_id(None)
        self.assertEqual(request_id, "")

    def test_extract_request_id_exception(self):
        """Test handling exception case"""
        response = MagicMock()
        response.to_map.side_effect = AttributeError("No to_map method")

        request_id = extract_request_id(response)
        self.assertEqual(request_id, "")


if __name__ == "__main__":
    unittest.main()
