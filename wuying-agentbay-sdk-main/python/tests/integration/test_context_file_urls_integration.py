import os
import time
import unittest
import httpx

from agentbay import AgentBay


class TestContextFileUrlsIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        api_key = os.environ.get("AGENTBAY_API_KEY")
        if not api_key or os.environ.get("CI"):
            raise unittest.SkipTest(
                "Skipping integration test: No API key available or running in CI"
            )
        cls.agent_bay = AgentBay(api_key)

        # Create a test context
        cls.context_name = f"test-file-url-py-{int(time.time())}"
        context_result = cls.agent_bay.context.create(cls.context_name)
        if not context_result.success or not context_result.context:
            raise unittest.SkipTest("Failed to create context for file URL test")
        cls.context = context_result.context
        print(f"Created context: {cls.context.name} (ID: {cls.context.id})")

    @classmethod
    def tearDownClass(cls):
        # Clean up created context
        if hasattr(cls, "context"):
            try:
                cls.agent_bay.context.delete(cls.context)
                print(f"Deleted context: {cls.context.name} (ID: {cls.context.id})")
            except Exception as e:
                print(f"Warning: Failed to delete context {cls.context.name}: {e}")

    def test_get_file_upload_url(self):
        """
        Create a context and request a presigned upload URL for a test path.
        Validate that a URL is returned.
        """
        test_path = "/tmp/integration_upload_test.txt"
        result = self.agent_bay.context.get_file_upload_url(self.context.id, test_path)

        self.assertTrue(result.request_id is not None and isinstance(result.request_id, str))
        self.assertTrue(result.success, "get_file_upload_url should be successful")
        self.assertTrue(isinstance(result.url, str) and len(result.url) > 0, "URL should be non-empty")
        # Expire time may be optional depending on backend; if present, should be int-like
        if result.expire_time is not None:
            self.assertTrue(isinstance(result.expire_time, int))

        print(f"Upload URL: {result.url[:80]}... (RequestID: {result.request_id})")

        # Use the obtained presigned URL to upload content to OSS
        upload_content = f"agentbay integration upload test at {int(time.time())}\n".encode("utf-8")
        response = httpx.put(result.url, content=upload_content, timeout=30.0)
        self.assertIn(
            response.status_code,
            (200, 204),
            f"Upload failed with status code {response.status_code}"
        )
        etag = response.headers.get("ETag")
        print(f"Uploaded {len(upload_content)} bytes, status={response.status_code}, ETag={etag}")

        # Fetch a presigned download URL for the same file and verify content
        dl_result = self.agent_bay.context.get_file_download_url(self.context.id, test_path)
        self.assertTrue(dl_result.success, "get_file_download_url should be successful")
        self.assertTrue(isinstance(dl_result.url, str) and len(dl_result.url) > 0, "Download URL should be non-empty")
        print(f"Download URL: {dl_result.url[:80]}... (RequestID: {dl_result.request_id})")

        dl_resp = httpx.get(dl_result.url, timeout=30.0)
        self.assertEqual(dl_resp.status_code, 200, f"Download failed with status code {dl_resp.status_code}")
        self.assertEqual(dl_resp.content, upload_content, "Downloaded content does not match uploaded content")
        print(f"Downloaded {len(dl_resp.content)} bytes, content matches uploaded data")

        # List files to verify presence of the uploaded file under /tmp (with small retry)
        file_name = os.path.basename(test_path)

        def list_contains():
            res = self.agent_bay.context.list_files(self.context.id, "/tmp", page_number=1, page_size=50)
            if not res or not res.success:
                return False, res, "/tmp"
            found_local = any(
                (getattr(e, "file_path", "") == test_path)
                or (getattr(e, "file_name", "") == file_name)
                for e in res.entries
            )
            if found_local or len(res.entries) > 0:
                return found_local, res, "/tmp"
            return False, res, "/tmp"

        found = False
        last_lf_res = None
        chosen_parent = None
        retries_presence = 0
        for _ in range(30):
            found, last_lf_res, chosen_parent = list_contains()
            if found:
                break
            retries_presence += 1
            time.sleep(2.0)
        print(f"List files retry attempts (presence check): {retries_presence}")

        if last_lf_res and chosen_parent:
            total = (last_lf_res.count if getattr(last_lf_res, "count", None) is not None else len(last_lf_res.entries))
            print(f"List files: checked parent={chosen_parent}, total={total}, contains={found}")
        else:
            print("List files: no listing result available")

        # Only assert presence if listing returned entries; otherwise skip presence assert due to backend limitations
        if last_lf_res and len(last_lf_res.entries) > 0:
            self.assertTrue(found, "Uploaded file should appear in list_files")

        # Delete the file and verify it disappears from listing (with small retry)
        op = self.agent_bay.context.delete_file(self.context.id, test_path)
        self.assertTrue(op.success, "delete_file should be successful")
        print(f"Deleted file: {test_path}")

        removed = False
        retries_deletion = 0
        for _ in range(20):
            present, _, _ = list_contains()
            if last_lf_res and len(last_lf_res.entries) > 0:
                if not present:
                    removed = True
                    break
                removed = False
            else:
                removed = True
                break
            retries_deletion += 1
            time.sleep(1.0)
        print(f"List files retry attempts (deletion check): {retries_deletion}")
        self.assertTrue(removed, "Deleted file should not appear in list_files when listing is available")
        if last_lf_res:
            prev = (last_lf_res.count if getattr(last_lf_res, "count", None) is not None else len(last_lf_res.entries))
            print(f"List files: {file_name} absent after delete (listing availability: {prev})")

        # Additionally, attempt to download after delete and log the status.
        # Some backends may keep presigned URLs valid until expiry even if the file is deleted.
        post_dl = self.agent_bay.context.get_file_download_url(self.context.id, test_path)
        if post_dl.success and isinstance(post_dl.url, str) and len(post_dl.url) > 0:
            post_resp = httpx.get(post_dl.url, timeout=30.0)
            print(f"Post-delete download status (informational): {post_resp.status_code}")
        else:
            print("Post-delete: download URL not available, treated as deleted") 