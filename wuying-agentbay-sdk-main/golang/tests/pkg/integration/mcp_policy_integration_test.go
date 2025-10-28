package integration_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

func TestMcpPolicy_CreateSession_WithPolicyId(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	client, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a session with PolicyId
	policyID := "mpg-04bdvx0p76nbwhdt5"
	params := agentbay.NewCreateSessionParams().
		WithImageId("linux_latest").
		WithPolicyId(policyID)

	t.Logf("Creating session with PolicyId: %s", policyID)
	result, err := client.Create(params)
	if err != nil {
		t.Fatalf("Error creating session with PolicyId: %v", err)
	}

	session := result.Session
	if session == nil || session.SessionID == "" {
		t.Fatalf("Expected valid session, got nil or empty ID")
	}
	t.Logf("Session created successfully with ID: %s (RequestID: %s)", session.SessionID, result.RequestID)

	// Ensure cleanup
	defer func() {
		t.Log("Cleaning up: Deleting the session...")
		if _, err := client.Delete(session); err != nil {
			t.Logf("Warning: Error deleting session: %v", err)
		} else {
			t.Log("Session successfully deleted")
		}
	}()
}
