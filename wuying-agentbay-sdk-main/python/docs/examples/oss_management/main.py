import os

from agentbay import AgentBay
from agentbay.exceptions import OssError
from agentbay.oss.oss import Oss
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


def test_oss_integration():
    """
    Integration test for Oss class methods.
    """
    # Get API Key
    api_key = os.getenv("AGENTBAY_API_KEY")
    if not api_key:
        api_key = "akm-xxx"

    session = None
    try:
        agent_bay = AgentBay(api_key=api_key)
        # Create session
        print("\nCreating a new session...")
        params = CreateSessionParams(
            image_id="code_latest",
        )
        session_result = agent_bay.create(params)
        if not session_result.success or not session_result.session:
            print("Failed to create session")
            return
            
        session = session_result.session
        print(f"Session created with ID: {session.session_id}")

        oss = Oss(session)

        # env_init
        print("\nTesting env_init...")
        credentials = get_oss_credentials()
        result = oss.env_init(
            credentials["access_key_id"],
            credentials["access_key_secret"],
            credentials["security_token"],
            credentials["endpoint"],
            credentials["region"],
        )

        print(f"env_init result: {result}")
        print(f"Request ID: {result.request_id}")
        print(f"Success: {result.success}")
        if result.success:
            print(f"Client config: {result.client_config}")
        else:
            print(f"Error: {result.error_message}")

        # Create a test file to upload
        test_content = "This is a test file for OSS upload."
        test_file_path = "/tmp/test_oss_upload.txt"
        session.file_system.write_file(test_file_path, test_content, "overwrite")

        # upload
        print("\nTesting upload...")
        bucket = os.getenv("OSS_TEST_BUCKET", "test-bucket")
        upload_result = oss.upload(
            bucket=bucket, object="test-object.txt", path=test_file_path
        )
        print(f"Upload result: {upload_result}")
        print(f"Request ID: {upload_result.request_id}")
        print(f"Success: {upload_result.success}")
        if upload_result.success:
            print(f"Content: {upload_result.content}")
        else:
            print(f"Error: {upload_result.error_message}")

        # upload_anonymous
        print("\nTesting upload_anonymous...")
        upload_url = os.getenv(
            "OSS_TEST_UPLOAD_URL", "https://example.com/upload/test-file.txt"
        )
        upload_anon_result = oss.upload_anonymous(upload_url, test_file_path)
        print(f"Upload anonymous result: {upload_anon_result}")
        print(f"Request ID: {upload_anon_result.request_id}")
        print(f"Success: {upload_anon_result.success}")
        if upload_anon_result.success:
            print(f"Content: {upload_anon_result.content}")
        else:
            print(f"Error: {upload_anon_result.error_message}")

        # download test
        print("\nTesting download...")
        download_result = oss.download(
            bucket=os.getenv("OSS_TEST_BUCKET", "test-bucket"),
            object="test-object.txt",
            path="/tmp/test_oss_download.txt",
        )
        print(f"Download result: {download_result}")
        print(f"Request ID: {download_result.request_id}")
        print(f"Success: {download_result.success}")
        if download_result.success:
            print(f"Content: {download_result.content}")
        else:
            print(f"Error: {download_result.error_message}")

        # download_anonymous
        print("\nTesting download_anonymous...")
        download_anon_result = oss.download_anonymous(
            url=os.getenv("OSS_TEST_DOWNLOAD_URL", "https://oss-test-download-url.com"),
            path="/tmp/test_oss_download_anon.txt",
        )
        print(f"Download anonymous result: {download_anon_result}")
        print(f"Request ID: {download_anon_result.request_id}")
        print(f"Success: {download_anon_result.success}")
        if download_anon_result.success:
            print(f"Content: {download_anon_result.content}")
        else:
            print(f"Error: {download_anon_result.error_message}")

        # delete the session
        print("\nDeleting the session...")
        session.delete()
        session = None  # Clear session reference
        print("Session deleted successfully.")

    except OssError as e:
        print(f"Failed to test Oss integration: {e}")
        if session:
            try:
                session.delete()
                print("Session deleted successfully after error")
            except Exception as delete_error:
                print(f"Error deleting session after error: {delete_error}")


if __name__ == "__main__":
    test_oss_integration()
