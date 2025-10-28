import os
import sys
import unittest

from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.api.models import ExtraConfigs, MobileExtraConfig, AppManagerRule
from agentbay.exceptions import AgentBayError

# Add the parent directory to the path so we can import the agentbay package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSessionExtraConfigsIntegration(unittest.TestCase):
    """Integration test cases for session creation with extra configurations using real API."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment with real API key."""
        cls.api_key = os.getenv("AGENTBAY_API_KEY", "your_api_key")
        cls.agent_bay = AgentBay(api_key=cls.api_key)

    def test_create_session_with_mobile_config_integration(self):
        """Integration test for creating a session with mobile configuration."""
        print("Testing session creation with mobile configuration...")
        
        # Create mobile configuration with whitelist
        app_rule = AppManagerRule(
            rule_type="White",
            app_package_name_list=[
                "com.android.settings",
                "com.example.test.app",
                "com.trusted.service"
            ]
        )
        mobile_config = MobileExtraConfig(
            lock_resolution=True,
            app_manager_rule=app_rule
        )
        extra_configs = ExtraConfigs(mobile=mobile_config)

        # Create session parameters with mobile_latest image
        params = CreateSessionParams(
            image_id="mobile_latest",  # Specify mobile image
            labels={
                "test_type": "mobile_config_integration",
                "config_type": "whitelist",
                "created_by": "integration_test"
            },
            extra_configs=extra_configs
        )

        # Create session
        result = self.__class__.agent_bay.create(params)
        print(f"Session creation result: {result.success}")
        
        if result.success:
            self.assertIsNotNone(result.session)
            session = result.session
            if session is not None:
                print(f"Mobile session created with ID: {session.session_id}")
                
                # Verify session properties
                self.assertIsNotNone(session.session_id)
                
                # Test session info
                try:
                    info_result = session.info()
                    if info_result.success:
                        print(f"Session info retrieved successfully")
                        print(f"Resource URL: {info_result.data.resource_url}")
                        # Verify this is a mobile session (check for android or mobile indicators)
                        resource_url_lower = info_result.data.resource_url.lower()
                        self.assertTrue(
                            "android" in resource_url_lower or "mobile" in resource_url_lower,
                            f"Session should be mobile-based, got URL: {info_result.data.resource_url}"
                        )
                    else:
                        print(f"Failed to get session info: {info_result.error_message}")
                except Exception as e:
                    print(f"Session info call failed: {e}")

                # Clean up
                try:
                    delete_result = self.__class__.agent_bay.delete(session)
                    if delete_result.success:
                        print("Mobile session deleted successfully")
                    else:
                        print(f"Failed to delete mobile session: {delete_result.error_message}")
                        
                    self.assertTrue(delete_result.success, "Session deletion should succeed")
                except Exception as e:
                    print(f"Session deletion failed: {e}")
        else:
            print(f"Failed to create mobile session: {result.error_message}")
            # Fail the test if mobile session creation fails in real environment
            self.fail(f"Mobile session creation should succeed in real environment: {result.error_message}")

    def test_create_session_with_mobile_blacklist_integration(self):
        """Integration test for creating a session with mobile blacklist configuration."""
        print("Testing session creation with mobile blacklist configuration...")
        
        # Create mobile configuration with blacklist
        app_rule = AppManagerRule(
            rule_type="Black",
            app_package_name_list=[
                "com.malware.suspicious",
                "com.unwanted.adware",
                "com.blocked.app"
            ]
        )
        mobile_config = MobileExtraConfig(
            lock_resolution=False,  # Allow flexible resolution
            app_manager_rule=app_rule
        )
        extra_configs = ExtraConfigs(mobile=mobile_config)

        # Create session parameters with mobile_latest image
        params = CreateSessionParams(
            image_id="mobile_latest",  # Specify mobile image
            labels={
                "test_type": "mobile_config_integration", 
                "config_type": "blacklist",
                "security": "enabled",
                "created_by": "integration_test"
            },
            extra_configs=extra_configs
        )

        # Create session
        result = self.__class__.agent_bay.create(params)
        print(f"Secure session creation result: {result.success}")
        
        if result.success:
            self.assertIsNotNone(result.session)
            session = result.session
            if session is not None:
                print(f"Secure mobile session created with ID: {session.session_id}")
                
                # Verify session properties
                self.assertIsNotNone(session.session_id)
                
                # Test session info to verify mobile environment
                try:
                    info_result = session.info()
                    if info_result.success:
                        print(f"Session info retrieved successfully")
                        print(f"Resource URL: {info_result.data.resource_url}")
                        # Verify this is a mobile session (check for android or mobile indicators)
                        resource_url_lower = info_result.data.resource_url.lower()
                        self.assertTrue(
                            "android" in resource_url_lower or "mobile" in resource_url_lower,
                            f"Session should be mobile-based, got URL: {info_result.data.resource_url}"
                        )
                    else:
                        print(f"Failed to get session info: {info_result.error_message}")
                except Exception as e:
                    print(f"Session info call failed: {e}")
                
                # Verify labels were set
                try:
                    labels_result = session.get_labels()
                    if labels_result.success:
                        labels = labels_result.data
                        print(f"Session labels: {labels}")
                        self.assertEqual(labels.get("config_type"), "blacklist")
                        self.assertEqual(labels.get("security"), "enabled")
                    else:
                        print(f"Failed to get session labels: {labels_result.error_message}")
                except Exception as e:
                    print(f"Get labels call failed: {e}")

                # Clean up
                try:
                    delete_result = self.__class__.agent_bay.delete(session)
                    if delete_result.success:
                        print("Secure mobile session deleted successfully")
                    else:
                        print(f"Failed to delete secure mobile session: {delete_result.error_message}")
                        
                    self.assertTrue(delete_result.success, "Session deletion should succeed")
                except Exception as e:
                    print(f"Session deletion failed: {e}")
        else:
            print(f"Failed to create secure mobile session: {result.error_message}")
            # Fail the test if mobile session creation fails in real environment
            self.fail(f"Secure mobile session creation should succeed in real environment: {result.error_message}")


if __name__ == "__main__":
    unittest.main()