import unittest
from unittest.mock import MagicMock

from agentbay.context import ContextService, ContextFileListResult, ContextFileEntry


class TestContextFileUrls(unittest.TestCase):
    def setUp(self):
        self.agent_bay = MagicMock()
        self.agent_bay.api_key = "test-api-key"
        self.agent_bay.client = MagicMock()
        self.context = ContextService(self.agent_bay)
        self.context_id = "ctx-123"
        self.test_path = "/tmp/integration_upload_test.txt"

    def test_get_file_upload_url_success(self):
        mock_resp = MagicMock()
        mock_body = MagicMock()
        mock_data = MagicMock()
        mock_data.url = "https://oss.example.com/upload-url"
        mock_data.expire_time = 3600
        mock_body.success = True
        mock_body.data = mock_data
        mock_resp.to_map.return_value = {"body": {"RequestId": "req-upload-1"}}
        mock_resp.body = mock_body
        self.agent_bay.client.get_context_file_upload_url.return_value = mock_resp

        result = self.context.get_file_upload_url(self.context_id, self.test_path)

        self.assertTrue(result.success)
        self.assertEqual(result.url, "https://oss.example.com/upload-url")
        self.assertEqual(result.expire_time, 3600)

    def test_get_file_download_url_success(self):
        mock_resp = MagicMock()
        mock_body = MagicMock()
        mock_data = MagicMock()
        mock_data.url = "https://oss.example.com/download-url"
        mock_data.expire_time = 7200
        mock_body.success = True
        mock_body.data = mock_data
        mock_resp.to_map.return_value = {"body": {"RequestId": "req-download-1"}}
        mock_resp.body = mock_body
        self.agent_bay.client.get_context_file_download_url.return_value = mock_resp

        result = self.context.get_file_download_url(self.context_id, self.test_path)

        self.assertTrue(result.success)
        self.assertEqual(result.url, "https://oss.example.com/download-url")
        self.assertEqual(result.expire_time, 7200)

    def test_get_file_download_url_unavailable(self):
        mock_resp = MagicMock()
        mock_body = MagicMock()
        mock_body.success = False
        mock_body.data = None
        mock_resp.to_map.return_value = {"body": {"RequestId": "req-download-2"}}
        mock_resp.body = mock_body
        self.agent_bay.client.get_context_file_download_url.return_value = mock_resp

        result = self.context.get_file_download_url(self.context_id, self.test_path)

        self.assertFalse(result.success)
        self.assertEqual(result.url, "")
        self.assertIsNone(result.expire_time)

    def test_list_files_with_entry(self):
        mock_resp = MagicMock()
        mock_body = MagicMock()
        entry = MagicMock()
        entry.file_id = "fid-1"
        entry.file_name = "integration_upload_test.txt"
        entry.file_path = "/tmp/integration_upload_test.txt"
        entry.size = 21
        entry.status = "ready"
        mock_body.success = True
        mock_body.count = 1
        mock_body.data = [entry]
        mock_resp.to_map.return_value = {"body": {"RequestId": "req-list-1"}}
        mock_resp.body = mock_body
        self.agent_bay.client.describe_context_files.return_value = mock_resp

        result = self.context.list_files(self.context_id, "/tmp", page_number=1, page_size=50)

        self.assertTrue(result.success)
        self.assertEqual(len(result.entries), 1)
        self.assertEqual(result.entries[0].file_path, "/tmp/integration_upload_test.txt")
        self.assertEqual(result.count, 1)

    def test_list_files_empty(self):
        mock_resp = MagicMock()
        mock_body = MagicMock()
        mock_body.success = True
        mock_body.count = None
        mock_body.data = []
        mock_resp.to_map.return_value = {"body": {"RequestId": "req-list-2"}}
        mock_resp.body = mock_body
        self.agent_bay.client.describe_context_files.return_value = mock_resp

        result = self.context.list_files(self.context_id, "/tmp", page_number=1, page_size=50)

        self.assertTrue(result.success)
        self.assertEqual(len(result.entries), 0)
        self.assertIsNone(result.count)

    def test_delete_file_success(self):
        mock_resp = MagicMock()
        mock_body = MagicMock()
        mock_body.success = True
        mock_resp.to_map.return_value = {"body": {"RequestId": "req-del-1"}}
        mock_resp.body = mock_body
        self.agent_bay.client.delete_context_file.return_value = mock_resp

        result = self.context.delete_file(self.context_id, self.test_path)

        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main() 