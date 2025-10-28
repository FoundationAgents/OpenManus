package agentbay_test

import (
	"fmt"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

// Create a context from the context result
func contextFromResult(result *agentbay.ContextResult) *agentbay.Context {
	if result == nil || result.Context == nil {
		return nil
	}

	return result.Context
}

// TestContext_GetNonExistentContext tests attempting to get a context that doesn't exist
func TestContext_GetNonExistentContext(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Try to get a non-existent context with AllowCreate=false
	nonExistentName := fmt.Sprintf("non-existent-context-%d", time.Now().Unix())
	t.Logf("Attempting to get non-existent context: %s with AllowCreate=false", nonExistentName)

	result, err := agentBay.Context.Get(nonExistentName, false)

	// We expect either an error or a nil context since the context doesn't exist
	// and we're not allowing creation
	if err == nil && result != nil && result.ContextID != "" {
		// If we somehow got a context, make sure to clean it up
		t.Errorf("Unexpectedly got a context when requesting a non-existent one with AllowCreate=false: %+v", result.Context)

		context := contextFromResult(result)
		// Clean up the unexpected context
		_, cleanupErr := agentBay.Context.Delete(context)
		if cleanupErr != nil {
			t.Logf("Warning: Error cleaning up unexpected context: %v", cleanupErr)
		}
	} else {
		// This is the expected outcome - either an error or nil context
		t.Logf("As expected, failed to get non-existent context or got nil: err=%v, result=%+v", err, result)
	}
}

// TestContext_Create tests creating a new context
func TestContext_Create(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a new context
	contextName := "test-context-" + fmt.Sprintf("%d", time.Now().Unix())
	result, err := agentBay.Context.Create(contextName)
	if err != nil {
		t.Fatalf("Error creating context: %v", err)
	}
	if result == nil {
		t.Fatalf("Context not created")
	}

	// Get the created context to get its full details
	getResult, err := agentBay.Context.Get(contextName, false)
	if err != nil {
		t.Fatalf("Error getting created context: %v", err)
	}

	context := contextFromResult(getResult)
	t.Logf("Created context: %s (%s) with RequestID: %s", context.Name, context.ID, result.RequestID)

	// Verify the created context has the expected name
	if context.Name != contextName {
		t.Errorf("Expected context name to be '%s', got '%s'", contextName, context.Name)
	}
	if context.ID == "" {
		t.Errorf("Expected non-empty context ID")
	}

	// Clean up
	_, err = agentBay.Context.Delete(context)
	if err != nil {
		t.Logf("Warning: Error deleting context: %v", err)
	}
}

// TestContext_Get tests retrieving a context by name
func TestContext_Get(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// First create a context
	contextName := "test-context-" + fmt.Sprintf("%d", time.Now().Unix())
	createResult, err := agentBay.Context.Create(contextName)
	if err != nil {
		t.Fatalf("Error creating context: %v", err)
	}

	originalContextID := createResult.ContextID

	// Get the created context to get its full details
	firstGetResult, err := agentBay.Context.Get(contextName, false)
	if err != nil {
		t.Fatalf("Error getting created context: %v", err)
	}

	context := contextFromResult(firstGetResult)

	// Ensure cleanup of the context after test
	defer func() {
		_, err := agentBay.Context.Delete(context)
		if err != nil {
			t.Logf("Warning: Error deleting context: %v", err)
		}
	}()

	// Get the context we just created (second time)
	getResult, err := agentBay.Context.Get(contextName, false)
	if err != nil {
		t.Fatalf("Error getting context: %v", err)
	}
	if getResult == nil {
		t.Fatalf("Context not found")
	}

	retrievedContext := contextFromResult(getResult)
	// Verify the retrieved context matches what we created
	if retrievedContext.Name != contextName {
		t.Errorf("Expected retrieved context name to be '%s', got '%s'", contextName, retrievedContext.Name)
	}
	if retrievedContext.ID != originalContextID {
		t.Errorf("Expected retrieved context ID to be '%s', got '%s'", originalContextID, retrievedContext.ID)
	}
	t.Logf("Successfully retrieved context: %s (%s) with RequestID: %s",
		retrievedContext.Name, retrievedContext.ID, getResult.RequestID)
}

// TestContext_List tests listing all contexts
func TestContext_List(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Get initial list of contexts
	initialListResult, err := agentBay.Context.List(agentbay.NewContextListParams())
	if err != nil {
		t.Fatalf("Error listing contexts: %v", err)
	}

	initialContexts := initialListResult.Contexts
	t.Logf("Found %d contexts initially with RequestID: %s",
		len(initialContexts), initialListResult.RequestID)

	// Create a new context
	contextName := "test-context-" + fmt.Sprintf("%d", time.Now().Unix())
	createResult, err := agentBay.Context.Create(contextName)
	if err != nil {
		t.Fatalf("Error creating context: %v", err)
	}

	originalContextID := createResult.ContextID

	// Get the created context to get its full details
	getResult, err := agentBay.Context.Get(contextName, false)
	if err != nil {
		t.Fatalf("Error getting created context: %v", err)
	}

	context := contextFromResult(getResult)

	// Ensure cleanup of the context after test
	defer func() {
		_, err := agentBay.Context.Delete(context)
		if err != nil {
			t.Logf("Warning: Error deleting context: %v", err)
		}
	}()

	// List contexts again and verify our new context is in the list
	listResult, err := agentBay.Context.List(agentbay.NewContextListParams())
	if err != nil {
		t.Fatalf("Error listing contexts: %v", err)
	}

	allContexts := listResult.Contexts

	// Verify the list contains our new context
	var foundInList bool
	for _, c := range allContexts {
		if c.ID == originalContextID {
			foundInList = true
			if c.Name != contextName {
				t.Errorf("Expected context name in list to be '%s', got '%s'", contextName, c.Name)
			}
			break
		}
	}
	if !foundInList {
		t.Errorf("New context with ID '%s' not found in context list", originalContextID)
	}

	// Verify the list contains at least one more context than the initial list
	if len(allContexts) <= len(initialContexts) {
		t.Errorf("Expected context list to grow, but it didn't: initial=%d, current=%d",
			len(initialContexts), len(allContexts))
	}
	t.Logf("Successfully listed contexts with RequestID: %s, found our context in the list",
		listResult.RequestID)
}

// TestContext_Update tests updating a context's name
func TestContext_Update(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// First create a context
	contextName := "test-context-" + fmt.Sprintf("%d", time.Now().Unix())
	createResult, err := agentBay.Context.Create(contextName)
	if err != nil {
		t.Fatalf("Error creating context: %v", err)
	}

	originalContextID := createResult.ContextID

	// Get the created context to get its full details
	getResult, err := agentBay.Context.Get(contextName, false)
	if err != nil {
		t.Fatalf("Error getting created context: %v", err)
	}

	context := contextFromResult(getResult)

	// Ensure cleanup of the context after test
	defer func() {
		_, err := agentBay.Context.Delete(context)
		if err != nil {
			t.Logf("Warning: Error deleting context: %v", err)
		}
	}()

	// Update the context
	updatedName := "updated-" + contextName
	context.Name = updatedName
	updateResult, err := agentBay.Context.Update(context)
	if err != nil {
		t.Fatalf("Error updating context: %v", err)
	}
	if !updateResult.Success {
		t.Fatalf("Context update reported as unsuccessful")
	}
	t.Logf("Context update reported as successful with RequestID: %s", updateResult.RequestID)

	// Verify the update by getting the context again
	updatedGetResult, err := agentBay.Context.Get(updatedName, false)
	if err != nil {
		t.Fatalf("Error getting updated context: %v", err)
	}
	if updatedGetResult == nil {
		t.Fatalf("Updated context not found")
	}

	retrievedUpdatedContext := contextFromResult(updatedGetResult)
	// Verify the retrieved context has the updated name
	if retrievedUpdatedContext.Name != updatedName {
		t.Errorf("Expected retrieved context name to be '%s', got '%s'", updatedName, retrievedUpdatedContext.Name)
	}
	if retrievedUpdatedContext.ID != originalContextID {
		t.Errorf("Expected retrieved context ID to be '%s', got '%s'", originalContextID, retrievedUpdatedContext.ID)
	}
}

// TestContext_Delete tests deleting a context
func TestContext_Delete(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// First create a context
	contextName := "test-context-" + fmt.Sprintf("%d", time.Now().Unix())
	createResult, err := agentBay.Context.Create(contextName)
	if err != nil {
		t.Fatalf("Error creating context: %v", err)
	}

	originalContextID := createResult.ContextID

	// Get the created context to get its full details
	getResult, err := agentBay.Context.Get(contextName, false)
	if err != nil {
		t.Fatalf("Error getting created context: %v", err)
	}

	context := contextFromResult(getResult)

	// Delete the context
	deleteResult, err := agentBay.Context.Delete(context)
	if err != nil {
		t.Fatalf("Error deleting context: %v", err)
	}
	t.Logf("Context successfully deleted with RequestID: %s", deleteResult.RequestID)

	// Verify the context is actually deleted
	deletedGetResult, err := agentBay.Context.Get(contextName, false)
	if err == nil && deletedGetResult != nil && deletedGetResult.ContextID == originalContextID {
		t.Errorf("Context still exists after deletion")

		deletedContext := contextFromResult(deletedGetResult)
		// Clean up if it still exists
		_, cleanupErr := agentBay.Context.Delete(deletedContext)
		if cleanupErr != nil {
			t.Logf("Warning: Error cleaning up context: %v", cleanupErr)
		}
	}
}
