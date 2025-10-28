package integration_test

import (
	"fmt"
	"math/rand"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

func generateUniqueID() string {
	timestamp := time.Now().UnixNano() / 1000
	randomPart := rand.Intn(10000)
	return fmt.Sprintf("%d-%d", timestamp, randomPart)
}

// TestAgentBay_List_Integration tests the List API with end-to-end integration
func TestAgentBay_List_Integration(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBayClient, err := agentbay.NewAgentBay(apiKey, nil)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Generate unique ID for this test run
	uniqueID := generateUniqueID()
	t.Logf("Using unique ID for test: %s", uniqueID)

	// Create multiple sessions with different labels for testing
	var testSessions []*agentbay.Session

	// Session 1: project=list-test, environment=dev
	t.Log("Creating session 1 with dev environment...")
	params1 := agentbay.NewCreateSessionParams().WithLabels(map[string]string{
		"project":     fmt.Sprintf("list-test-%s", uniqueID),
		"environment": "dev",
		"owner":       fmt.Sprintf("test-%s", uniqueID),
	})
	result1, err := agentBayClient.Create(params1)
	if err != nil {
		t.Fatalf("Error creating session 1: %v", err)
	}
	testSessions = append(testSessions, result1.Session)
	t.Logf("Session 1 created: %s", result1.Session.SessionID)
	t.Logf("Request ID: %s", result1.RequestID)

	// Session 2: project=list-test, environment=staging
	t.Log("Creating session 2 with staging environment...")
	params2 := agentbay.NewCreateSessionParams().WithLabels(map[string]string{
		"project":     fmt.Sprintf("list-test-%s", uniqueID),
		"environment": "staging",
		"owner":       fmt.Sprintf("test-%s", uniqueID),
	})
	result2, err := agentBayClient.Create(params2)
	if err != nil {
		t.Fatalf("Error creating session 2: %v", err)
	}
	testSessions = append(testSessions, result2.Session)
	t.Logf("Session 2 created: %s", result2.Session.SessionID)
	t.Logf("Request ID: %s", result2.RequestID)

	// Session 3: project=list-test, environment=prod
	t.Log("Creating session 3 with prod environment...")
	params3 := agentbay.NewCreateSessionParams().WithLabels(map[string]string{
		"project":     fmt.Sprintf("list-test-%s", uniqueID),
		"environment": "prod",
		"owner":       fmt.Sprintf("test-%s", uniqueID),
	})
	result3, err := agentBayClient.Create(params3)
	if err != nil {
		t.Fatalf("Error creating session 3: %v", err)
	}
	testSessions = append(testSessions, result3.Session)
	t.Logf("Session 3 created: %s", result3.Session.SessionID)
	t.Logf("Request ID: %s", result3.RequestID)

	// Wait a bit for sessions to be fully created
	time.Sleep(2 * time.Second)

	// Cleanup function
	defer func() {
		t.Log("Cleaning up: Deleting all test sessions...")
		for _, session := range testSessions {
			result, err := agentBayClient.Delete(session)
			if err != nil {
				t.Logf("Warning: Error deleting session %s: %v", session.SessionID, err)
			} else {
				t.Logf("Session %s deleted. Success: %v, Request ID: %s",
					session.SessionID, result.Success, result.RequestID)
			}
		}
	}()

	// Test 1: List all sessions without any label filter
	t.Run("ListAllSessions", func(t *testing.T) {
		t.Log("\n=== Testing List() without labels ===")

		result, err := agentBayClient.List(nil, nil, nil)
		if err != nil {
			t.Fatalf("Error listing all sessions: %v", err)
		}

		// Verify the result
		if result.RequestID == "" {
			t.Error("Request ID should be present")
		}
		if result.SessionIds == nil {
			t.Error("SessionIds list should not be nil")
		}

		t.Logf("Total sessions found: %d", result.TotalCount)
		t.Logf("Request ID: %s", result.RequestID)
	})

	// Test 2: List sessions with a single label filter
	t.Run("ListWithSingleLabel", func(t *testing.T) {
		t.Log("\n=== Testing List() with single label ===")

		result, err := agentBayClient.List(
			map[string]string{"project": fmt.Sprintf("list-test-%s", uniqueID)},
			nil,
			nil,
		)
		if err != nil {
			t.Fatalf("Error listing sessions with single label: %v", err)
		}

		// Verify the result
		if result.RequestID == "" {
			t.Error("Request ID should be present")
		}
		if len(result.SessionIds) < 3 {
			t.Errorf("Should find at least 3 sessions, found %d", len(result.SessionIds))
		}

		// Verify all returned sessions have the expected label
		sessionIDs := make(map[string]bool)
		for _, s := range testSessions {
			sessionIDs[s.SessionID] = true
		}

		foundCount := 0
		for _, sessionID := range result.SessionIds {
			if sessionIDs[sessionID] {
				foundCount++
			}
		}

		if foundCount != 3 {
			t.Errorf("Should find exactly 3 test sessions, found %d", foundCount)
		}

		t.Logf("Found %d test sessions", foundCount)
		t.Logf("Total sessions with label: %d", len(result.SessionIds))
		t.Logf("Request ID: %s", result.RequestID)
	})

	// Test 3: List sessions with multiple label filters
	t.Run("ListWithMultipleLabels", func(t *testing.T) {
		t.Log("\n=== Testing List() with multiple labels ===")

		result, err := agentBayClient.List(
			map[string]string{
				"project":     fmt.Sprintf("list-test-%s", uniqueID),
				"environment": "dev",
			},
			nil,
			nil,
		)
		if err != nil {
			t.Fatalf("Error listing sessions with multiple labels: %v", err)
		}

		// Verify the result
		if result.RequestID == "" {
			t.Error("Request ID should be present")
		}
		if len(result.SessionIds) < 1 {
			t.Errorf("Should find at least 1 session, found %d", len(result.SessionIds))
		}

		// Verify the dev session is in the results
		devSessionID := testSessions[0].SessionID
		found := false
		for _, sessionID := range result.SessionIds {
			if sessionID == devSessionID {
				found = true
				break
			}
		}

		if !found {
			t.Error("Dev session should be in the results")
		}

		t.Logf("Found dev session: %v", found)
		t.Logf("Total matching sessions: %d", len(result.SessionIds))
		t.Logf("Request ID: %s", result.RequestID)
	})

	// Test 4: List sessions with pagination parameters
	t.Run("ListWithPagination", func(t *testing.T) {
		t.Log("\n=== Testing List() with pagination ===")

		// List first page with limit of 2
		page := 1
		limit := int32(2)
		resultPage1, err := agentBayClient.List(
			map[string]string{"project": fmt.Sprintf("list-test-%s", uniqueID)},
			&page,
			&limit,
		)
		if err != nil {
			t.Fatalf("Error listing first page: %v", err)
		}

		// Verify first page
		if resultPage1.RequestID == "" {
			t.Error("Request ID should be present")
		}
		if len(resultPage1.SessionIds) > 2 {
			t.Errorf("First page should have at most 2 sessions, found %d", len(resultPage1.SessionIds))
		}

		t.Logf("Page 1 - Found %d sessions", len(resultPage1.SessionIds))
		t.Logf("Request ID: %s", resultPage1.RequestID)

		// If there are more results, test page 2
		if resultPage1.NextToken != "" {
			page2 := 2
			resultPage2, err := agentBayClient.List(
				map[string]string{"project": fmt.Sprintf("list-test-%s", uniqueID)},
				&page2,
				&limit,
			)
			if err != nil {
				t.Fatalf("Error listing second page: %v", err)
			}

			if resultPage2.RequestID == "" {
				t.Error("Request ID should be present")
			}

			t.Logf("Page 2 - Found %d sessions", len(resultPage2.SessionIds))
			t.Logf("Request ID: %s", resultPage2.RequestID)
		}
	})

	// Test 5: List sessions with non-matching labels
	t.Run("ListWithNonMatchingLabels", func(t *testing.T) {
		t.Log("\n=== Testing List() with non-matching label ===")

		result, err := agentBayClient.List(
			map[string]string{
				"project":     fmt.Sprintf("list-test-%s", uniqueID),
				"environment": "nonexistent",
			},
			nil,
			nil,
		)
		if err != nil {
			t.Fatalf("Error listing sessions with non-matching label: %v", err)
		}

		// Verify the result
		if result.RequestID == "" {
			t.Error("Request ID should be present")
		}

		// Verify our test sessions are NOT in the results
		sessionIDs := make(map[string]bool)
		for _, s := range testSessions {
			sessionIDs[s.SessionID] = true
		}

		foundCount := 0
		for _, sessionID := range result.SessionIds {
			if sessionIDs[sessionID] {
				foundCount++
			}
		}

		if foundCount != 0 {
			t.Errorf("Should not find any test sessions, found %d", foundCount)
		}

		t.Logf("Correctly found %d test sessions (expected 0)", foundCount)
		t.Logf("Request ID: %s", result.RequestID)
	})

	// Test 6: Verify default limit
	t.Run("ListWithDefaultLimit", func(t *testing.T) {
		t.Log("\n=== Testing List() with default limit ===")

		result, err := agentBayClient.List(
			map[string]string{"owner": fmt.Sprintf("test-%s", uniqueID)},
			nil,
			nil,
		)
		if err != nil {
			t.Fatalf("Error listing sessions with default limit: %v", err)
		}

		// Verify the result
		if result.RequestID == "" {
			t.Error("Request ID should be present")
		}
		if result.MaxResults != 10 {
			t.Errorf("Default limit should be 10, got %d", result.MaxResults)
		}

		t.Logf("Max results: %d", result.MaxResults)
		t.Logf("Request ID: %s", result.RequestID)
	})

	// Test 7: Verify request_id is always present
	t.Run("ListRequestIDPresence", func(t *testing.T) {
		t.Log("\n=== Testing List() request_id presence ===")

		// Test 1: No labels
		result1, err := agentBayClient.List(nil, nil, nil)
		if err != nil {
			t.Fatalf("Error in test 1: %v", err)
		}
		if result1.RequestID == "" {
			t.Error("Test 1: Request ID should not be empty")
		}
		t.Logf("Test 1 Request ID: %s", result1.RequestID)

		// Test 2: With labels
		result2, err := agentBayClient.List(
			map[string]string{"project": fmt.Sprintf("list-test-%s", uniqueID)},
			nil,
			nil,
		)
		if err != nil {
			t.Fatalf("Error in test 2: %v", err)
		}
		if result2.RequestID == "" {
			t.Error("Test 2: Request ID should not be empty")
		}
		t.Logf("Test 2 Request ID: %s", result2.RequestID)

		// Test 3: With pagination
		page := 1
		limit := int32(5)
		result3, err := agentBayClient.List(
			map[string]string{"project": fmt.Sprintf("list-test-%s", uniqueID)},
			&page,
			&limit,
		)
		if err != nil {
			t.Fatalf("Error in test 3: %v", err)
		}
		if result3.RequestID == "" {
			t.Error("Test 3: Request ID should not be empty")
		}
		t.Logf("Test 3 Request ID: %s", result3.RequestID)
	})

	// Test 8: Error scenarios (invalid page numbers and out-of-range pages)
	t.Run("ListErrorScenarios", func(t *testing.T) {
		t.Log("\n=== Testing List() error scenarios ===")

		// Test 1: page=0
		t.Log("Test 1: Testing page=0")
		page0 := 0
		limit := int32(5)
		_, err := agentBayClient.List(
			map[string]string{"project": fmt.Sprintf("list-test-%s", uniqueID)},
			&page0,
			&limit,
		)
		if err == nil {
			t.Error("page=0 should return an error")
		} else {
			t.Logf("page=0 correctly failed with error: %s", err.Error())
		}

		// Test 2: page=-1
		t.Log("Test 2: Testing page=-1")
		pageNeg := -1
		_, err = agentBayClient.List(
			map[string]string{"project": fmt.Sprintf("list-test-%s", uniqueID)},
			&pageNeg,
			&limit,
		)
		if err == nil {
			t.Error("page=-1 should return an error")
		} else {
			t.Logf("page=-1 correctly failed with error: %s", err.Error())
		}

		// Test 3: page=999999 (out of range)
		t.Log("Test 3: Testing page=999999 (out of range)")
		pageHuge := 999999
		limitSmall := int32(2)
		_, err = agentBayClient.List(
			map[string]string{"project": fmt.Sprintf("list-test-%s", uniqueID)},
			&pageHuge,
			&limitSmall,
		)
		if err == nil {
			t.Error("page=999999 should return an error (out of range)")
		} else {
			t.Logf("page=999999 correctly failed with error: %s", err.Error())
		}
	})

	// Test 9: Pagination completeness (traverse all pages until next_token is empty)
	t.Run("ListPaginationCompleteness", func(t *testing.T) {
		t.Log("\n=== Testing List() pagination completeness ===")

		allSessionIDs := make([]string, 0)
		page := 1
		limit := int32(2)
		maxIterations := 100

		for i := 0; i < maxIterations; i++ {
			result, err := agentBayClient.List(
				map[string]string{"project": fmt.Sprintf("list-test-%s", uniqueID)},
				&page,
				&limit,
			)
			if err != nil {
				t.Fatalf("Error listing page %d: %v", page, err)
			}

			allSessionIDs = append(allSessionIDs, result.SessionIds...)

			t.Logf("Page %d: Found %d sessions", page, len(result.SessionIds))

			if result.NextToken == "" {
				t.Logf("Reached end of pagination at page %d", page)
				break
			}

			page++
		}

		// Verify we found all 3 test sessions
		testSessionIDs := make(map[string]bool)
		for _, session := range testSessions {
			testSessionIDs[session.SessionID] = true
		}

		foundCount := 0
		for _, sessionID := range allSessionIDs {
			if testSessionIDs[sessionID] {
				foundCount++
			}
		}

		if foundCount != 3 {
			t.Errorf("Should find all 3 test sessions, found %d", foundCount)
		}

		// Verify no duplicates
		uniqueIDs := make(map[string]bool)
		for _, sessionID := range allSessionIDs {
			if uniqueIDs[sessionID] {
				t.Errorf("Duplicate session ID found: %s", sessionID)
			}
			uniqueIDs[sessionID] = true
		}

		t.Logf("Total sessions collected: %d", len(allSessionIDs))
		t.Logf("Unique sessions: %d", len(uniqueIDs))
		t.Logf("Test sessions found: %d/3", foundCount)
	})

	// Test 10: total_count consistency
	t.Run("ListTotalCountConsistency", func(t *testing.T) {
		t.Log("\n=== Testing List() total_count consistency ===")

		// Test 1: total_count >= test sessions
		t.Log("Test 1: Verifying total_count >= test sessions")
		limit := int32(10)
		result1, err := agentBayClient.List(
			map[string]string{"owner": fmt.Sprintf("test-%s", uniqueID)},
			nil,
			&limit,
		)
		if err != nil {
			t.Fatalf("Error listing sessions: %v", err)
		}

		if result1.TotalCount < 3 {
			t.Errorf("total_count should be at least 3, got %d", result1.TotalCount)
		}
		t.Logf("total_count: %d (expected >= 3)", result1.TotalCount)

		// Test 2: total_count consistent across calls
		t.Log("Test 2: Verifying total_count consistency across calls")
		result2, err := agentBayClient.List(
			map[string]string{"owner": fmt.Sprintf("test-%s", uniqueID)},
			nil,
			&limit,
		)
		if err != nil {
			t.Fatalf("Error listing sessions: %v", err)
		}

		if result1.TotalCount != result2.TotalCount {
			t.Errorf("total_count should be consistent: first=%d, second=%d",
				result1.TotalCount, result2.TotalCount)
		}
		t.Logf("total_count consistency verified: %d", result2.TotalCount)

		// Test 3: total_count matches collected sessions count
		t.Log("Test 3: Verifying total_count matches actual session count")
		allSessionIDs := make([]string, 0)
		page := 1
		pageLimit := int32(2)

		for {
			result, err := agentBayClient.List(
				map[string]string{"project": fmt.Sprintf("list-test-%s", uniqueID)},
				&page,
				&pageLimit,
			)
			if err != nil {
				t.Fatalf("Error listing page %d: %v", page, err)
			}

			allSessionIDs = append(allSessionIDs, result.SessionIds...)

			if result.NextToken == "" {
				// Verify total_count matches
				uniqueIDs := make(map[string]bool)
				for _, sessionID := range allSessionIDs {
					uniqueIDs[sessionID] = true
				}

				if int32(len(uniqueIDs)) != result.TotalCount {
					t.Errorf("total_count mismatch: reported=%d, actual=%d",
						result.TotalCount, len(uniqueIDs))
				}
				t.Logf("total_count matches actual count: %d", result.TotalCount)
				break
			}

			page++
		}
	})
}
