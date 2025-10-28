package integration

import (
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

// TestSessionDeleteWithoutParams integration test for Delete without parameters
func TestSessionDeleteWithoutParams(t *testing.T) {
	// Get API Key
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		t.Fatal("AGENTBAY_API_KEY environment variable is not set")
	}

	// Initialize AgentBay client
	client, err := agentbay.NewAgentBay(apiKey, nil)
	if err != nil {
		t.Fatalf("Failed to initialize AgentBay client: %v", err)
	}

	// Create a session
	fmt.Println("Creating a new session for delete testing...")
	result, err := client.Create(nil)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	session := result.Session
	t.Logf("Session created with ID: %s", session.SessionID)

	// Delete session using default parameters
	fmt.Println("Deleting session without parameters...")
	deleteResult, err := session.Delete()
	if err != nil {
		t.Fatalf("Failed to delete session: %v", err)
	}
	t.Logf("Session deleted (RequestID: %s)", deleteResult.RequestID)

	// Verify session has been deleted
	listResult, err := client.ListByLabels(agentbay.NewListSessionParams())
	if err != nil {
		t.Fatalf("Failed to list sessions: %v", err)
	}

	for _, sessionId := range listResult.SessionIds {
		if sessionId == session.SessionID {
			t.Errorf("Session with ID %s still exists after deletion", session.SessionID)
		}
	}
}

// TestAgentBayDeleteWithSyncContext integration test for AgentBay.Delete with syncContext parameter
func TestAgentBayDeleteWithSyncContext(t *testing.T) {
	// Get API Key
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		t.Fatal("AGENTBAY_API_KEY environment variable is not set")
	}

	// Initialize AgentBay client
	client, err := agentbay.NewAgentBay(apiKey, nil)
	if err != nil {
		t.Fatalf("Failed to initialize AgentBay client: %v", err)
	}

	// Create context
	contextName := "test-context-" + time.Now().Format("20060102150405")
	fmt.Println("Creating a new context...")
	createResult, err := client.Context.Create(contextName)
	if err != nil {
		t.Fatalf("Failed to create context: %v", err)
	}
	contextID := createResult.ContextID
	t.Logf("Context created with ID: %s", contextID)

	// Create persistence configuration
	persistenceData := []*agentbay.ContextSync{
		{
			ContextID: contextID,
			Path:      "/home/wuying/test",
		},
	}

	// Create session with context
	params := agentbay.NewCreateSessionParams()
	params.ImageId = "linux_latest"
	params.ContextSync = persistenceData

	fmt.Println("Creating a new session with context...")
	result, err := client.Create(params)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	session := result.Session
	t.Logf("Session created with ID: %s", session.SessionID)

	// Create 1GB test file in session
	fmt.Println("Creating a 1GB test file for agentbay delete...")
	testCmd := "dd if=/dev/zero of=/home/wuying/test/testfile2.txt bs=1M count=1024"
	cmdResult, err := session.Command.ExecuteCommand(testCmd)
	if err != nil {
		t.Logf("Warning: Failed to create 1GB test file: %v", err)
	} else {
		t.Logf("Created 1GB test file: %s", cmdResult)
	}

	// Delete session using client.Delete with syncContext=true
	fmt.Println("Deleting session with AgentBay.Delete and syncContext=true...")
	deleteResult, err := client.Delete(session, true)
	if err != nil {
		t.Fatalf("Failed to delete session: %v", err)
	}
	t.Logf("Session deleted with client.Delete and syncContext=true (RequestID: %s)", deleteResult.RequestID)

	// Verify session has been deleted
	listResult, err := client.ListByLabels(agentbay.NewListSessionParams())
	if err != nil {
		t.Fatalf("Failed to list sessions: %v", err)
	}

	for _, sessionId := range listResult.SessionIds {
		if sessionId == session.SessionID {
			t.Errorf("Session with ID %s still exists after deletion", session.SessionID)
		}
	}

	// Clean up context
	// Create Context object for deletion
	getResult, err := client.Context.Get(contextName, false)
	if err == nil && getResult != nil && getResult.Context != nil {
		_, err = client.Context.Delete(getResult.Context)
		if err != nil {
			t.Logf("Warning: Failed to delete context: %v", err)
		} else {
			t.Logf("Context %s deleted", contextID)
		}
	}
}
