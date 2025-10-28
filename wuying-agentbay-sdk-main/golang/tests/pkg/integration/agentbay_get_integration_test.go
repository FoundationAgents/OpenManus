package integration

import (
	"fmt"
	"os"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func TestAgentBayGetAPI(t *testing.T) {
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		t.Fatal("AGENTBAY_API_KEY environment variable is not set")
	}

	client, err := agentbay.NewAgentBay(apiKey, nil)
	if err != nil {
		t.Fatalf("Failed to initialize AgentBay client: %v", err)
	}

	fmt.Println("Creating a new session for Get API testing...")
	createResult, err := client.Create(nil)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	createdSession := createResult.Session
	sessionId := createdSession.SessionID
	t.Logf("Session created with ID: %s", sessionId)

	fmt.Println("Testing Get API...")
	result, err := client.Get(sessionId)
	if err != nil {
		t.Fatalf("Failed to get session: %v", err)
	}

	if result == nil {
		t.Fatal("Get returned nil result")
	}

	if !result.Success {
		t.Fatalf("Get failed: %s", result.ErrorMessage)
	}

	if result.Session == nil {
		t.Fatal("Result.Session is nil")
	}

	if result.Session.SessionID != sessionId {
		t.Errorf("Expected SessionID %s, got %s", sessionId, result.Session.SessionID)
	}

	if result.Session.AgentBay == nil {
		t.Error("Session AgentBay reference is nil")
	}

	if result.RequestID == "" {
		t.Error("RequestID should not be empty")
	}

	t.Logf("Successfully retrieved session with ID: %s", result.Session.SessionID)
	t.Logf("Request ID: %s", result.RequestID)

	fmt.Println("Get API test passed successfully")

	fmt.Println("Cleaning up: Deleting the session...")
	deleteResult, err := result.Session.Delete()
	if err != nil {
		t.Fatalf("Failed to delete session: %v", err)
	}
	t.Logf("Session %s deleted successfully", sessionId)
	if !deleteResult.Success {
		t.Error("Session deletion failed")
	}
}

func TestAgentBayGetNonExistentSession(t *testing.T) {
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		t.Fatal("AGENTBAY_API_KEY environment variable is not set")
	}

	client, err := agentbay.NewAgentBay(apiKey, nil)
	if err != nil {
		t.Fatalf("Failed to initialize AgentBay client: %v", err)
	}

	fmt.Println("Testing Get API with non-existent session ID...")
	nonExistentSessionId := "session-nonexistent-12345"
	result, err := client.Get(nonExistentSessionId)

	// Get should not return error, but result.Success should be false
	if err != nil {
		t.Fatalf("Unexpected error: %v", err)
	}

	if result.Success {
		t.Fatal("Expected failure for non-existent session, got success")
	}

	if result.ErrorMessage == "" {
		t.Error("ErrorMessage should not be empty for failed result")
	}

	t.Logf("Correctly received error for non-existent session: %s", result.ErrorMessage)
	fmt.Println("Get API non-existent session test passed successfully")
}

func TestAgentBayGetEmptySessionId(t *testing.T) {
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		t.Fatal("AGENTBAY_API_KEY environment variable is not set")
	}

	client, err := agentbay.NewAgentBay(apiKey, nil)
	if err != nil {
		t.Fatalf("Failed to initialize AgentBay client: %v", err)
	}

	fmt.Println("Testing Get API with empty session ID...")
	result, err := client.Get("")

	// Get should not return error, but result.Success should be false
	if err != nil {
		t.Fatalf("Unexpected error: %v", err)
	}

	if result.Success {
		t.Fatal("Expected failure for empty session ID, got success")
	}

	expectedErrMsg := "session_id is required"
	if result.ErrorMessage != expectedErrMsg {
		t.Errorf("Expected error message '%s', got '%s'", expectedErrMsg, result.ErrorMessage)
	}

	t.Logf("Correctly received error for empty session ID: %s", result.ErrorMessage)
	fmt.Println("Get API empty session ID test passed successfully")
}
