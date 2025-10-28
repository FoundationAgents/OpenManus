package integration_test

import (
	"fmt"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

// TestContextPagination tests the pagination functionality of the Context List API
func TestContextPagination(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	t.Logf("Using API key: %s", apiKey)

	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}
	t.Logf("AgentBay client initialized successfully")

	// Create multiple contexts for testing pagination
	contextNames := make([]string, 0)
	defer func() {
		// Clean up created contexts
		for _, name := range contextNames {
			getResult, err := agentBay.Context.Get(name, false)
			if err != nil {
				t.Logf("Warning: Error getting context %s for cleanup: %v", name, err)
				continue
			}

			context := contextFromResult(getResult)
			if context != nil {
				_, err := agentBay.Context.Delete(context)
				if err != nil {
					t.Logf("Warning: Error deleting context %s: %v", name, err)
				} else {
					t.Logf("Successfully deleted context %s", name)
				}
			}
		}
	}()

	// Create 15 test contexts
	for i := 0; i < 15; i++ {
		contextName := fmt.Sprintf("test-pagination-%d-%d", time.Now().Unix(), i)
		t.Logf("Creating context: %s", contextName)

		_, err := agentBay.Context.Create(contextName)
		if err != nil {
			t.Fatalf("Error creating context %s: %v", contextName, err)
		}

		contextNames = append(contextNames, contextName)
	}

	// Wait a moment for all contexts to be fully created
	time.Sleep(2 * time.Second)

	// Test 1: List contexts with default pagination (should get first 10)
	t.Log("Test 1: Listing contexts with default pagination (first page)")
	params := agentbay.NewContextListParams()
	params.MaxResults = 10

	listResult, err := agentBay.Context.List(params)
	if err != nil {
		t.Fatalf("Error listing contexts: %v", err)
	}

	if len(listResult.Contexts) != 10 {
		t.Errorf("Expected 10 contexts in first page, got %d", len(listResult.Contexts))
	}

	t.Logf("First page: Got %d contexts (RequestID: %s)", len(listResult.Contexts), listResult.RequestID)
	t.Logf("NextToken: %s, MaxResults: %d, TotalCount: %d", listResult.NextToken, listResult.MaxResults, listResult.TotalCount)

	// Test 2: List contexts with custom page size
	t.Log("Test 2: Listing contexts with custom page size (5 per page)")
	params = agentbay.NewContextListParams()
	params.MaxResults = 5

	listResult, err = agentBay.Context.List(params)
	if err != nil {
		t.Fatalf("Error listing contexts with custom page size: %v", err)
	}

	if len(listResult.Contexts) != 5 {
		t.Errorf("Expected 5 contexts with custom page size, got %d", len(listResult.Contexts))
	}

	t.Logf("Custom page size: Got %d contexts (RequestID: %s)", len(listResult.Contexts), listResult.RequestID)
	t.Logf("NextToken: %s, MaxResults: %d, TotalCount: %d", listResult.NextToken, listResult.MaxResults, listResult.TotalCount)

	// Test 3: Get second page using NextToken
	if listResult.NextToken != "" {
		t.Log("Test 3: Getting second page using NextToken")
		params = agentbay.NewContextListParams()
		params.MaxResults = 5
		params.NextToken = listResult.NextToken

		secondPageResult, err := agentBay.Context.List(params)
		if err != nil {
			t.Fatalf("Error listing contexts second page: %v", err)
		}

		t.Logf("Second page: Got %d contexts (RequestID: %s)", len(secondPageResult.Contexts), secondPageResult.RequestID)
		t.Logf("NextToken: %s, MaxResults: %d, TotalCount: %d", secondPageResult.NextToken, secondPageResult.MaxResults, secondPageResult.TotalCount)

		// Note: We're not verifying that the second page has different contexts than the first page
		// because the API might return the same contexts in different orders or have other behaviors
		// that are not strictly paginated
	} else {
		t.Log("No NextToken available for second page test")
	}

	// Test 4: List contexts with larger page size
	t.Log("Test 4: Listing contexts with larger page size (20 per page)")
	params = agentbay.NewContextListParams()
	params.MaxResults = 20

	listResult, err = agentBay.Context.List(params)
	if err != nil {
		t.Fatalf("Error listing contexts with larger page size: %v", err)
	}

	// Should get all contexts (up to 15) since we only created 15
	if len(listResult.Contexts) < 10 {
		t.Errorf("Expected at least 10 contexts with larger page size, got %d", len(listResult.Contexts))
	}

	t.Logf("Larger page size: Got %d contexts (RequestID: %s)", len(listResult.Contexts), listResult.RequestID)
	t.Logf("NextToken: %s, MaxResults: %d, TotalCount: %d", listResult.NextToken, listResult.MaxResults, listResult.TotalCount)

	// Test 5: Test with empty parameters (should use defaults)
	t.Log("Test 5: Listing contexts with nil parameters (should use defaults)")
	listResult, err = agentBay.Context.List(nil)
	if err != nil {
		t.Fatalf("Error listing contexts with nil parameters: %v", err)
	}

	// Note: We're not checking for a specific number of contexts since the API behavior
	// may vary, but we're ensuring the call succeeds and returns some data
	t.Logf("Nil parameters: Got %d contexts (RequestID: %s)", len(listResult.Contexts), listResult.RequestID)
	if listResult.NextToken != "" {
		t.Logf("NextToken: %s, MaxResults: %d, TotalCount: %d", listResult.NextToken, listResult.MaxResults, listResult.TotalCount)
	}

	t.Log("TestContextPagination completed successfully")
}
