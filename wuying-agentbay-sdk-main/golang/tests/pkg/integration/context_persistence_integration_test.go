package integration_test

import (
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

// Helper function to check if a string contains "tool not found"
func containsToolNotFound(s string) bool {
	return strings.Contains(strings.ToLower(s), "tool not found")
}

// TestContextPersistence tests the persistence of files across sessions with the same context
// and the isolation of files between different contexts.
func TestContextPersistence(t *testing.T) {
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}
	t.Logf("AgentBay client initialized successfully with region: %s", agentBay.APIKey)

	// Step 1: Create a new context
	contextName := fmt.Sprintf("test-context-%d", time.Now().Unix())
	t.Logf("Creating new context with name: %s", contextName)

	// List existing contexts before creation
	listResult, err := agentBay.Context.List(agentbay.NewContextListParams())
	if err != nil {
		t.Logf("Warning: Failed to list existing contexts: %v", err)
	} else {
		existingContexts := listResult.Contexts
		t.Logf("Found %d existing contexts before creation (RequestID: %s)",
			len(existingContexts), listResult.RequestID)
		for i, ctx := range existingContexts {
			t.Logf("Existing context %d: ID=%s, Name=%s, State=%s, OSType=%s",
				i+1, ctx.ID, ctx.Name, ctx.State, ctx.OSType)
		}
	}

	createResult, err := agentBay.Context.Create(contextName)
	if err != nil {
		t.Fatalf("Error creating context: %v", err)
	}

	// Get the created context to get its full details
	getResult, err := agentBay.Context.Get(contextName, false)
	if err != nil {
		t.Fatalf("Error getting created context: %v", err)
	}

	context := getResult.Context
	t.Logf("Context created successfully - ID: %s, Name: %s, State: %s, OSType: %s (RequestID: %s)",
		context.ID, context.Name, context.State, context.OSType, createResult.RequestID)

	// Create a unique filename for testing in the home directory
	testFilePath := fmt.Sprintf("~/test-file-%d.txt", time.Now().Unix())
	testFileContent := "This is a test file for context persistence"

	// Step 2: Create a session with context sync
	t.Log("Creating first session with context sync...")
	params := agentbay.NewCreateSessionParams()
	contextSync := &agentbay.ContextSync{
		ContextID: context.ID,
		Path:      "/home/wuying",
		Policy:    agentbay.NewSyncPolicy(),
	}
	params.AddContextSyncConfig(contextSync)
	params.ImageId = "linux_latest"

	// List active sessions before creation
	listSessionResult, err := agentBay.ListByLabels(agentbay.NewListSessionParams())
	if err != nil {
		t.Logf("Warning: Failed to list active sessions: %v", err)
	} else {
		activeSessionIds := listSessionResult.SessionIds
		t.Logf("Found %d active sessions before creation (RequestID: %s)",
			len(activeSessionIds), listSessionResult.RequestID)
		for i, sessionId := range activeSessionIds {
			t.Logf("Active session %d: ID=%s", i+1, sessionId)
		}
	}

	sessionResult, err := agentBay.Create(params)
	if err != nil {
		t.Fatalf("Error creating session with context sync: %v", err)
	}
	session1 := sessionResult.Session
	t.Logf("Session created with ID: %s, AgentBay client region: %s (RequestID: %s)",
		session1.SessionID, session1.AgentBay.APIKey, sessionResult.RequestID)

	// Step 3: Use Execute command to create a file
	t.Logf("Creating test file at %s...", testFilePath)
	createFileCmd := fmt.Sprintf("echo '%s' > %s", testFileContent, testFilePath)
	t.Logf("Executing command: %s", createFileCmd)

	// First check if the file already exists (it shouldn't)
	checkCmd := fmt.Sprintf("ls -la %s 2>&1 || echo 'File does not exist'", testFilePath)
	checkResult, err := session1.Command.ExecuteCommand(checkCmd)
	if err != nil {
		t.Logf("Warning: Pre-check command failed: %v", err)
	}
	t.Logf("Pre-check output: %s (RequestID: %s)",
		checkResult.Output, checkResult.RequestID)

	// Now create the file
	cmdResult, err := session1.Command.ExecuteCommand(createFileCmd)
	if err != nil {
		t.Logf("Warning: Command execution failed: %v", err)
		if containsToolNotFound(cmdResult.Output) {
			t.Skip("Skipping test as execute_command tool is not available")
		}
	}
	t.Logf("File creation output: %s (RequestID: %s)",
		cmdResult.Output, cmdResult.RequestID)

	// Verify the file was created
	verifyCmd := fmt.Sprintf("cat %s", testFilePath)
	t.Logf("Verifying file with command: %s", verifyCmd)
	verifyResult, err := session1.Command.ExecuteCommand(verifyCmd)
	if err != nil {
		t.Fatalf("Error verifying file creation: %v", err)
	}

	// Also check file attributes
	lsCmd := fmt.Sprintf("ls -la %s", testFilePath)
	lsResult, lsErr := session1.Command.ExecuteCommand(lsCmd)
	if lsErr != nil {
		t.Logf("Warning: Could not get file attributes: %v", lsErr)
	} else {
		t.Logf("File attributes: %s (RequestID: %s)",
			lsResult.Output, lsResult.RequestID)
	}

	if !strings.Contains(verifyResult.Output, testFileContent) {
		t.Fatalf("File content verification failed. Expected to contain '%s', got: '%s'",
			testFileContent, verifyResult.Output)
	}
	t.Logf("File created and verified successfully with content: %s (RequestID: %s)",
		verifyResult.Output, verifyResult.RequestID)

	// Step 4: Release the session
	t.Log("Releasing first session...")
	deleteResult, err := agentBay.Delete(session1)
	if err != nil {
		t.Fatalf("Error releasing session: %v", err)
	}
	t.Logf("First session released successfully (RequestID: %s)",
		deleteResult.RequestID)

	// Add a 20-second delay to ensure the session is fully released
	t.Log("Waiting for 20 seconds before creating the second session...")
	time.Sleep(20 * time.Second)

	// Step 5: Create another session with the same context
	t.Log("Creating second session with the same context...")
	params = agentbay.NewCreateSessionParams()
	contextSync = &agentbay.ContextSync{
		ContextID: context.ID,
		Path:      "/home/wuying",
		Policy:    agentbay.NewSyncPolicy(),
	}
	params.AddContextSyncConfig(contextSync)
	params.ImageId = "linux_latest"

	// List active sessions before creating second session
	listSessionResult, err = agentBay.ListByLabels(agentbay.NewListSessionParams())
	if err != nil {
		t.Logf("Warning: Failed to list active sessions before second session creation: %v", err)
	} else {
		activeSessionIds := listSessionResult.SessionIds
		t.Logf("Found %d active sessions before second session creation (RequestID: %s)",
			len(activeSessionIds), listSessionResult.RequestID)
		for i, sessionId := range activeSessionIds {
			t.Logf("Active session %d: ID=%s", i+1, sessionId)
		}
	}

	// Check context state before creating second session
	contextBeforeResult, err := agentBay.Context.Get(contextName, false)
	if err != nil {
		t.Logf("Warning: Failed to get context before second session creation: %v", err)
	} else if contextBeforeResult != nil {
		contextBefore := contextBeforeResult.Context
		t.Logf("Context state before second session: ID=%s, Name=%s, State=%s, OSType=%s (RequestID: %s)",
			contextBefore.ID, contextBefore.Name, contextBefore.State, contextBefore.OSType,
			contextBeforeResult.RequestID)
	}

	session2Result, err := agentBay.Create(params)
	if err != nil {
		t.Logf("Error creating second session with context sync: %v", err)
		t.Logf("This may be due to resource limits or the context being in use.")

		// Try to clean up the context before failing
		t.Log("Attempting to clean up context before failing...")
		deleteContextResult, cleanupErr := agentBay.Context.Delete(context)
		if cleanupErr != nil {
			t.Logf("Warning: Failed to clean up context: %v", cleanupErr)
		} else {
			t.Logf("Successfully cleaned up context %s (RequestID: %s)",
				context.ID, deleteContextResult.RequestID)
		}

		t.Fatalf("Failed to create second session with context sync: %v", err)
	}
	session2 := session2Result.Session
	t.Logf("Second session created with ID: %s, AgentBay client region: %s (RequestID: %s)",
		session2.SessionID, session2.AgentBay.APIKey, session2Result.RequestID)

	// Step 6: Check if the file still exists (expected: yes)
	t.Logf("Checking if file %s still exists in the second session...", testFilePath)
	verifyResult, err = session2.Command.ExecuteCommand(verifyCmd)
	if err != nil {
		t.Fatalf("Error checking file existence in second session: %v", err)
	}
	if !strings.Contains(verifyResult.Output, testFileContent) {
		t.Fatalf("File persistence test failed. Expected file to exist with content '%s', got: '%s'",
			testFileContent, verifyResult.Output)
	}
	t.Logf("File persistence verified: file exists in the second session (RequestID: %s)",
		verifyResult.RequestID)

	// Step 7: Release the second session
	t.Log("Releasing second session...")
	deleteResult, err = agentBay.Delete(session2)
	if err != nil {
		t.Fatalf("Error releasing second session: %v", err)
	}
	t.Logf("Second session released successfully (RequestID: %s)",
		deleteResult.RequestID)

	// Step 8: Create a session without context sync
	t.Log("Creating third session without context sync...")

	// List active sessions before creating third session
	listSessionResult, err = agentBay.ListByLabels(agentbay.NewListSessionParams())
	if err != nil {
		t.Logf("Warning: Failed to list active sessions before third session creation: %v", err)
	} else {
		activeSessionIds := listSessionResult.SessionIds
		t.Logf("Found %d active sessions before third session creation (RequestID: %s)",
			len(activeSessionIds), listSessionResult.RequestID)
	}

	params = agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	session3Result, err := agentBay.Create(params)
	if err != nil {
		t.Fatalf("Error creating third session without context sync: %v", err)
	}
	session3 := session3Result.Session
	t.Logf("Third session created with ID: %s (RequestID: %s)",
		session3.SessionID, session3Result.RequestID)

	// Step 9: Check if the file exists in the third session (expected: no)
	t.Logf("Checking if file %s exists in the third session (should not exist)...", testFilePath)
	checkResult, err = session3.Command.ExecuteCommand(checkCmd)
	if err != nil {
		t.Logf("Warning: Check command in third session failed: %v", err)
	}
	t.Logf("Check output in third session: %s (RequestID: %s)",
		checkResult.Output, checkResult.RequestID)

	// Try to read the file directly
	verifyResult, err = session3.Command.ExecuteCommand(verifyCmd)
	// We expect this to fail or return an error message
	if err == nil && strings.Contains(verifyResult.Output, testFileContent) {
		t.Errorf("File isolation test failed. File unexpectedly exists in session without context")
	} else {
		t.Logf("File isolation verified: file does not exist in session without context")
	}

	// Step 10: Clean up all resources
	t.Log("Cleaning up all resources...")

	// Release the third session
	deleteResult, err = agentBay.Delete(session3)
	if err != nil {
		t.Logf("Warning: Error releasing third session: %v", err)
	} else {
		t.Logf("Third session released successfully (RequestID: %s)",
			deleteResult.RequestID)
	}

	// Delete the context
	deleteContextResult, err := agentBay.Context.Delete(context)
	if err != nil {
		t.Logf("Warning: Error deleting context: %v", err)
	} else {
		t.Logf("Context deleted successfully (RequestID: %s)",
			deleteContextResult.RequestID)
	}

	t.Log("Test completed successfully")
}
