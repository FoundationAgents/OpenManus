import os
import random
import sys
import time
import unittest

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

# Add the parent directory to the path so we can import the agentbay package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_test_api_key():
    """Get API key for testing"""
    api_key = os.environ.get("AGENTBAY_API_KEY")
    if not api_key:
        api_key = "akm-xxx"  # Replace with your test API key
        print(
            "Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for testing."
        )
    return api_key


def generate_unique_id():
    """Create a unique identifier for test labels to avoid conflicts with existing data"""
    timestamp = int(time.time() * 1000000)
    random_part = random.randint(0, 10000)
    return f"{timestamp}-{random_part}"


class TestAgentBayList(unittest.TestCase):
    """Integration tests for AgentBay.list() API."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for the entire test class."""
        api_key = get_test_api_key()
        cls.agent_bay = AgentBay(api_key=api_key)

        # Generate a unique identifier for this test run
        cls.unique_id = generate_unique_id()
        print(f"Using unique ID for test: {cls.unique_id}")

        # Create multiple sessions with different labels for testing
        cls.sessions = []

        # Session 1: project=list-test, environment=dev
        print("Creating session 1 with dev environment...")
        params1 = CreateSessionParams(
            labels={
                "project": f"list-test-{cls.unique_id}",
                "environment": "dev",
                "owner": f"test-{cls.unique_id}",
            }
        )
        result1 = cls.agent_bay.create(params1)
        if result1.success:
            cls.sessions.append(result1.session)
            print(f"Session 1 created: {result1.session.session_id}")
            print(f"Request ID: {result1.request_id}")

        # Session 2: project=list-test, environment=staging
        print("Creating session 2 with staging environment...")
        params2 = CreateSessionParams(
            labels={
                "project": f"list-test-{cls.unique_id}",
                "environment": "staging",
                "owner": f"test-{cls.unique_id}",
            }
        )
        result2 = cls.agent_bay.create(params2)
        if result2.success:
            cls.sessions.append(result2.session)
            print(f"Session 2 created: {result2.session.session_id}")
            print(f"Request ID: {result2.request_id}")

            # Session 3: project=list-test, environment=prod
        print("Creating session 3 with prod environment...")
        params3 = CreateSessionParams(
            labels={
                "project": f"list-test-{cls.unique_id}",
                "environment": "prod",
                "owner": f"test-{cls.unique_id}",
            }
        )
        # Retry logic for session 3 creation
        max_retries = 3
        for attempt in range(max_retries):
            result3 = cls.agent_bay.create(params3)
            if result3.success:
                cls.sessions.append(result3.session)
                print(f"Session 3 created: {result3.session.session_id}")
                print(f"Request ID: {result3.request_id}")
                break
            else:
                print(f"Attempt {attempt + 1} failed to create session 3: {result3.error_message}")
                if attempt < max_retries - 1:
                    print("Waiting 15 seconds before retrying...")
                    time.sleep(15)

        # Verify all sessions were created
        if len(cls.sessions) != 3:
            raise RuntimeError(f"Failed to create all 3 test sessions. Only created {len(cls.sessions)} sessions.")

        # Wait a bit for sessions to be fully created and labels to propagate
        time.sleep(5)

    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures after all tests in the class have been run."""
        print("Cleaning up: Deleting all test sessions...")
        for session in cls.sessions:
            try:
                result = cls.agent_bay.delete(session)
                print(
                    f"Session {session.session_id} deleted. Success: {result.success}, Request ID: {result.request_id}"
                )
            except Exception as e:
                print(f"Warning: Error deleting session {session.session_id}: {e}")

    def test_list_all_sessions(self):
        """Test listing all sessions without any label filter."""
        print("\n=== Testing list() without labels ===")

        result = self.agent_bay.list()

        # Verify the result
        self.assertTrue(result.success, "list() should succeed")
        self.assertIsNotNone(result.request_id, "Request ID should be present")
        self.assertIsNotNone(result.session_ids, "Session IDs list should not be None")

        print(f"Total sessions found: {result.total_count}")
        print(f"Sessions in current page: {len(result.session_ids)}")
        print(f"Request ID: {result.request_id}")

    def test_list_with_single_label(self):
        """Test listing sessions with a single label filter."""
        print("\n=== Testing list() with single label ===")

        # List sessions with project label
        result = self.agent_bay.list(labels={"project": f"list-test-{self.unique_id}"})

        # Verify the result
        self.assertTrue(result.success, "list() with single label should succeed")
        self.assertIsNotNone(result.request_id, "Request ID should be present")
        self.assertGreaterEqual(
            len(result.session_ids), 3, "Should find at least 3 sessions"
        )

        # Verify all returned sessions have the expected label
        session_ids = [s.session_id for s in self.sessions]
        found_count = 0
        for session_id in result.session_ids:
            if session_id in session_ids:
                found_count += 1

        self.assertEqual(
            found_count, 3, "Should find exactly 3 test sessions"
        )

        print(f"Found {found_count} test sessions")
        print(f"Total sessions with label: {len(result.session_ids)}")
        print(f"Request ID: {result.request_id}")

    def test_list_with_multiple_labels(self):
        """Test listing sessions with multiple label filters."""
        print("\n=== Testing list() with multiple labels ===")

        # List sessions with project and environment labels
        result = self.agent_bay.list(
            labels={
                "project": f"list-test-{self.unique_id}",
                "environment": "dev",
            }
        )

        # Verify the result
        self.assertTrue(result.success, "list() with multiple labels should succeed")
        self.assertIsNotNone(result.request_id, "Request ID should be present")
        self.assertGreaterEqual(
            len(result.session_ids), 1, "Should find at least 1 session"
        )

        # Verify the dev session is in the results
        dev_session_id = self.sessions[0].session_id
        found = False
        for session_id in result.session_ids:
            if session_id == dev_session_id:
                found = True
                break

        self.assertTrue(found, "Dev session should be in the results")

        print(f"Found dev session: {found}")
        print(f"Total matching sessions: {len(result.session_ids)}")
        print(f"Request ID: {result.request_id}")

    def test_list_with_pagination(self):
        """Test listing sessions with pagination parameters."""
        print("\n=== Testing list() with pagination ===")

        # List first page with limit of 2
        result_page1 = self.agent_bay.list(
            labels={"project": f"list-test-{self.unique_id}"}, page=1, limit=2
        )

        # Verify first page
        self.assertTrue(result_page1.success, "First page should succeed")
        self.assertIsNotNone(result_page1.request_id, "Request ID should be present")
        self.assertLessEqual(
            len(result_page1.session_ids), 2, "First page should have at most 2 sessions"
        )

        print(f"Page 1 - Found {len(result_page1.session_ids)} sessions")
        print(f"Request ID: {result_page1.request_id}")

        # If there are more results, test page 2
        if result_page1.next_token:
            result_page2 = self.agent_bay.list(
                labels={"project": f"list-test-{self.unique_id}"}, page=2, limit=2
            )

            self.assertTrue(result_page2.success, "Second page should succeed")
            self.assertIsNotNone(
                result_page2.request_id, "Request ID should be present"
            )

            print(f"Page 2 - Found {len(result_page2.session_ids)} sessions")
            print(f"Request ID: {result_page2.request_id}")

    def test_list_with_non_matching_label(self):
        """Test listing sessions with a label that doesn't match any session."""
        print("\n=== Testing list() with non-matching label ===")

        # List sessions with a label that doesn't exist
        result = self.agent_bay.list(
            labels={
                "project": f"list-test-{self.unique_id}",
                "environment": "nonexistent",
            }
        )

        # Verify the result
        self.assertTrue(result.success, "list() should succeed even with no matches")
        self.assertIsNotNone(result.request_id, "Request ID should be present")

        # Verify our test sessions are NOT in the results
        session_ids = [s.session_id for s in self.sessions]
        found_count = 0
        for session_id in result.session_ids:
            if session_id in session_ids:
                found_count += 1

        self.assertEqual(found_count, 0, "Should not find any test sessions")

        print(f"Correctly found {found_count} test sessions (expected 0)")
        print(f"Request ID: {result.request_id}")

    def test_list_default_limit(self):
        """Test that list() uses default limit of 10 when not specified."""
        print("\n=== Testing list() with default limit ===")

        result = self.agent_bay.list(labels={"owner": f"test-{self.unique_id}"})

        # Verify the result
        self.assertTrue(result.success, "list() should succeed")
        self.assertIsNotNone(result.request_id, "Request ID should be present")
        self.assertEqual(result.max_results, 10, "Default limit should be 10")

        print(f"Max results: {result.max_results}")
        print(f"Request ID: {result.request_id}")

    def test_list_request_id_present(self):
        """Test that all list() responses include request_id."""
        print("\n=== Testing list() request_id presence ===")

        # Test 1: No labels
        result1 = self.agent_bay.list()
        self.assertIsNotNone(result1.request_id, "Request ID should be present")
        self.assertNotEqual(result1.request_id, "", "Request ID should not be empty")
        print(f"Test 1 Request ID: {result1.request_id}")

        # Test 2: With labels
        result2 = self.agent_bay.list(labels={"project": f"list-test-{self.unique_id}"})
        self.assertIsNotNone(result2.request_id, "Request ID should be present")
        self.assertNotEqual(result2.request_id, "", "Request ID should not be empty")
        print(f"Test 2 Request ID: {result2.request_id}")

        # Test 3: With pagination
        result3 = self.agent_bay.list(
            labels={"project": f"list-test-{self.unique_id}"}, page=1, limit=5
        )
        self.assertIsNotNone(result3.request_id, "Request ID should be present")
        self.assertNotEqual(result3.request_id, "", "Request ID should not be empty")
        print(f"Test 3 Request ID: {result3.request_id}")

    def test_list_error_scenarios(self):
        """Test error handling for invalid page numbers and out-of-range pages."""
        print("\n=== Testing list() error scenarios ===")

        # Test 1: Invalid page number (page = 0)
        print("\nTest 1: page=0 should return error")
        result = self.agent_bay.list(
            labels={"project": f"list-test-{self.unique_id}"}, page=0, limit=5
        )
        self.assertFalse(result.success, "page=0 should fail")
        self.assertIsNotNone(result.error_message, "Error message should be present")
        self.assertIn("Page number must be >= 1", result.error_message)
        print(f"✓ Correctly rejected page=0: {result.error_message}")

        # Test 2: Invalid page number (page = -1)
        print("\nTest 2: page=-1 should return error")
        result = self.agent_bay.list(
            labels={"project": f"list-test-{self.unique_id}"}, page=-1, limit=5
        )
        self.assertFalse(result.success, "page=-1 should fail")
        self.assertIsNotNone(result.error_message, "Error message should be present")
        self.assertIn("Page number must be >= 1", result.error_message)
        print(f"✓ Correctly rejected page=-1: {result.error_message}")

        # Test 3: Out-of-range page number (page way beyond available data)
        print("\nTest 3: page=999999 should return error (no more pages)")
        result = self.agent_bay.list(
            labels={"project": f"list-test-{self.unique_id}"}, page=999999, limit=2
        )
        self.assertFalse(result.success, "page=999999 should fail")
        self.assertIsNotNone(result.error_message, "Error message should be present")
        self.assertIn("No more pages available", result.error_message)
        print(f"✓ Correctly handled out-of-range page: {result.error_message}")

    def test_list_pagination_completeness(self):
        """Test traversing all pages until next_token is empty and verify total count."""
        print("\n=== Testing list() pagination completeness ===")

        all_session_ids = []
        page = 1
        limit = 2
        total_count_from_api = 0

        print(f"\nTraversing all pages with limit={limit}...")

        while True:
            result = self.agent_bay.list(
                labels={"project": f"list-test-{self.unique_id}"}, page=page, limit=limit
            )

            # Verify each page request succeeds
            self.assertTrue(
                result.success, f"Page {page} request should succeed"
            )
            self.assertIsNotNone(
                result.request_id, f"Page {page} should have request_id"
            )

            # Collect session IDs
            all_session_ids.extend(result.session_ids)
            total_count_from_api = result.total_count

            print(
                f"Page {page}: Found {len(result.session_ids)} sessions, "
                f"NextToken: {'Yes' if result.next_token else 'No'}, "
                f"Total count: {result.total_count}"
            )

            # Verify page size constraint
            self.assertLessEqual(
                len(result.session_ids),
                limit,
                f"Page {page} should have at most {limit} sessions",
            )

            # Check if we've reached the end
            if not result.next_token:
                print(f"\n✓ Reached last page (page {page})")
                break

            page += 1

            # Safety check to prevent infinite loop
            if page > 100:
                self.fail("Pagination exceeded 100 pages, possible infinite loop")

        # Verify we collected at least our 3 test sessions
        self.assertGreaterEqual(
            len(all_session_ids),
            3,
            f"Should find at least 3 sessions across all pages, found {len(all_session_ids)}",
        )

        # Verify our test sessions are in the collected IDs
        test_session_ids = [s.session_id for s in self.sessions]
        found_count = sum(1 for sid in all_session_ids if sid in test_session_ids)
        self.assertEqual(
            found_count, 3, f"Should find all 3 test sessions, found {found_count}"
        )

        # Verify no duplicate session IDs
        unique_session_ids = set(all_session_ids)
        self.assertEqual(
            len(all_session_ids),
            len(unique_session_ids),
            "Should not have duplicate session IDs across pages",
        )

        print(f"\n✓ Pagination completeness verified:")
        print(f"  - Total pages traversed: {page}")
        print(f"  - Total sessions collected: {len(all_session_ids)}")
        print(f"  - Total count from API: {total_count_from_api}")
        print(f"  - Found all 3 test sessions: Yes")
        print(f"  - No duplicates: Yes")

    def test_list_total_count_consistency(self):
        """Test that total_count is consistent with actual session count."""
        print("\n=== Testing list() total_count consistency ===")

        # Test 1: Verify total_count >= number of test sessions
        print("\nTest 1: total_count should be >= 3 (our test sessions)")
        result = self.agent_bay.list(
            labels={"owner": f"test-{self.unique_id}"}, limit=10
        )

        self.assertTrue(result.success, "List should succeed")
        self.assertGreaterEqual(
            result.total_count,
            3,
            f"total_count should be >= 3, got {result.total_count}",
        )
        print(f"✓ total_count = {result.total_count} (>= 3)")

        # Test 2: Verify total_count remains consistent across multiple calls
        print("\nTest 2: total_count should be consistent across multiple calls")
        result2 = self.agent_bay.list(
            labels={"owner": f"test-{self.unique_id}"}, limit=10
        )

        self.assertEqual(
            result.total_count,
            result2.total_count,
            "total_count should be consistent across calls",
        )
        print(f"✓ total_count consistent: {result.total_count} == {result2.total_count}")

        # Test 3: Verify total_count matches actual sessions when collecting all pages
        print("\nTest 3: total_count should match actual session count across all pages")

        all_session_ids = []
        page = 1
        limit = 2
        expected_total_count = 0

        while True:
            result = self.agent_bay.list(
                labels={"project": f"list-test-{self.unique_id}"}, page=page, limit=limit
            )

            if not result.success:
                break

            all_session_ids.extend(result.session_ids)
            expected_total_count = result.total_count

            if not result.next_token:
                break

            page += 1

            if page > 100:
                break

        # The total_count should match the number of unique sessions collected
        unique_session_ids = set(all_session_ids)
        self.assertEqual(
            len(unique_session_ids),
            expected_total_count,
            f"Collected {len(unique_session_ids)} unique sessions, "
            f"but total_count is {expected_total_count}",
        )

        print(
            f"✓ total_count matches actual count: "
            f"{expected_total_count} == {len(unique_session_ids)}"
        )

        # Test 4: Verify session_ids count <= total_count for each page
        print("\nTest 4: session_ids count should be <= total_count on each page")
        result = self.agent_bay.list(
            labels={"owner": f"test-{self.unique_id}"}, limit=2
        )

        self.assertLessEqual(
            len(result.session_ids),
            result.total_count,
            f"session_ids count ({len(result.session_ids)}) should be <= "
            f"total_count ({result.total_count})",
        )
        print(
            f"✓ session_ids count ({len(result.session_ids)}) <= "
            f"total_count ({result.total_count})"
        )


if __name__ == "__main__":
    unittest.main()

