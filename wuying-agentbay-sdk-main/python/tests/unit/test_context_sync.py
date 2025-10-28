#!/usr/bin/env python3
"""
Unit tests for context_sync module.
"""

import unittest
from agentbay.context_sync import (
    SyncPolicy,
    UploadPolicy,
    DownloadPolicy,
    DeletePolicy,
    BWList,
    WhiteList,
    UploadStrategy,
    DownloadStrategy,
)


class TestSyncPolicy(unittest.TestCase):
    """Test SyncPolicy class functionality."""

    def test_sync_policy_with_partial_parameters(self):
        """Test that SyncPolicy automatically fills missing parameters with defaults."""
        # Create SyncPolicy with only upload_policy
        upload_policy = UploadPolicy(auto_upload=False)
        sync_policy = SyncPolicy(upload_policy=upload_policy)
        
        # Verify upload_policy is set correctly
        self.assertEqual(sync_policy.upload_policy.auto_upload, False)
        
        # Verify other policies are filled with defaults
        self.assertIsNotNone(sync_policy.download_policy)
        self.assertIsNotNone(sync_policy.delete_policy)
        self.assertIsNotNone(sync_policy.bw_list)
        
        # Verify default values
        self.assertTrue(sync_policy.download_policy.auto_download)
        self.assertEqual(sync_policy.download_policy.download_strategy, DownloadStrategy.DOWNLOAD_ASYNC)
        self.assertTrue(sync_policy.delete_policy.sync_local_file)
        self.assertEqual(len(sync_policy.bw_list.white_lists), 1)

    def test_sync_policy_with_no_parameters(self):
        """Test that SyncPolicy with no parameters uses all defaults."""
        sync_policy = SyncPolicy()
        
        # Verify all policies are set with defaults
        self.assertIsNotNone(sync_policy.upload_policy)
        self.assertIsNotNone(sync_policy.download_policy)
        self.assertIsNotNone(sync_policy.delete_policy)
        self.assertIsNotNone(sync_policy.bw_list)
        
        # Verify default values
        self.assertTrue(sync_policy.upload_policy.auto_upload)
        self.assertEqual(sync_policy.upload_policy.upload_strategy, UploadStrategy.UPLOAD_BEFORE_RESOURCE_RELEASE)
        
        self.assertTrue(sync_policy.download_policy.auto_download)
        self.assertEqual(sync_policy.download_policy.download_strategy, DownloadStrategy.DOWNLOAD_ASYNC)
        
        self.assertTrue(sync_policy.delete_policy.sync_local_file)
        
        self.assertEqual(len(sync_policy.bw_list.white_lists), 1)
        self.assertEqual(sync_policy.bw_list.white_lists[0].path, "")
        self.assertEqual(sync_policy.bw_list.white_lists[0].exclude_paths, [])

    def test_sync_policy_with_all_parameters(self):
        """Test that SyncPolicy with all parameters works correctly."""
        upload_policy = UploadPolicy(auto_upload=False)
        download_policy = DownloadPolicy(auto_download=False)
        delete_policy = DeletePolicy(sync_local_file=False)
        bw_list = BWList(white_lists=[WhiteList(path="/test", exclude_paths=["/exclude"])])
        
        sync_policy = SyncPolicy(
            upload_policy=upload_policy,
            download_policy=download_policy,
            delete_policy=delete_policy,
            bw_list=bw_list
        )
        
        # Verify all policies are set correctly
        self.assertEqual(sync_policy.upload_policy.auto_upload, False)
        
        self.assertEqual(sync_policy.download_policy.auto_download, False)
        self.assertEqual(sync_policy.delete_policy.sync_local_file, False)
        
        self.assertEqual(len(sync_policy.bw_list.white_lists), 1)
        self.assertEqual(sync_policy.bw_list.white_lists[0].path, "/test")
        self.assertEqual(sync_policy.bw_list.white_lists[0].exclude_paths, ["/exclude"])

    def test_sync_policy_serialization(self):
        """Test that SyncPolicy serializes correctly with all policies present."""
        sync_policy = SyncPolicy(upload_policy=UploadPolicy(auto_upload=False))
        
        # Serialize to dict
        result = sync_policy.__dict__()
        
        # Verify all policies are present in serialization
        self.assertIn("uploadPolicy", result)
        self.assertIn("downloadPolicy", result)
        self.assertIn("deletePolicy", result)
        self.assertIn("bwList", result)
        
        # Verify upload policy values
        self.assertEqual(result["uploadPolicy"]["autoUpload"], False)
        self.assertEqual(result["uploadPolicy"]["uploadStrategy"], UploadStrategy.UPLOAD_BEFORE_RESOURCE_RELEASE.value)
        
        # Verify download policy values
        self.assertEqual(result["downloadPolicy"]["autoDownload"], True)
        self.assertEqual(result["downloadPolicy"]["downloadStrategy"], DownloadStrategy.DOWNLOAD_ASYNC.value)
        
        # Verify delete policy values
        self.assertEqual(result["deletePolicy"]["syncLocalFile"], True)
        
        # Verify bw list values
        self.assertEqual(len(result["bwList"]["whiteLists"]), 1)
        self.assertEqual(result["bwList"]["whiteLists"][0]["path"], "")
        self.assertEqual(result["bwList"]["whiteLists"][0]["excludePaths"], [])


if __name__ == "__main__":
    unittest.main()
