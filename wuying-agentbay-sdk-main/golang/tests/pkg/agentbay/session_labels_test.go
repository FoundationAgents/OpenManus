package agentbay_test

import (
	"fmt"
	"math/rand"
	"strings"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

// generateUniqueID creates a unique identifier for test labels
// to avoid conflicts with existing data in the database
func generateUniqueID() string {
	// Seed the random number generator to ensure different random numbers each time
	rand.Seed(time.Now().UnixNano())
	timestamp := time.Now().UnixNano()
	randomPart := rand.Intn(10000)
	return fmt.Sprintf("%d-%d", timestamp, randomPart)
}

func TestSession_SetGetLabels(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBayClient, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a new session
	t.Log("Creating a new session for labels testing...")
	sessionResult, err := agentBayClient.Create(nil)
	if err != nil {
		t.Fatalf("Error creating session: %v", err)
	}

	session := sessionResult.Session
	t.Logf("Session created with ID: %s", session.SessionID)

	// Ensure cleanup of session
	defer func() {
		t.Log("Cleaning up session...")
		deleteResult, err := agentBayClient.Delete(session)
		if err != nil {
			t.Logf("Warning: Error deleting session: %v", err)
		} else {
			t.Logf("Session deleted (RequestID: %s)", deleteResult.RequestID)
		}
	}()

	// Generate a unique identifier for this test run
	uniqueID := generateUniqueID()
	t.Logf("Using unique ID for test labels: %s", uniqueID)

	// Define test labels with unique values to avoid conflicts with existing data
	testLabels := map[string]string{
		"environment": fmt.Sprintf("testing-%s", uniqueID),
		"owner":       fmt.Sprintf("test-team-%s", uniqueID),
		"project":     fmt.Sprintf("labels-test-%s", uniqueID),
		"version":     "1.0.0",
	}

	// Test 1: Set labels using SetLabels (using map directly)
	t.Log("Setting labels for the session...")
	labelResult, err := session.SetLabels(testLabels)
	if err != nil {
		t.Fatalf("Error setting labels: %v", err)
	}
	t.Logf("Labels set successfully (RequestID: %s)", labelResult.RequestID)

	// Test 2: Get labels using GetLabels
	t.Log("Getting labels for the session...")
	getLabelResult, err := session.GetLabels()
	if err != nil {
		t.Fatalf("Error getting labels: %v", err)
	}
	t.Logf("Labels retrieved successfully (RequestID: %s)", getLabelResult.RequestID)

	// The labels should be returned as JSON string, we need to verify they contain our test labels
	// For now, just verify that we got some labels back
	if getLabelResult.Labels == "" {
		t.Errorf("Expected non-empty labels, got empty string")
	}

	// Test 3: Update labels (using map directly)
	updatedLabels := map[string]string{
		"environment": fmt.Sprintf("staging-%s", uniqueID),
		"owner":       testLabels["owner"],
		"project":     fmt.Sprintf("labels-test-updated-%s", uniqueID),
		"status":      "active",
	}

	t.Log("Updating labels for the session...")
	updateResult, err := session.SetLabels(updatedLabels)
	if err != nil {
		t.Fatalf("Error updating labels: %v", err)
	}
	t.Logf("Labels updated successfully (RequestID: %s)", updateResult.RequestID)

	fmt.Println("Session labels test completed successfully")
}

// TestSession_SetLabels_ValidationCases tests the validation logic in SetLabels
func TestSession_SetLabels_ValidationCases(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBayClient, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a new session
	sessionResult, err := agentBayClient.Create(nil)
	if err != nil {
		t.Fatalf("Error creating session: %v", err)
	}

	session := sessionResult.Session
	defer func() {
		// Cleanup session
		_, _ = agentBayClient.Delete(session)
	}()

	// Test cases for validation
	testCases := []struct {
		name          string
		labels        map[string]string
		expectError   bool
		errorContains string
	}{
		{
			name:          "Nil labels",
			labels:        nil,
			expectError:   true,
			errorContains: "Labels cannot be nil",
		},
		{
			name:          "Empty labels",
			labels:        map[string]string{},
			expectError:   true,
			errorContains: "Labels cannot be empty",
		},
		{
			name: "Valid labels",
			labels: map[string]string{
				"environment": "production",
				"team":        "backend",
				"version":     "1.0.0",
			},
			expectError: false,
		},
		{
			name: "Empty key",
			labels: map[string]string{
				"":    "value",
				"key": "value",
			},
			expectError:   true,
			errorContains: "Label keys cannot be empty",
		},
		{
			name: "Whitespace-only key",
			labels: map[string]string{
				"   ": "value",
				"key": "value",
			},
			expectError:   true,
			errorContains: "Label keys cannot be empty",
		},
		{
			name: "Empty value",
			labels: map[string]string{
				"key":  "",
				"key2": "value",
			},
			expectError:   true,
			errorContains: "Label values cannot be empty",
		},
		{
			name: "Whitespace-only value",
			labels: map[string]string{
				"key":  "   ",
				"key2": "value",
			},
			expectError:   true,
			errorContains: "Label values cannot be empty",
		},
		{
			name: "Special characters in key (allowed)",
			labels: map[string]string{
				"key-with_special.chars@domain.com": "value",
			},
			expectError: false,
		},
		{
			name: "Special characters in value (allowed)",
			labels: map[string]string{
				"key": "value with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
			},
			expectError: false,
		},
		{
			name: "Unicode in key and value",
			labels: map[string]string{
				"key_name": "value",
				"key":      "value with Chinese and emoji 🚀",
			},
			expectError: false,
		},
		{
			name: "Single character key and value",
			labels: map[string]string{
				"a": "b",
			},
			expectError: false,
		},
		{
			name: "Key with leading and trailing spaces",
			labels: map[string]string{
				" key ": "value",
			},
			expectError: false, // Leading/trailing spaces are allowed, only all-whitespace is rejected
		},
		{
			name: "Value with leading and trailing spaces",
			labels: map[string]string{
				"key": " value ",
			},
			expectError: false, // Leading/trailing spaces are allowed, only all-whitespace is rejected
		},
		{
			name: "Multiple labels with mixed valid cases",
			labels: map[string]string{
				"simple":     "value",
				"with-dash":  "another-value",
				"with_under": "under_value",
				"with.dot":   "dot.value",
				"123numeric": "456value",
			},
			expectError: false,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			result, err := session.SetLabels(tc.labels)
			t.Logf("Running test case: %s", result)
			if tc.expectError {
				// Should have an error
				t.Logf("Expecting error for test case: %s", err)
				if err == nil {
					t.Errorf("Expected error but got none")
					return
				}

				// Check if error message contains expected text
				if tc.errorContains != "" && !strings.Contains(err.Error(), tc.errorContains) {
					t.Errorf("Expected error to contain '%s', but got: %s", tc.errorContains, err.Error())
				}

				t.Logf("Expected error occurred: %s", err.Error())
			} else {
				// Should not have an error
				if err != nil {
					t.Errorf("Expected no error but got: %s", err.Error())
					return
				}

				// Verify the result
				if result == nil {
					t.Errorf("Expected non-nil result but got nil")
					return
				}

				if result.RequestID != "" {
					t.Logf("SetLabels successful (RequestID: %s)", result.RequestID)
				}
			}
		})
	}
}

// TestListByUIDLabel tests querying sessions with a specific UID label
// and verifies pagination functionality
func TestListByUIDLabel(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBayClient, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Define UID filter
	uidFilter := map[string]string{
		"test_group": "multi-session-test-1751262241385739000-4623",
	}

	// Test pagination by setting page size to 3 (expecting 6 total sessions)
	t.Log("Testing pagination with page size of 3...")

	// First page
	params := agentbay.NewListSessionParams()
	params.Labels = uidFilter
	params.MaxResults = 4 // Set page size to 4

	firstPageResult, err := agentBayClient.ListByLabels(params)
	if err != nil {
		t.Fatalf("Error listing first page of sessions: %v", err)
	}

	// Log the first page results
	t.Logf("First page - Sessions listed by UID label (RequestID: %s)", firstPageResult.RequestID)
	t.Logf("First page - Found %d sessions (MaxResults: %d, TotalCount: %d)",
		len(firstPageResult.SessionIds), firstPageResult.MaxResults, firstPageResult.TotalCount)

	// Store session IDs from first page
	firstPageSessionIDs := make(map[string]bool)
	if len(firstPageResult.SessionIds) > 0 {
		t.Log("First page - Sessions found:")
		for i, sessionId := range firstPageResult.SessionIds {
			t.Logf("  %d. Session ID: %s", i+1, sessionId)
			firstPageSessionIDs[sessionId] = true
		}
	} else {
		t.Log("First page - No sessions found with the specified UID label")
	}

	// Check if we have a next token for pagination
	if firstPageResult.NextToken == "" {
		t.Log("No NextToken returned, pagination not possible or not needed")
		return
	}

	// Second page
	t.Log("Fetching second page using NextToken...")
	secondPageParams := agentbay.NewListSessionParams()
	secondPageParams.Labels = uidFilter
	secondPageParams.MaxResults = 3
	secondPageParams.NextToken = firstPageResult.NextToken

	secondPageResult, err := agentBayClient.ListByLabels(secondPageParams)
	if err != nil {
		t.Fatalf("Error listing second page of sessions: %v", err)
	}

	// Log the second page results
	t.Logf("Second page - Sessions listed by UID label (RequestID: %s)", secondPageResult.RequestID)
	t.Logf("Second page - Found %d sessions", len(secondPageResult.SessionIds))

	// Verify second page sessions are different from first page
	if len(secondPageResult.SessionIds) > 0 {
		t.Log("Second page - Sessions found:")
		duplicateFound := false

		for i, sessionId := range secondPageResult.SessionIds {
			t.Logf("  %d. Session ID: %s", i+1, sessionId)

			// Check if this session was already in the first page
			if firstPageSessionIDs[sessionId] {
				duplicateFound = true
				t.Errorf("Session ID %s found in both first and second page", sessionId)
			}
		}

		if !duplicateFound {
			t.Log("Pagination verification successful: No duplicate sessions between pages")
		}
	} else {
		t.Log("Second page - No sessions found")
	}

	// Verify total count
	totalSessionsFound := len(firstPageResult.SessionIds) + len(secondPageResult.SessionIds)
	t.Logf("Total sessions found across both pages: %d", totalSessionsFound)

	if firstPageResult.TotalCount > 0 {
		if int(firstPageResult.TotalCount) != totalSessionsFound {
			t.Errorf("Note: TotalCount (%d) doesn't match actual sessions found (%d)",
				firstPageResult.TotalCount, totalSessionsFound)
		} else {
			t.Logf("TotalCount matches actual sessions found: %d", totalSessionsFound)
		}
	}
}

// TestListByLabels_OnlyUnreleasedSessions tests that ListByLabels only returns unreleased sessions
func TestListByLabels_OnlyUnreleasedSessions(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBayClient, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Generate a unique identifier for this test run
	uniqueID := generateUniqueID()
	t.Logf("Using unique ID for test labels: %s", uniqueID)

	// Define a label to be used for all sessions in this test
	testLabel := map[string]string{
		"test_group": fmt.Sprintf("unreleased-session-test-%s", uniqueID),
	}

	// Number of sessions to create
	const totalSessionCount = 3
	const sessionsToReleaseCount = 1

	// Create multiple sessions with the same label
	var sessions []*agentbay.Session
	t.Logf("Creating %d sessions with the same label...", totalSessionCount)

	for i := 0; i < totalSessionCount; i++ {
		sessionResult, err := agentBayClient.Create(nil)
		if err != nil {
			t.Fatalf("Error creating session %d: %v", i+1, err)
		}

		session := sessionResult.Session
		t.Logf("Session %d created with ID: %s", i+1, session.SessionID)

		// Set the same label for each session (using map directly)
		labelResult, err := session.SetLabels(testLabel)
		if err != nil {
			t.Fatalf("Error setting label for session %d: %v", i+1, err)
		}
		t.Logf("Label set successfully for session %d (RequestID: %s)", i+1, labelResult.RequestID)

		sessions = append(sessions, session)

		// Add a short delay between session creations to avoid rate limiting
		if i < totalSessionCount-1 {
			time.Sleep(2 * time.Second)
		}
	}

	// Store the IDs of all sessions for verification
	allSessionIDs := make(map[string]bool)
	for _, session := range sessions {
		allSessionIDs[session.SessionID] = true
	}

	// Release (delete) some of the sessions
	releasedSessionIDs := make(map[string]bool)
	t.Logf("Releasing %d out of %d sessions...", sessionsToReleaseCount, totalSessionCount)

	for i := 0; i < sessionsToReleaseCount; i++ {
		session := sessions[i]
		deleteResult, err := agentBayClient.Delete(session)
		if err != nil {
			t.Fatalf("Error releasing session %d: %v", i+1, err)
		}
		t.Logf("Session %d with ID %s released (RequestID: %s)", i+1, session.SessionID, deleteResult.RequestID)
		releasedSessionIDs[session.SessionID] = true
	}

	// Ensure cleanup of remaining sessions at the end of the test
	defer func() {
		t.Log("Cleaning up remaining sessions...")
		for i := sessionsToReleaseCount; i < totalSessionCount; i++ {
			session := sessions[i]
			deleteResult, err := agentBayClient.Delete(session)
			if err != nil {
				t.Logf("Warning: Error deleting session %d: %v", i+1, err)
			} else {
				t.Logf("Session %d deleted (RequestID: %s)", i+1, deleteResult.RequestID)
			}
		}
	}()

	// Use ListByLabels to get sessions with the test label
	t.Log("Listing sessions by label to verify only unreleased sessions are returned...")
	params := agentbay.NewListSessionParams()
	params.Labels = testLabel
	sessionsResult, err := agentBayClient.ListByLabels(params)
	if err != nil {
		t.Fatalf("Error listing sessions by label: %v", err)
	}
	t.Logf("Sessions listed by label (RequestID: %s)", sessionsResult.RequestID)

	// Verify that only unreleased sessions are returned
	t.Logf("Found %d sessions in the results", len(sessionsResult.SessionIds))

	// Check each returned session
	for i, sessionId := range sessionsResult.SessionIds {
		t.Logf("Result session %d: ID=%s", i+1, sessionId)

		// Verify this session is one of our test sessions
		if !allSessionIDs[sessionId] {
			t.Logf("Note: Found a session not created in this test: %s", sessionId)
			continue
		}

		// Verify this session was not released
		if releasedSessionIDs[sessionId] {
			t.Errorf("Error: Released session with ID %s was returned by ListByLabels", sessionId)
		}
	}

	// Count how many of our unreleased sessions were found
	expectedUnreleasedCount := totalSessionCount - sessionsToReleaseCount
	foundUnreleasedCount := 0

	for _, sessionId := range sessionsResult.SessionIds {
		if allSessionIDs[sessionId] && !releasedSessionIDs[sessionId] {
			foundUnreleasedCount++
		}
	}

	// Verify that all unreleased sessions were found
	if foundUnreleasedCount != expectedUnreleasedCount {
		t.Errorf("Expected to find %d unreleased sessions, but found %d",
			expectedUnreleasedCount, foundUnreleasedCount)
	} else {
		t.Logf("Successfully found all %d unreleased sessions", expectedUnreleasedCount)
	}

	// Verify that no released sessions were found
	releasedSessionsFound := 0
	for _, sessionId := range sessionsResult.SessionIds {
		if releasedSessionIDs[sessionId] {
			releasedSessionsFound++
		}
	}

	if releasedSessionsFound > 0 {
		t.Errorf("Found %d released sessions in the results, expected 0", releasedSessionsFound)
	} else {
		t.Log("Verified that no released sessions were returned by ListByLabels")
	}

	fmt.Println("ListByLabels only returns unreleased sessions test completed successfully")
}
