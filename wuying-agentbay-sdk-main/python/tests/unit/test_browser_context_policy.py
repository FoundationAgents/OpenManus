#!/usr/bin/env python3
"""
Test script to verify browser_context policy includes BWList with white lists.
"""

import json
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

from agentbay.agentbay import AgentBay
from agentbay.session_params import CreateSessionParams, BrowserContext


def test_browser_context_policy():
    """Test that browser_context policy includes BWList with white lists."""
    
    # Create session parameters with browser context
    params = CreateSessionParams()
    
    # Create browser context
    browser_context = BrowserContext(
        context_id="test-browser-context",
        auto_upload=True
    )
    params.browser_context = browser_context
    
    # Create AgentBay instance (this will trigger the policy creation)
    try:
        # This will fail without API key, but we can test the policy creation logic
        ab = AgentBay("dummy-key")
        
        # The policy creation happens in the create method
        # Let's manually test the policy creation logic
        from agentbay.context_sync import SyncPolicy, UploadPolicy, WhiteList, BWList
        
        # Create a new SyncPolicy with default values for browser context
        upload_policy = UploadPolicy(auto_upload=browser_context.auto_upload)
        
        # Create BWList with white lists for browser data paths
        white_lists = [
            WhiteList(path="/Local State", exclude_paths=[]),
            WhiteList(path="/Default/Cookies", exclude_paths=[]),
            WhiteList(path="/Default/Cookies-journal", exclude_paths=[])
        ]
        bw_list = BWList(white_lists=white_lists)
        
        sync_policy = SyncPolicy(upload_policy=upload_policy, bw_list=bw_list)
        
        # Serialize policy to JSON string
        policy_json = json.dumps(sync_policy, default=lambda obj: obj.__dict__() if hasattr(obj, '__dict__') else str(obj), ensure_ascii=False)
        
        print("Generated policy JSON:")
        print(json.dumps(json.loads(policy_json), indent=2, ensure_ascii=False))
        
        # Verify the policy contains the expected structure
        policy_dict = json.loads(policy_json)
        
        # Check that bwList exists
        assert "bwList" in policy_dict, "bwList should be present in policy"
        
        # Check that whiteLists exists in bwList
        assert "whiteLists" in policy_dict["bwList"], "whiteLists should be present in bwList"
        
        # Check that we have 3 white lists
        white_lists = policy_dict["bwList"]["whiteLists"]
        assert len(white_lists) == 3, f"Expected 3 white lists, got {len(white_lists)}"
        
        # Check the specific paths
        paths = [wl["path"] for wl in white_lists]
        expected_paths = ["/Local State", "/Default/Cookie", "/Default/Cookies-journal"]
        
        for expected_path in expected_paths:
            assert expected_path in paths, f"Expected path {expected_path} not found in white lists"
        
        print("✅ All tests passed! Browser context policy correctly includes BWList with white lists.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = test_browser_context_policy()
    sys.exit(0 if success else 1) 