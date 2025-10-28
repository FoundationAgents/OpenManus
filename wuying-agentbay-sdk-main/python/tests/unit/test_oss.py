import unittest
from unittest.mock import MagicMock

from agentbay.model import OperationResult
from agentbay.oss.oss import Oss


class TestOss(unittest.TestCase):
    def setUp(self):
        self.mock_session = MagicMock()
        self.oss = Oss(self.mock_session)

    def test_env_init_success(self):
        # Create a mock OperationResult
        mock_result = OperationResult(
            request_id="test-request-id",
            success=True,
            data="Set oss config successfully",
            error_message="",
        )
        self.oss._call_mcp_tool = MagicMock(return_value=mock_result)

        result = self.oss.env_init("key_id", "key_secret", endpoint="test_endpoint")

        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(result.client_config, "Set oss config successfully")
        self.assertEqual(result.error_message, "")

    def test_env_init_failure(self):
        # Create a mock failed OperationResult
        mock_result = OperationResult(
            request_id="test-request-id",
            success=False,
            data=None,
            error_message="Failed to create OSS client",
        )
        self.oss._call_mcp_tool = MagicMock(return_value=mock_result)

        result = self.oss.env_init("key_id", "key_secret")

        self.assertFalse(result.success)
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(result.client_config, {})
        self.assertEqual(result.error_message, "Failed to create OSS client")

    def test_upload_success(self):
        """
        Test the upload method to ensure it succeeds with valid input.
        """
        mock_result = OperationResult(
            request_id="test-request-id",
            success=True,
            data="Upload success",
            error_message="",
        )
        self.oss._call_mcp_tool = MagicMock(return_value=mock_result)

        result = self.oss.upload("test_bucket", "test_object", "test_path")

        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(result.content, "Upload success")
        self.assertEqual(result.error_message, "")

    def test_upload_failure(self):
        """
        Test the upload method to ensure it handles failure correctly.
        """
        error_msg = "Upload failed: The OSS Access Key Id you provided does not exist in our records."
        mock_result = OperationResult(
            request_id="test-request-id",
            success=False,
            data=None,
            error_message=error_msg,
        )
        self.oss._call_mcp_tool = MagicMock(return_value=mock_result)

        result = self.oss.upload("test_bucket", "test_object", "test_path")

        self.assertFalse(result.success)
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(result.content, "")
        self.assertEqual(result.error_message, error_msg)

    def test_upload_anonymous_success(self):
        mock_result = OperationResult(
            request_id="test-request-id",
            success=True,
            data="upload_anon_success",
            error_message="",
        )
        self.oss._call_mcp_tool = MagicMock(return_value=mock_result)

        result = self.oss.upload_anonymous("test_url", "test_path")

        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(result.content, "upload_anon_success")
        self.assertEqual(result.error_message, "")

    def test_upload_anonymous_failure(self):
        mock_result = OperationResult(
            request_id="test-request-id",
            success=False,
            data=None,
            error_message="Failed to upload anonymously",
        )
        self.oss._call_mcp_tool = MagicMock(return_value=mock_result)

        result = self.oss.upload_anonymous("test_url", "test_path")

        self.assertFalse(result.success)
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(result.content, "")
        self.assertEqual(result.error_message, "Failed to upload anonymously")

    def test_download_success(self):
        mock_result = OperationResult(
            request_id="test-request-id",
            success=True,
            data="download_success",
            error_message="",
        )
        self.oss._call_mcp_tool = MagicMock(return_value=mock_result)

        result = self.oss.download("test_bucket", "test_object", "test_path")

        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(result.content, "download_success")
        self.assertEqual(result.error_message, "")

    def test_download_failure(self):
        mock_result = OperationResult(
            request_id="test-request-id",
            success=False,
            data=None,
            error_message="Failed to download from OSS",
        )
        self.oss._call_mcp_tool = MagicMock(return_value=mock_result)

        result = self.oss.download("test_bucket", "test_object", "test_path")

        self.assertFalse(result.success)
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(result.content, "")
        self.assertEqual(result.error_message, "Failed to download from OSS")

    def test_download_anonymous_success(self):
        mock_result = OperationResult(
            request_id="test-request-id",
            success=True,
            data="download_anon_success",
            error_message="",
        )
        self.oss._call_mcp_tool = MagicMock(return_value=mock_result)

        result = self.oss.download_anonymous("test_url", "test_path")

        self.assertTrue(result.success)
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(result.content, "download_anon_success")
        self.assertEqual(result.error_message, "")

    def test_download_anonymous_failure(self):
        mock_result = OperationResult(
            request_id="test-request-id",
            success=False,
            data=None,
            error_message="Failed to download anonymously",
        )
        self.oss._call_mcp_tool = MagicMock(return_value=mock_result)

        result = self.oss.download_anonymous("test_url", "test_path")

        self.assertFalse(result.success)
        self.assertEqual(result.request_id, "test-request-id")
        self.assertEqual(result.content, "")
        self.assertEqual(result.error_message, "Failed to download anonymously")


if __name__ == "__main__":
    unittest.main()
