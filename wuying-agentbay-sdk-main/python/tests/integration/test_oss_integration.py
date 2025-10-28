import os
import unittest

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams


def get_oss_credentials():
    """Helper function to get OSS credentials from environment variables or use defaults."""
    credentials = {
        "access_key_id": os.getenv("OSS_ACCESS_KEY_ID", "test-access-key-id"),
        "access_key_secret": os.getenv(
            "OSS_ACCESS_KEY_SECRET", "test-access-key-secret"
        ),
        "security_token": os.getenv("OSS_SECURITY_TOKEN", "test-security-token"),
        "endpoint": os.getenv("OSS_ENDPOINT", "https://oss-cn-hangzhou.aliyuncs.com"),
        "region": os.getenv("OSS_REGION", "cn-hangzhou"),
    }
    return credentials


class TestOssIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment before all tests."""
        # Get API key from environment
        cls.api_key = os.getenv("AGENTBAY_API_KEY")
        if not cls.api_key:
            raise unittest.SkipTest("AGENTBAY_API_KEY environment variable not set")

        # Initialize AgentBay client
        cls.agent_bay = AgentBay(cls.api_key)

        # Create a session
        print("Creating a new session for OSS testing...")
        params = CreateSessionParams(
            image_id="code_latest",
        )
        result = cls.agent_bay.create(params)
        cls.session = result.session
        print(cls.session.get_session_id())
        print(f"Session created with ID: {cls.session.get_session_id()}")

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment after all tests."""
        print("Cleaning up: Deleting the session...")
        if hasattr(cls, "session"):
            cls.agent_bay.delete(cls.session)
            print("Session successfully deleted")

    def test_env_init(self):
        """Test OSS environment initialization."""
        if not self.session.oss:
            self.skipTest("OSS interface is not available")

        print("Initializing OSS environment...")
        credentials = get_oss_credentials()
        result = self.session.oss.env_init(
            credentials["access_key_id"],
            credentials["access_key_secret"],
            credentials["security_token"],
            credentials["endpoint"],
            credentials["region"],
        )
        print(f"EnvInit result: {result}")
        self.assertTrue(result.success)
        self.assertIsNotNone(result.request_id)
        self.assertIsNotNone(result.client_config)

    def test_upload(self):
        """Test OSS file upload."""
        if not self.session.oss or not self.session.file_system:
            self.skipTest("OSS or FileSystem interface is not available")

        # Initialize OSS environment first
        credentials = get_oss_credentials()
        init_result = self.session.oss.env_init(
            credentials["access_key_id"],
            credentials["access_key_secret"],
            credentials["security_token"],
            credentials["endpoint"],
            credentials["region"],
        )
        self.assertTrue(init_result.success)

        # Create a test file to upload
        test_content = "This is a test file for OSS upload."
        test_file_path = "/tmp/test_oss_upload.txt"
        self.session.file_system.write_file(test_file_path, test_content, "overwrite")

        # Upload the file
        print("Uploading file to OSS...")
        bucket = os.getenv("OSS_TEST_BUCKET", "test-bucket")
        object_key = "test-object.txt"
        result = self.session.oss.upload(bucket, object_key, test_file_path)
        print(f"Upload result: {result}")
        self.assertTrue(result.success)
        self.assertIsNotNone(result.request_id)
        self.assertIn("Upload success", result.content)

    def test_upload_anonymous(self):
        """Test OSS anonymous file upload."""
        if not self.session.oss or not self.session.file_system:
            self.skipTest("OSS or FileSystem interface is not available")

        # Create a test file to upload
        test_content = "This is a test file for OSS anonymous upload."
        test_file_path = "/tmp/test_oss_upload_anon.txt"
        self.session.file_system.write_file(test_file_path, test_content, "overwrite")

        # Upload the file anonymously
        print("Uploading file anonymously...")
        upload_url = os.getenv(
            "OSS_TEST_UPLOAD_URL", "https://example.com/upload/test-file.txt"
        )
        result = self.session.oss.upload_anonymous(upload_url, test_file_path)
        print(f"UploadAnonymous result: {result}")
        self.assertTrue(result.success)
        self.assertIsNotNone(result.request_id)
        self.assertIn("Upload success", result.content)

    def test_download(self):
        """Test OSS file download."""
        if not self.session.oss or not self.session.file_system:
            self.skipTest("OSS or FileSystem interface is not available")

        # Initialize OSS environment first
        credentials = get_oss_credentials()
        init_result = self.session.oss.env_init(
            credentials["access_key_id"],
            credentials["access_key_secret"],
            credentials["security_token"],
            credentials["endpoint"],
            credentials["region"],
        )
        self.assertTrue(init_result.success)

        # Download the file
        print("Downloading file from OSS...")
        bucket = os.getenv("OSS_TEST_BUCKET", "test-bucket")
        object_key = "test-object.txt"
        download_path = "/tmp/test_oss_download.txt"
        result = self.session.oss.download(bucket, object_key, download_path)
        print(f"Download result: {result}")
        self.assertTrue(result.success)
        self.assertIsNotNone(result.request_id)
        self.assertIn("Download success", result.content)

        # Verify the downloaded file exists
        file_info = self.session.file_system.get_file_info(download_path)
        self.assertIsNotNone(file_info)

    def test_download_anonymous(self):
        """Test OSS anonymous file download."""
        if not self.session.oss or not self.session.file_system:
            self.skipTest("OSS or FileSystem interface is not available")

        # Download the file anonymously
        print("Downloading file anonymously...")
        download_url = os.getenv(
            "OSS_TEST_DOWNLOAD_URL",
            "https://example.com/download/test-file.txt",
        )
        download_path = "/tmp/test_oss_download_anon.txt"
        result = self.session.oss.download_anonymous(download_url, download_path)
        print(f"DownloadAnonymous result: {result}")
        self.assertTrue(result.success)
        self.assertIsNotNone(result.request_id)
        self.assertIn("Download success", result.content)

        # Verify the downloaded file exists
        file_info = self.session.file_system.get_file_info(download_path)
        self.assertIsNotNone(file_info)


if __name__ == "__main__":
    unittest.main()
