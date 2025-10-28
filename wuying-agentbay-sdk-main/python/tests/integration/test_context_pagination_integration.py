#!/usr/bin/env python3
"""
Integration test for context pagination functionality.
Based on golang/tests/pkg/integration/context_pagination_integration_test.go
"""

import os
import time
import unittest
from typing import List

from agentbay import AgentBay
from agentbay.context import Context, ContextListParams


class TestContextPaginationIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Skip if no API key is available or in CI environment
        api_key = os.environ.get("AGENTBAY_API_KEY")
        if not api_key or os.environ.get("CI"):
            raise unittest.SkipTest(
                "Skipping integration test: No API key available or running in CI"
            )

        # Initialize AgentBay client
        cls.agent_bay = AgentBay(api_key)

        # Create multiple contexts for testing pagination
        cls.context_names = []
        cls.created_contexts: List[Context] = []

        # Create 15 test contexts
        for i in range(15):
            context_name = f"test-pagination-py-{int(time.time())}-{i}"
            context_result = cls.agent_bay.context.create(context_name)
            if context_result.success and context_result.context:
                cls.context_names.append(context_name)
                cls.created_contexts.append(context_result.context)
                print(f"Created context: {context_name} (ID: {context_result.context.id})")
            else:
                raise unittest.SkipTest(f"Failed to create context {context_name}")

        # Wait a moment for all contexts to be fully created
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        # Clean up created contexts
        for context in cls.created_contexts:
            try:
                cls.agent_bay.context.delete(context)
                print(f"Deleted context: {context.name} (ID: {context.id})")
            except Exception as e:
                print(f"Warning: Failed to delete context {context.name}: {e}")

    def test_context_pagination_default(self):
        """Test 1: List contexts with default pagination (should get first 10)"""
        print("Test 1: Listing contexts with default pagination (first page)")
        params = ContextListParams()
        params.max_results = 10

        list_result = self.agent_bay.context.list(params)

        self.assertTrue(list_result.success, "List contexts should be successful")
        self.assertEqual(len(list_result.contexts), 10, "Expected 10 contexts in first page")
        
        print(f"First page: Got {len(list_result.contexts)} contexts (RequestID: {list_result.request_id})")
        print(f"NextToken: {list_result.next_token}, MaxResults: {list_result.max_results}, TotalCount: {list_result.total_count}")

    def test_context_pagination_custom_page_size(self):
        """Test 2: List contexts with custom page size"""
        print("Test 2: Listing contexts with custom page size (5 per page)")
        params = ContextListParams()
        params.max_results = 5

        list_result = self.agent_bay.context.list(params)

        self.assertTrue(list_result.success, "List contexts should be successful")
        self.assertEqual(len(list_result.contexts), 5, "Expected 5 contexts with custom page size")
        
        print(f"Custom page size: Got {len(list_result.contexts)} contexts (RequestID: {list_result.request_id})")
        print(f"NextToken: {list_result.next_token}, MaxResults: {list_result.max_results}, TotalCount: {list_result.total_count}")

    def test_context_pagination_second_page(self):
        """Test 3: Get second page using NextToken"""
        print("Test 3: Getting second page using NextToken")
        
        # First, get the first page to obtain the NextToken
        params = ContextListParams()
        params.max_results = 5
        first_page_result = self.agent_bay.context.list(params)

        if first_page_result.next_token:
            # Get second page using NextToken
            params = ContextListParams()
            params.max_results = 5
            params.next_token = first_page_result.next_token

            second_page_result = self.agent_bay.context.list(params)
            
            self.assertTrue(second_page_result.success, "List contexts second page should be successful")
            
            print(f"Second page: Got {len(second_page_result.contexts)} contexts (RequestID: {second_page_result.request_id})")
            print(f"NextToken: {second_page_result.next_token}, MaxResults: {second_page_result.max_results}, TotalCount: {second_page_result.total_count}")
        else:
            print("No NextToken available for second page test")

    def test_context_pagination_large_page_size(self):
        """Test 4: List contexts with larger page size"""
        print("Test 4: Listing contexts with larger page size (20 per page)")
        params = ContextListParams()
        params.max_results = 20

        list_result = self.agent_bay.context.list(params)

        self.assertTrue(list_result.success, "List contexts should be successful")
        # Should get all contexts (up to 15) since we only created 15
        self.assertGreaterEqual(len(list_result.contexts), 10, "Expected at least 10 contexts with larger page size")
        
        print(f"Larger page size: Got {len(list_result.contexts)} contexts (RequestID: {list_result.request_id})")
        print(f"NextToken: {list_result.next_token}, MaxResults: {list_result.max_results}, TotalCount: {list_result.total_count}")

    def test_context_pagination_nil_params(self):
        """Test 5: Test with empty parameters (should use defaults)"""
        print("Test 5: Listing contexts with nil parameters (should use defaults)")
        list_result = self.agent_bay.context.list(None)

        self.assertTrue(list_result.success, "List contexts should be successful")
        # Note: We're not checking for a specific number of contexts since the API behavior
        # may vary, but we're ensuring the call succeeds and returns some data
        self.assertIsNotNone(list_result.contexts, "Contexts should not be None")
        
        print(f"Nil parameters: Got {len(list_result.contexts)} contexts (RequestID: {list_result.request_id})")
        if list_result.next_token:
            print(f"NextToken: {list_result.next_token}, MaxResults: {list_result.max_results}, TotalCount: {list_result.total_count}")


if __name__ == "__main__":
    unittest.main()