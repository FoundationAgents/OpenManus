package testutil

import (
	"fmt"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

// TestSession holds the session and client for testing
type TestSession struct {
	Client  *agentbay.AgentBay
	Session *agentbay.Session
	T       *testing.T
}

// GetTestAPIKey retrieves the API key for testing
func GetTestAPIKey(t *testing.T) string {
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		apiKey = "akm-xxx" // Replace with your test API key
		t.Logf("Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for testing.")
	}
	return apiKey
}

// SetupTestSession creates a new AgentBay client and session for testing
func SetupTestSession(t *testing.T, params *agentbay.CreateSessionParams) *TestSession {
	// Initialize AgentBay client
	apiKey := GetTestAPIKey(t)
	client, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a session
	fmt.Println("Creating a new session for testing...")
	result, err := client.Create(params)
	if err != nil {
		t.Fatalf("Error creating session: %v", err)
	}

	session := result.Session
	t.Logf("Session created with ID: %s", session.SessionID)

	return &TestSession{
		Client:  client,
		Session: session,
		T:       t,
	}
}

// Cleanup deletes the session after test completion
func (ts *TestSession) Cleanup() {
	fmt.Println("Cleaning up: Deleting the session...")
	_, err := ts.Client.Delete(ts.Session)
	if err != nil {
		ts.T.Logf("Warning: Error deleting session: %v", err)
	} else {
		ts.T.Log("Session successfully deleted")
	}
}

// SetupAndCleanup creates a session and returns it along with a cleanup function
// This is useful for defer-based cleanup
func SetupAndCleanup(t *testing.T, params *agentbay.CreateSessionParams) (*agentbay.Session, func()) {
	testSession := SetupTestSession(t, params)
	return testSession.Session, func() {
		testSession.Cleanup()
	}
}

// ContainsToolNotFound checks if a string contains "tool not found"
func ContainsToolNotFound(s string) bool {
	return strings.Contains(strings.ToLower(s), "tool not found")
}

// SleepWithMessage waits for the specified number of seconds with a message
func SleepWithMessage(seconds int, message string) {
	fmt.Println(message)
	time.Sleep(time.Duration(seconds) * time.Second)
}
