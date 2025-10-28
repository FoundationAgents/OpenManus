import json
import unittest

from agentbay.session_params import CreateSessionParams
from agentbay.api.models import ExtraConfigs, MobileExtraConfig, AppManagerRule


class TestCreateSessionParams(unittest.TestCase):
    def test_default_initialization(self):
        """Test that CreateSessionParams initializes with default values."""
        params = CreateSessionParams()
        self.assertEqual(params.labels, {})

    def test_custom_labels(self):
        """Test that CreateSessionParams accepts custom labels."""
        labels = {"username": "alice", "project": "my-project"}
        params = CreateSessionParams(labels=labels)
        self.assertEqual(params.labels, labels)

    def test_labels_json_conversion(self):
        """Test that labels can be converted to JSON for the API request."""
        labels = {"username": "alice", "project": "my-project"}
        params = CreateSessionParams(labels=labels)

        # Simulate what happens in AgentBay.create()
        labels_json = json.dumps(params.labels)

        # Verify the JSON string
        parsed_labels = json.loads(labels_json)
        self.assertEqual(parsed_labels, labels)

    def test_policy_id(self):
        """Test that policy_id can be carried by CreateSessionParams."""
        params = CreateSessionParams(policy_id="policy-xyz")
        self.assertEqual(params.policy_id, "policy-xyz")

    def test_extra_configs_initialization(self):
        """Test that CreateSessionParams accepts extra_configs parameter."""
        # Create mobile configuration with whitelist
        app_rule = AppManagerRule(
            rule_type="White",
            app_package_name_list=["com.example.app", "com.trusted.service"]
        )
        mobile_config = MobileExtraConfig(
            lock_resolution=True,
            app_manager_rule=app_rule
        )
        extra_configs = ExtraConfigs(mobile=mobile_config)
        
        params = CreateSessionParams(extra_configs=extra_configs)
        self.assertEqual(params.extra_configs, extra_configs)
        self.assertEqual(params.extra_configs.mobile.lock_resolution, True)
        self.assertEqual(params.extra_configs.mobile.app_manager_rule.rule_type, "White")
        self.assertEqual(len(params.extra_configs.mobile.app_manager_rule.app_package_name_list), 2)

    def test_mobile_extra_config_whitelist(self):
        """Test MobileExtraConfig with app whitelist configuration."""
        app_rule = AppManagerRule(
            rule_type="White",
            app_package_name_list=["com.allowed.app1", "com.allowed.app2"]
        )
        mobile_config = MobileExtraConfig(
            lock_resolution=True,
            app_manager_rule=app_rule
        )
        
        self.assertTrue(mobile_config.lock_resolution)
        self.assertEqual(mobile_config.app_manager_rule.rule_type, "White")
        self.assertIn("com.allowed.app1", mobile_config.app_manager_rule.app_package_name_list)
        self.assertIn("com.allowed.app2", mobile_config.app_manager_rule.app_package_name_list)

    def test_mobile_extra_config_blacklist(self):
        """Test MobileExtraConfig with app blacklist configuration."""
        app_rule = AppManagerRule(
            rule_type="Black",
            app_package_name_list=["com.malware.app", "com.blocked.service"]
        )
        mobile_config = MobileExtraConfig(
            lock_resolution=False,
            app_manager_rule=app_rule
        )
        
        self.assertFalse(mobile_config.lock_resolution)
        self.assertEqual(mobile_config.app_manager_rule.rule_type, "Black")
        self.assertIn("com.malware.app", mobile_config.app_manager_rule.app_package_name_list)

    def test_app_manager_rule_validation(self):
        """Test AppManagerRule validation with various inputs."""
        # Test with valid string list
        app_rule = AppManagerRule(
            rule_type="White",
            app_package_name_list=["com.valid.app", "com.another.app"]
        )
        # Should not raise any exception
        app_rule.validate()
        
        # Test with empty list
        app_rule_empty = AppManagerRule(
            rule_type="Black",
            app_package_name_list=[]
        )
        app_rule_empty.validate()  # Should not raise

    def test_extra_configs_to_map(self):
        """Test ExtraConfigs serialization to dictionary."""
        app_rule = AppManagerRule(
            rule_type="White",
            app_package_name_list=["com.test.app"]
        )
        mobile_config = MobileExtraConfig(
            lock_resolution=True,
            app_manager_rule=app_rule
        )
        extra_configs = ExtraConfigs(mobile=mobile_config)
        
        config_dict = extra_configs.to_map()
        
        self.assertIn("Mobile", config_dict)
        self.assertIn("LockResolution", config_dict["Mobile"])
        self.assertIn("AppManagerRule", config_dict["Mobile"])
        self.assertTrue(config_dict["Mobile"]["LockResolution"])
        self.assertEqual(config_dict["Mobile"]["AppManagerRule"]["RuleType"], "White")
        self.assertEqual(config_dict["Mobile"]["AppManagerRule"]["AppPackageNameList"], ["com.test.app"])

    def test_extra_configs_from_map(self):
        """Test ExtraConfigs deserialization from dictionary."""
        config_dict = {
            "Mobile": {
                "LockResolution": False,
                "AppManagerRule": {
                    "RuleType": "Black",
                    "AppPackageNameList": ["com.blocked.app1", "com.blocked.app2"]
                }
            }
        }
        
        extra_configs = ExtraConfigs()
        extra_configs.from_map(config_dict)
        
        self.assertIsNotNone(extra_configs.mobile)
        self.assertFalse(extra_configs.mobile.lock_resolution)
        self.assertEqual(extra_configs.mobile.app_manager_rule.rule_type, "Black")
        self.assertEqual(len(extra_configs.mobile.app_manager_rule.app_package_name_list), 2)
        self.assertIn("com.blocked.app1", extra_configs.mobile.app_manager_rule.app_package_name_list)


if __name__ == "__main__":
    unittest.main()
