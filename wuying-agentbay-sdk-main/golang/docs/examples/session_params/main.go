package main

import (
	"fmt"
	"os"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	// Get API key from environment variable or use a default value for testing
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		apiKey = "akm-xxx" // Replace with your actual API key for testing
		fmt.Println("Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for production use.")
	}

	// Initialize the AgentBay client
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Example 1: Create a session with custom labels
	fmt.Println("\nExample 1: Creating a session with custom labels...")

	// Create parameters with labels
	params := agentbay.NewCreateSessionParams().
		WithLabels(map[string]string{
			"username": "alice",
			"project":  "my-project",
		})

	sessionResult, err := agentBay.Create(params)
	if err != nil {
		fmt.Printf("\nError creating session: %v\n", err)
		os.Exit(1)
	}
	session := sessionResult.Session
	fmt.Printf("\nSession created with ID: %s and labels: username=alice, project=my-project (RequestID: %s)\n", session.SessionID, sessionResult.RequestID)

	// Example 2: List sessions by labels
	fmt.Println("\nExample 2: Listing sessions by labels...")

	// Query sessions with the "project" label set to "my-project"
	listParams := agentbay.NewListSessionParams()
	listParams.Labels = map[string]string{
		"project": "my-project",
	}
	// Set page size to 5 sessions per page
	listParams.MaxResults = 5

	limit := int32(5)
	sessionsByLabelResult, err := agentBay.List(listParams.Labels, nil, &limit)
	if err != nil {
		fmt.Printf("\nError listing sessions by labels: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("\nFound %d sessions with project=my-project (total: %d, page size: %d, RequestID: %s):\n",
		len(sessionsByLabelResult.SessionIds),
		sessionsByLabelResult.TotalCount,
		sessionsByLabelResult.MaxResults,
		sessionsByLabelResult.RequestID)

	for i, sessionId := range sessionsByLabelResult.SessionIds {
		fmt.Printf("  %d. Session ID: %s\n", i+1, sessionId)
	}

	// Example 3: Pagination with NextToken
	fmt.Println("\nExample 3: Demonstrating pagination...")

	// If there are more pages available
	if sessionsByLabelResult.NextToken != "" {
		fmt.Printf("\nMore sessions available. Fetching next page using NextToken: %s\n", sessionsByLabelResult.NextToken)

		// Create new params for the next page
		nextPageParams := agentbay.NewListSessionParams()
		nextPageParams.Labels = map[string]string{
			"project": "my-project",
		}
		nextPageParams.MaxResults = 5
		nextPageParams.NextToken = sessionsByLabelResult.NextToken

		page := 2
		nextPageResult, err := agentBay.List(nextPageParams.Labels, &page, &limit)
		if err != nil {
			fmt.Printf("\nError listing next page of sessions: %v\n", err)
		} else {
			fmt.Printf("\nNext page found %d more sessions (RequestID: %s):\n",
				len(nextPageResult.SessionIds), nextPageResult.RequestID)

			for i, sessionId := range nextPageResult.SessionIds {
				fmt.Printf("  %d. Session ID: %s\n", i+1, sessionId)
			}
		}
	} else {
		fmt.Println("\nNo more pages available.")
	}

	// Clean up
	fmt.Println("\nCleaning up sessions...")

	deleteResult, err := session.Delete()
	if err != nil {
		fmt.Printf("Error deleting session: %v\n", err)
	} else {
		fmt.Printf("Session deleted successfully (RequestID: %s)\n", deleteResult.RequestID)
	}
}
