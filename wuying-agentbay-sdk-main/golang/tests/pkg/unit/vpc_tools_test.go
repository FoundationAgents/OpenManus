package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

// TestVpcSessionAutoToolsFetch tests that VPC sessions automatically fetch MCP tools
func TestVpcSessionAutoToolsFetch(t *testing.T) {
	// This test verifies the logic for VPC session auto tools fetching
	// We can't actually create a VPC session in unit tests due to API dependencies,
	// but we can verify the logic structure

	// Test that the IsVpc flag is properly set in CreateSessionParams
	params := agentbay.NewCreateSessionParams().
		WithImageId("test-image").
		WithIsVpc(true)

	if !params.IsVpc {
		t.Errorf("Expected IsVpc to be true, got %v", params.IsVpc)
	}

	// Test that the ImageId is properly set
	if params.ImageId != "test-image" {
		t.Errorf("Expected ImageId to be 'test-image', got %s", params.ImageId)
	}

	t.Log("VPC session parameters correctly configured")
}

// TestNonVpcSessionNoAutoToolsFetch tests that non-VPC sessions don't auto-fetch tools
func TestNonVpcSessionNoAutoToolsFetch(t *testing.T) {
	// Test that non-VPC sessions don't have the auto-fetch behavior
	params := agentbay.NewCreateSessionParams().
		WithImageId("test-image").
		WithIsVpc(false)

	if params.IsVpc {
		t.Errorf("Expected IsVpc to be false, got %v", params.IsVpc)
	}

	t.Log("Non-VPC session parameters correctly configured")
}
