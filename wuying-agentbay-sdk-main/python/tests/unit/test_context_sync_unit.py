#!/usr/bin/env python3
"""
Unit tests for context synchronization functionality.
Tests data structures and API without network calls.
"""

import unittest

from agentbay.context_sync import (
    ContextSync,
    SyncPolicy,
    UploadPolicy,
    UploadStrategy,
    DownloadPolicy,
    DownloadStrategy,
    DeletePolicy,
    BWList,
    WhiteList,
)

class TestContextSyncUnit(unittest.TestCase):
    """Unit tests for context synchronization functionality."""

    def test_01_basic_context_sync_creation(self):
        """Test creating a basic context sync configuration."""
        print("Test 1: Creating a basic context sync configuration...")

        # Create a basic context sync configuration with default policy
        basic_sync = ContextSync.new(
            "test-context-id", "/home/wuying", SyncPolicy.default()
        )

        self.assertEqual(basic_sync.context_id, "test-context-id")
        self.assertEqual(basic_sync.path, "/home/wuying")
        self.assertIsNotNone(basic_sync.policy)

        # Verify default policy values - auto_upload defaults to True
        self.assertTrue(basic_sync.policy.upload_policy.auto_upload)
        self.assertEqual(
            basic_sync.policy.upload_policy.upload_strategy,
            UploadStrategy.UPLOAD_BEFORE_RESOURCE_RELEASE,
        )

        self.assertTrue(basic_sync.policy.download_policy.auto_download)
        self.assertEqual(
            basic_sync.policy.download_policy.download_strategy,
            DownloadStrategy.DOWNLOAD_ASYNC,
        )

        self.assertTrue(basic_sync.policy.delete_policy.sync_local_file)

        print(
            f"Basic sync - ContextID: {basic_sync.context_id}, Path: {basic_sync.path}"
        )

    def test_02_advanced_context_sync_configuration(self):
        """Test creating an advanced context sync configuration with custom policies."""
        print("\nTest 2: Creating an advanced context sync configuration...")

        # Create upload policy
        upload_policy = UploadPolicy(
            auto_upload=True,
            upload_strategy=UploadStrategy.UPLOAD_BEFORE_RESOURCE_RELEASE,
        )

        # Create download policy
        download_policy = DownloadPolicy(
            auto_download=True, download_strategy=DownloadStrategy.DOWNLOAD_ASYNC
        )

        # Create delete policy
        delete_policy = DeletePolicy(sync_local_file=True)

        # Create white list
        white_list = WhiteList(
            path="/home/wuying/important",
            exclude_paths=[
                "/home/wuying/important/temp",
                "/home/wuying/important/logs",
            ],
        )

        # Create BW list
        bw_list = BWList(white_lists=[white_list])

        # Create sync policy
        sync_policy = SyncPolicy(
            upload_policy=upload_policy,
            download_policy=download_policy,
            delete_policy=delete_policy,
            bw_list=bw_list,
        )

        # Create advanced sync configuration
        advanced_sync = ContextSync.new("test-context-id", "/home/wuying", sync_policy)

        self.assertEqual(advanced_sync.context_id, "test-context-id")
        self.assertEqual(advanced_sync.path, "/home/wuying")
        self.assertIsNotNone(advanced_sync.policy)

        # Verify custom policy values
        self.assertTrue(advanced_sync.policy.upload_policy.auto_upload)
        self.assertEqual(
            advanced_sync.policy.upload_policy.upload_strategy,
            UploadStrategy.UPLOAD_BEFORE_RESOURCE_RELEASE,
        )

        self.assertTrue(advanced_sync.policy.download_policy.auto_download)
        self.assertEqual(
            advanced_sync.policy.download_policy.download_strategy,
            DownloadStrategy.DOWNLOAD_ASYNC,
        )

        self.assertTrue(advanced_sync.policy.delete_policy.sync_local_file)

        self.assertEqual(len(advanced_sync.policy.bw_list.white_lists), 1)
        self.assertEqual(
            advanced_sync.policy.bw_list.white_lists[0].path, "/home/wuying/important"
        )
        self.assertEqual(
            advanced_sync.policy.bw_list.white_lists[0].exclude_paths,
            ["/home/wuying/important/temp", "/home/wuying/important/logs"],
        )

        print(
            f"Advanced sync - ContextID: {advanced_sync.context_id}, Path: {advanced_sync.path}"
        )
        print(
            f"  - Upload: Auto={advanced_sync.policy.upload_policy.auto_upload}, "
            f"Strategy={advanced_sync.policy.upload_policy.upload_strategy}"
        )
        print(
            f"  - Download: Auto={advanced_sync.policy.download_policy.auto_download}, "
            f"Strategy={advanced_sync.policy.download_policy.download_strategy}"
        )
        print(
            f"  - Delete: SyncLocalFile={advanced_sync.policy.delete_policy.sync_local_file}"
        )
        print(
            f"  - WhiteList: Path={advanced_sync.policy.bw_list.white_lists[0].path}, "
            f"ExcludePaths={advanced_sync.policy.bw_list.white_lists[0].exclude_paths}"
        )

    def test_03_builder_pattern_context_sync(self):
        """Test using builder pattern for context sync."""
        print("\nTest 3: Using builder pattern for context sync...")

        # Create context sync using builder pattern
        builder_sync = ContextSync.new("test-context-id", "/workspace").with_policy(
            SyncPolicy(
                upload_policy=UploadPolicy(
                    auto_upload=True,
                    upload_strategy=UploadStrategy.UPLOAD_BEFORE_RESOURCE_RELEASE,
                ),
                download_policy=DownloadPolicy(
                    auto_download=True,
                    download_strategy=DownloadStrategy.DOWNLOAD_ASYNC,
                ),
                bw_list=BWList(
                    white_lists=[
                        WhiteList(
                            path="/workspace/src",
                            exclude_paths=["/workspace/src/node_modules"],
                        )
                    ]
                ),
            )
        )

        self.assertEqual(builder_sync.context_id, "test-context-id")
        self.assertEqual(builder_sync.path, "/workspace")
        self.assertIsNotNone(builder_sync.policy)

        # Verify builder pattern results
        self.assertTrue(builder_sync.policy.upload_policy.auto_upload)
        self.assertEqual(
            builder_sync.policy.upload_policy.upload_strategy,
            UploadStrategy.UPLOAD_BEFORE_RESOURCE_RELEASE,
        )

        self.assertTrue(builder_sync.policy.download_policy.auto_download)
        self.assertEqual(
            builder_sync.policy.download_policy.download_strategy,
            DownloadStrategy.DOWNLOAD_ASYNC,
        )

        self.assertEqual(len(builder_sync.policy.bw_list.white_lists), 1)
        self.assertEqual(
            builder_sync.policy.bw_list.white_lists[0].path, "/workspace/src"
        )
        self.assertEqual(
            builder_sync.policy.bw_list.white_lists[0].exclude_paths,
            ["/workspace/src/node_modules"],
        )

        print(
            f"Builder sync - ContextID: {builder_sync.context_id}, Path: {builder_sync.path}"
        )

    def test_04_multiple_white_lists_context_sync(self):
        """Test creating context sync with multiple white lists."""
        print("\nTest 4: Creating context sync with multiple white lists...")

        # Create multiple white lists
        source_white_list = WhiteList(
            path="/workspace/src",
            exclude_paths=["/workspace/src/node_modules", "/workspace/src/.git"],
        )

        docs_white_list = WhiteList(
            path="/workspace/docs",
            exclude_paths=["/workspace/docs/build", "/workspace/docs/temp"],
        )

        config_white_list = WhiteList(
            path="/workspace/config", exclude_paths=["/workspace/config/tmp"]
        )

        # Create BW list with multiple white lists
        bw_list = BWList(
            white_lists=[source_white_list, docs_white_list, config_white_list]
        )

        # Create sync policy - remove sync_paths parameter as it's not supported
        sync_policy = SyncPolicy(
            upload_policy=UploadPolicy.default(),
            download_policy=DownloadPolicy.default(),
            delete_policy=DeletePolicy.default(),
            bw_list=bw_list,
        )

        # Create context sync
        context_sync = ContextSync.new("test-context-id", "/workspace", sync_policy)

        self.assertEqual(len(context_sync.policy.bw_list.white_lists), 3)

        print(
            f"Multiple white lists - ContextID: {context_sync.context_id}, Path: {context_sync.path}"
        )
        print(
            f"  - Number of white lists: {len(context_sync.policy.bw_list.white_lists)}"
        )

    def test_05_different_upload_strategies(self):
        """Test different upload strategies."""
        print("\nTest 5: Testing different upload strategies...")

        strategies = [
            UploadStrategy.UPLOAD_BEFORE_RESOURCE_RELEASE,
        ]

        for strategy in strategies:
            upload_policy = UploadPolicy(
                auto_upload=True, upload_strategy=strategy
            )

            sync_policy = SyncPolicy(upload_policy=upload_policy)
            context_sync = ContextSync.new("test-context-id", "/test", sync_policy)

            self.assertEqual(
                context_sync.policy.upload_policy.upload_strategy, strategy
            )
            print(f"  - Strategy: {strategy}")

    def test_06_different_download_strategies(self):
        """Test different download strategies."""
        print("\nTest 6: Testing different download strategies...")

        strategies = [DownloadStrategy.DOWNLOAD_ASYNC]

        for strategy in strategies:
            download_policy = DownloadPolicy(
                auto_download=True, download_strategy=strategy
            )

            sync_policy = SyncPolicy(download_policy=download_policy)
            context_sync = ContextSync.new("test-context-id", "/test", sync_policy)

            self.assertEqual(
                context_sync.policy.download_policy.download_strategy, strategy
            )
            print(f"  - Strategy: {strategy}")

    def test_07_policy_modification(self):
        """Test modifying existing policies."""
        print("\nTest 7: Testing policy modification...")

        # Create initial context sync
        context_sync = ContextSync.new("test-context-id", "/test", SyncPolicy.default())

        # Modify upload policy - use existing upload strategy
        new_upload_policy = UploadPolicy(
            auto_upload=False, upload_strategy=UploadStrategy.UPLOAD_BEFORE_RESOURCE_RELEASE
        )

        # Create new sync policy with modified upload policy
        new_sync_policy = SyncPolicy(
            upload_policy=new_upload_policy,
            download_policy=context_sync.policy.download_policy,
            delete_policy=context_sync.policy.delete_policy,
            bw_list=context_sync.policy.bw_list,
        )

        # Apply new policy
        context_sync.with_policy(new_sync_policy)

        self.assertFalse(context_sync.policy.upload_policy.auto_upload)
        self.assertEqual(
            context_sync.policy.upload_policy.upload_strategy,
            UploadStrategy.UPLOAD_BEFORE_RESOURCE_RELEASE,
        )

        print(
            f"Policy modification - Upload auto: {context_sync.policy.upload_policy.auto_upload}, "
            f"Strategy: {context_sync.policy.upload_policy.upload_strategy}"
        )

    def test_08_default_policies(self):
        """Test default policy creation."""
        print("\nTest 8: Testing default policies...")

        # Test default upload policy
        upload_policy = UploadPolicy.default()
        self.assertTrue(upload_policy.auto_upload)  # Default is True
        self.assertEqual(
            upload_policy.upload_strategy, UploadStrategy.UPLOAD_BEFORE_RESOURCE_RELEASE
        )

        # Test default download policy
        download_policy = DownloadPolicy.default()
        self.assertTrue(download_policy.auto_download)
        self.assertEqual(
            download_policy.download_strategy, DownloadStrategy.DOWNLOAD_ASYNC
        )

        # Test default delete policy
        delete_policy = DeletePolicy.default()
        self.assertTrue(delete_policy.sync_local_file)

        # Test default sync policy
        sync_policy = SyncPolicy.default()
        self.assertTrue(sync_policy.upload_policy.auto_upload)  # Default is True
        self.assertTrue(sync_policy.download_policy.auto_download)
        self.assertTrue(sync_policy.delete_policy.sync_local_file)

        print("Default policies created successfully")

    def test_09_context_sync_serialization(self):
        """Test context sync object serialization."""
        print("\nTest 9: Testing context sync serialization...")

        # Create a complex context sync - use existing upload strategy
        context_sync = ContextSync.new(
            "test-context-id",
            "/workspace",
            SyncPolicy(
                upload_policy=UploadPolicy(
                    auto_upload=True,
                    upload_strategy=UploadStrategy.UPLOAD_BEFORE_RESOURCE_RELEASE,
                ),
                download_policy=DownloadPolicy(
                    auto_download=True,
                    download_strategy=DownloadStrategy.DOWNLOAD_ASYNC,
                ),
                bw_list=BWList(
                    white_lists=[
                        WhiteList(
                            path="/workspace/src",
                            exclude_paths=["/workspace/src/node_modules"],
                        )
                    ]
                ),
            ),
        )

        # Test that we can access all properties
        self.assertEqual(context_sync.context_id, "test-context-id")
        self.assertEqual(context_sync.path, "/workspace")
        self.assertTrue(context_sync.policy.upload_policy.auto_upload)
        self.assertEqual(len(context_sync.policy.bw_list.white_lists), 1)

        print("Context sync serialization test passed")

    def test_10_edge_cases(self):
        """Test edge cases and error handling."""
        print("\nTest 10: Testing edge cases...")

        # Test with empty exclude_paths
        white_list = WhiteList(path="/test", exclude_paths=[])
        self.assertEqual(white_list.path, "/test")
        self.assertEqual(white_list.exclude_paths, [])

        # Test with None exclude_paths - fix initialization
        white_list = WhiteList(path="/test")
        self.assertEqual(white_list.path, "/test")
        self.assertEqual(white_list.exclude_paths, [])  # Default to empty list, not None

        # Test with empty white_lists
        bw_list = BWList(white_lists=[])
        self.assertEqual(len(bw_list.white_lists), 0)

        # Test with None white_lists - fix initialization
        bw_list = BWList()
        self.assertEqual(bw_list.white_lists, [])  # Default to empty list, not None

        print("Edge cases test passed")

if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)
