import os
import random
import sys
import time
import unittest

from agentbay import AgentBay

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


class TestSessionLabels(unittest.TestCase):
    """Test cases for session labels functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for the entire test class."""
        api_key = get_test_api_key()
        cls.agent_bay = AgentBay(api_key=api_key)

        # Create a session
        print("Creating a new session for labels testing...")
        result = cls.agent_bay.create()
        cls.session = result.session
        print(f"Session created with ID: {cls.session.session_id}")
        print(f"Request ID: {result.request_id}")

        # Generate a unique identifier for this test run
        cls.unique_id = generate_unique_id()
        print(f"Using unique ID for test labels: {cls.unique_id}")

    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures after all tests in the class have been run."""
        print("Cleaning up: Deleting the session...")
        try:
            result = cls.agent_bay.delete(cls.session)
            print(
                f"Session deleted. Success: {result.success}",
                f"Request ID: {result.request_id}",
            )
        except Exception as e:
            print(f"Warning: Error deleting session: {e}")

    def test_set_get_labels(self):
        """Test setting and getting labels for a session."""
        # Define test labels with unique values to avoid conflicts with existing data
        test_labels = {
            "environment": f"testing-{self.unique_id}",
            "owner": f"test-team-{self.unique_id}",
            "project": f"labels-test-{self.unique_id}",
            "version": "1.0.0",
        }

        # Test 1: Set labels using set_labels
        print("Setting labels for the session...")
        try:
            set_result = self.session.set_labels(test_labels)
            self.assertTrue(set_result.success, "Failed to set labels")
            print(f"Labels set successfully. Request ID: {set_result.request_id}")
        except Exception as e:
            self.fail(f"Error setting labels: {e}")

        # Test 2: Get labels using get_labels
        print("Getting labels for the session...")
        try:
            get_result = self.session.get_labels()
            print(f"Retrieved labels: {get_result.data}")
            print(f"Request ID: {get_result.request_id}")

            # Get the actual labels data from the result object
            retrieved_labels = get_result.data

            # Verify that all expected labels are present with correct values
            for key, expected_value in test_labels.items():
                self.assertIn(
                    key,
                    retrieved_labels,
                    f"Expected label '{key}' not found in retrieved labels",
                )
                self.assertEqual(
                    expected_value,
                    retrieved_labels[key],
                    f"Label '{key}' value mismatch: expected '{expected_value}'"
                    f"got '{retrieved_labels[key]}'",
                )
        except Exception as e:
            self.fail(f"Error getting labels: {e}")

        # Test 3: Verify labels using list_by_labels
        print("Verifying labels using list_by_labels...")

        # Test with a single label (using the unique value)
        single_label_filter = {"environment": test_labels["environment"]}

        try:
            list_result = self.agent_bay.list_by_labels(single_label_filter)
            print(
                f"Found {len(list_result.session_ids)} sessions with single label filter.",
                f"Request ID: {list_result.request_id}",
            )

            # Check if our session is in the results
            self.assertIn(
                self.session.session_id,
                list_result.session_ids,
                "Session not found when filtering by single label",
            )
            print("Session successfully found when filtering by single label")
        except Exception as e:
            self.fail(f"Error listing sessions by single label: {e}")

        # Test with multiple labels (using the unique values)
        multi_label_filter = {
            "environment": test_labels["environment"],
            "project": test_labels["project"],
        }

        try:
            list_result = self.agent_bay.list_by_labels(multi_label_filter)
            print(
                f"Found {len(list_result.session_ids)} sessions with multiple labels filter.",
                f"Request ID: {list_result.request_id}",
            )

            # Check if our session is in the results
            self.assertIn(
                self.session.session_id,
                list_result.session_ids,
                "Session not found when filtering by multiple labels",
            )
            print("Session successfully found when filtering by multiple labels")
        except Exception as e:
            self.fail(f"Error listing sessions by multiple labels: {e}")

        # Test with non-matching label
        non_matching_filter = {
            # This doesn't match our session
            "environment": f"production-{self.unique_id}"
        }

        try:
            list_result = self.agent_bay.list_by_labels(non_matching_filter)
            print(
                f"Found {len(list_result.session_ids)} sessions with non-matching filter. Request ID: {list_result.request_id}"
            )

            # Check that our session is NOT in the results
            self.assertNotIn(
                self.session.session_id,
                list_result.session_ids,
                "Session found when filtering by non-matching label",
            )
            print("Session correctly not found when filtering by non-matching label")
        except Exception as e:
            self.fail(f"Error listing sessions by non-matching label: {e}")

        # Test 4: Update labels (using the unique values)
        updated_labels = {
            "environment": f"staging-{self.unique_id}",
            "owner": test_labels["owner"],
            "project": f"labels-test-updated-{self.unique_id}",
            "status": "active",
        }

        print("Updating labels for the session...")
        try:
            set_result = self.session.set_labels(updated_labels)
            self.assertTrue(set_result.success, "Failed to update labels")
            print(f"Labels updated successfully. Request ID: {set_result.request_id}")
        except Exception as e:
            self.fail(f"Error updating labels: {e}")

        # Verify updated labels using get_labels
        print("Getting updated labels for the session...")
        try:
            get_result = self.session.get_labels()
            retrieved_updated_labels = get_result.data
            print(f"Retrieved updated labels: {retrieved_updated_labels}")
            print(f"Request ID: {get_result.request_id}")

            # Verify that all expected updated labels are present with correct values
            for key, expected_value in updated_labels.items():
                self.assertIn(
                    key,
                    retrieved_updated_labels,
                    f"Expected updated label '{key}' not found in retrieved labels",
                )
                self.assertEqual(
                    expected_value,
                    retrieved_updated_labels[key],
                    f"Updated label '{key}' value mismatch: expected '{expected_value}'"
                    f"got '{retrieved_updated_labels[key]}'",
                )

            # Verify that the old label that was removed is no longer present
            self.assertNotIn(
                "version",
                retrieved_updated_labels,
                "Removed label 'version' still present in updated labels",
            )
        except Exception as e:
            self.fail(f"Error getting updated labels: {e}")

        # Verify updated labels using list_by_labels with the new environment value
        updated_env_filter = {"environment": updated_labels["environment"]}

        try:
            list_result = self.agent_bay.list_by_labels(updated_env_filter)
            print(
                f"Found {len(list_result.session_ids)} sessions with updated environment filter.",
                f"Request ID: {list_result.request_id}",
            )

            self.assertIn(
                self.session.session_id,
                list_result.session_ids,
                "Session not found when filtering by updated environment label",
            )
            print(
                "Session successfully found when filtering by updated environment label"
            )
        except Exception as e:
            self.fail(f"Error listing sessions by updated environment label: {e}")

        # The session should no longer be found with the old environment value
        old_env_filter = {"environment": test_labels["environment"]}

        try:
            list_result = self.agent_bay.list_by_labels(old_env_filter)
            print(
                f"Found {len(list_result.session_ids)} sessions with old environment filter.",
                f"Request ID: {list_result.request_id}",
            )

            self.assertNotIn(
                self.session.session_id,
                list_result.session_ids,
                "Session found when filtering by old environment label",
            )
            print("Session correctly not found when filtering by old environment label")
        except Exception as e:
            self.fail(f"Error listing sessions by old environment label: {e}")

        print("Session labels test completed successfully")

    def test_empty_labels_handling(self):
        """2.4 Empty labels handling test - should handle setting empty labels object"""
        # Prerequisites: Session instance has been created
        # Test objective: Verify handling of setting empty labels object

        empty_labels = {}
        set_result = self.session.set_labels(empty_labels)

        # Verification points - based on validation logic, empty labels should fail
        self.assertFalse(set_result.success)
        self.assertIn("empty", set_result.error_message.lower())

        print(f"Empty labels handled correctly")
 # 5. Error Handling Tests
    def test_set_labels_invalid_parameters(self):
        """5.1 setLabels invalid parameter handling test - should handle invalid parameters"""
        # Prerequisites: Session instance has been created
        # Test objective: Verify handling when invalid parameters are passed

        # Test None parameter
        null_result = self.session.set_labels(None)
        print(f"Null result: {null_result}")
        self.assertFalse(null_result.success)
        self.assertIn("null", null_result.error_message.lower())
        self.assertEqual(null_result.request_id, "")

        # Test non-dict type parameters
        string_result = self.session.set_labels("invalid")
        self.assertFalse(string_result.success)
        self.assertIn("invalid", string_result.error_message.lower())

        number_result = self.session.set_labels(123)
        self.assertFalse(number_result.success)
        self.assertIn("invalid", number_result.error_message.lower())

        boolean_result = self.session.set_labels(True)
        self.assertFalse(boolean_result.success)
        self.assertIn("invalid", boolean_result.error_message.lower())

        # Test list type parameters
        array_result = self.session.set_labels([])
        print(f"Array result: {array_result.error_message}")
        self.assertFalse(array_result.success)
        self.assertIn("array", array_result.error_message.lower())

        array_with_data_result = self.session.set_labels([{"key": "value"}])
        self.assertFalse(array_with_data_result.success)
        self.assertIn("array", array_with_data_result.error_message.lower())

        print(f"setLabels invalid parameters: All invalid parameter types correctly rejected")

    def test_set_labels_empty_object(self):
        """5.2 setLabels empty object handling test - should handle empty object"""
        # Prerequisites: Session instance has been created
        # Test objective: Verify handling when empty object is passed

        empty_result = self.session.set_labels({})
        self.assertFalse(empty_result.success)
        self.assertIn("empty", empty_result.error_message.lower())
        self.assertEqual(empty_result.request_id, "")

        print(f"setLabels empty object: Empty object correctly rejected")

    def test_set_labels_empty_keys_values(self):
        """5.3 setLabels empty keys/values handling test - should handle empty keys or values"""
        # Prerequisites: Session instance has been created
        # Test objective: Verify handling when empty keys or values are passed

        # Test empty key
        empty_key_result = self.session.set_labels({"": "value"})
        self.assertFalse(empty_key_result.success)
        self.assertIn("keys", empty_key_result.error_message.lower())
        self.assertEqual(empty_key_result.request_id, "")

        # Test empty value
        empty_value_result = self.session.set_labels({"key": ""})
        self.assertFalse(empty_value_result.success)
        self.assertIn("values", empty_value_result.error_message.lower())
        self.assertEqual(empty_value_result.request_id, "")

        # Test None value
        null_value_result = self.session.set_labels({"key": None})
        self.assertFalse(null_value_result.success)
        self.assertIn("values", null_value_result.error_message.lower())

        print(f"setLabels empty keys/values: All empty keys and values correctly rejected")

    def test_set_labels_mixed_invalid_parameters(self):
        """5.4 setLabels mixed invalid parameters test - should handle mixed invalid parameters with proper priority"""
        # Prerequisites: Session instance has been created
        # Test objective: Verify priority handling of mixed invalid parameters

        # Test mixed situation with empty key and valid key-value pair
        mixed_empty_key_result = self.session.set_labels({
            "validKey": "validValue",
            "": "emptyKeyValue"
        })
        self.assertFalse(mixed_empty_key_result.success)
        self.assertIn("keys", mixed_empty_key_result.error_message.lower())

        # Test mixed situation with empty value and valid key-value pair
        mixed_empty_value_result = self.session.set_labels({
            "validKey": "validValue",
            "emptyValueKey": ""
        })
        self.assertFalse(mixed_empty_value_result.success)
        self.assertIn("values", mixed_empty_value_result.error_message.lower())

        # Test multiple invalid key-value pairs
        multiple_invalid_result = self.session.set_labels({
            "": "emptyKey",
            "emptyValue": "",
            "nullValue": None
        })
        self.assertFalse(multiple_invalid_result.success)
        # Should return the first encountered error (empty key)
        self.assertIn("keys", multiple_invalid_result.error_message.lower())

        print(f"setLabels mixed invalid parameters: Mixed invalid parameters correctly handled with proper priority")
    def test_set_labels_boundary_cases(self):
        """5.5 setLabels boundary cases test - should handle boundary cases"""
        # Prerequisites: Session instance has been created
        # Test objective: Verify handling of boundary cases

        # Test key with only whitespace
        whitespace_key_result = self.session.set_labels({" ": "value"})
        self.assertFalse(whitespace_key_result.success)

        # Test value with only whitespace
        whitespace_value_result = self.session.set_labels({"key": " "})
        self.assertFalse(whitespace_value_result.success)

        # Test zero-length but non-empty special cases (if any exist)
        special_chars_result = self.session.set_labels({
            "key1": "value1",
            "key2": "value2"
        })
        self.assertTrue(special_chars_result.success)

        print(f"setLabels boundary cases: Boundary cases correctly handled")

if __name__ == "__main__":
    unittest.main()
