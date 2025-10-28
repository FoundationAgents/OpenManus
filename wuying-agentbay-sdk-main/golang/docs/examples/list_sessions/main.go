/*
AgentBay List Sessions Example

This example demonstrates how to use the List() API to query sessions with filtering and pagination.

Features demonstrated:
1. List all sessions
2. List sessions with label filtering
3. List sessions with pagination
4. Handle pagination to retrieve all results

Usage:

	go run main.go
*/
package main

import (
	"fmt"
	"os"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	// Get API key from environment variable
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		fmt.Println("Error: AGENTBAY_API_KEY environment variable not set")
		fmt.Println("Please set your API key: export AGENTBAY_API_KEY='your-api-key'")
		os.Exit(1)
	}

	// Initialize AgentBay client
	client, err := agentbay.NewAgentBay(apiKey, nil)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("✅ AgentBay client initialized")

	// Create some test sessions with labels for demonstration
	fmt.Println("\n📝 Creating test sessions...")
	var testSessions []*agentbay.Session

	// Create session 1 with labels
	params1 := agentbay.NewCreateSessionParams().WithLabels(map[string]string{
		"project":     "list-demo",
		"environment": "dev",
		"owner":       "demo-user",
	})
	result1, err := client.Create(params1)
	if err != nil {
		fmt.Printf("Error creating session 1: %v\n", err)
		os.Exit(1)
	}
	testSessions = append(testSessions, result1.Session)
	fmt.Printf("✅ Created session 1: %s\n", result1.Session.SessionID)
	fmt.Printf("   Request ID: %s\n", result1.RequestID)

	// Create session 2 with labels
	params2 := agentbay.NewCreateSessionParams().WithLabels(map[string]string{
		"project":     "list-demo",
		"environment": "staging",
		"owner":       "demo-user",
	})
	result2, err := client.Create(params2)
	if err != nil {
		fmt.Printf("Error creating session 2: %v\n", err)
		os.Exit(1)
	}
	testSessions = append(testSessions, result2.Session)
	fmt.Printf("✅ Created session 2: %s\n", result2.Session.SessionID)
	fmt.Printf("   Request ID: %s\n", result2.RequestID)

	// Create session 3 with labels
	params3 := agentbay.NewCreateSessionParams().WithLabels(map[string]string{
		"project":     "list-demo",
		"environment": "prod",
		"owner":       "demo-user",
	})
	result3, err := client.Create(params3)
	if err != nil {
		fmt.Printf("Error creating session 3: %v\n", err)
		os.Exit(1)
	}
	testSessions = append(testSessions, result3.Session)
	fmt.Printf("✅ Created session 3: %s\n", result3.Session.SessionID)
	fmt.Printf("   Request ID: %s\n", result3.RequestID)

	// Cleanup function
	defer func() {
		fmt.Println("\n" + "============================================================")
		fmt.Println("🧹 Cleaning up test sessions...")
		fmt.Println("============================================================")

		for _, session := range testSessions {
			deleteResult, err := client.Delete(session)
			if err != nil {
				fmt.Printf("❌ Error deleting session %s: %v\n", session.SessionID, err)
			} else if deleteResult.Success {
				fmt.Printf("✅ Deleted session: %s\n", session.SessionID)
				fmt.Printf("   Request ID: %s\n", deleteResult.RequestID)
			} else {
				fmt.Printf("❌ Failed to delete session %s\n", session.SessionID)
			}
		}

		fmt.Println("\n✨ Demo completed successfully!")
	}()

	// Example 1: List all sessions (no filter)
	fmt.Println("\n" + "============================================================")
	fmt.Println("Example 1: List all sessions (no filter)")
	fmt.Println("============================================================")

	result, err := client.List(nil, nil, nil)
	if err != nil {
		fmt.Printf("❌ Error: %v\n", err)
	} else {
		fmt.Printf("✅ Found %d total sessions\n", result.TotalCount)
		fmt.Printf("📄 Showing %d session IDs on this page\n", len(result.SessionIds))
		fmt.Printf("🔑 Request ID: %s\n", result.RequestID)
		fmt.Printf("📊 Max results per page: %d\n", result.MaxResults)

		// Display first few sessions
		for i := 0; i < 3 && i < len(result.SessionIds); i++ {
			fmt.Printf("   %d. Session ID: %s\n", i+1, result.SessionIds[i])
		}
	}

	// Example 2: List sessions with specific label
	fmt.Println("\n" + "============================================================")
	fmt.Println("Example 2: List sessions filtered by project label")
	fmt.Println("============================================================")

	result, err = client.List(map[string]string{"project": "list-demo"}, nil, nil)
	if err != nil {
		fmt.Printf("❌ Error: %v\n", err)
	} else {
		fmt.Printf("✅ Found %d sessions with project='list-demo'\n", result.TotalCount)
		fmt.Printf("📄 Showing %d session IDs on this page\n", len(result.SessionIds))
		fmt.Printf("🔑 Request ID: %s\n", result.RequestID)

		for i, sessionId := range result.SessionIds {
			fmt.Printf("   %d. Session ID: %s\n", i+1, sessionId)
		}
	}

	// Example 3: List sessions with multiple labels
	fmt.Println("\n" + "============================================================")
	fmt.Println("Example 3: List sessions filtered by multiple labels")
	fmt.Println("============================================================")

	result, err = client.List(
		map[string]string{
			"project":     "list-demo",
			"environment": "dev",
		},
		nil,
		nil,
	)
	if err != nil {
		fmt.Printf("❌ Error: %v\n", err)
	} else {
		fmt.Printf("✅ Found %d sessions with project='list-demo' AND environment='dev'\n", result.TotalCount)
		fmt.Printf("📄 Showing %d session IDs\n", len(result.SessionIds))
		fmt.Printf("🔑 Request ID: %s\n", result.RequestID)

		for i, sessionId := range result.SessionIds {
			fmt.Printf("   %d. Session ID: %s\n", i+1, sessionId)
		}
	}

	// Example 4: List sessions with pagination
	fmt.Println("\n" + "============================================================")
	fmt.Println("Example 4: List sessions with pagination (2 per page)")
	fmt.Println("============================================================")

	// Get first page
	page1 := 1
	limit := int32(2)
	resultPage1, err := client.List(
		map[string]string{"project": "list-demo"},
		&page1,
		&limit,
	)
	if err != nil {
		fmt.Printf("❌ Error: %v\n", err)
	} else {
		fmt.Printf("📄 Page 1:\n")
		fmt.Printf("   Total count: %d\n", resultPage1.TotalCount)
		fmt.Printf("   Session IDs on this page: %d\n", len(resultPage1.SessionIds))
		fmt.Printf("   Request ID: %s\n", resultPage1.RequestID)

		for i, sessionId := range resultPage1.SessionIds {
			fmt.Printf("   %d. Session ID: %s\n", i+1, sessionId)
		}

		// Get second page if available
		if resultPage1.NextToken != "" {
			fmt.Printf("\n   Has next page (token: %.20s...)\n", resultPage1.NextToken)

			page2 := 2
			resultPage2, err := client.List(
				map[string]string{"project": "list-demo"},
				&page2,
				&limit,
			)
			if err != nil {
				fmt.Printf("❌ Error on page 2: %v\n", err)
			} else {
				fmt.Printf("\n📄 Page 2:\n")
				fmt.Printf("   Session IDs on this page: %d\n", len(resultPage2.SessionIds))
				fmt.Printf("   Request ID: %s\n", resultPage2.RequestID)

				for i, sessionId := range resultPage2.SessionIds {
					fmt.Printf("   %d. Session ID: %s\n", i+1, sessionId)
				}
			}
		}
	}

	// Example 5: Retrieve all session IDs across multiple pages
	fmt.Println("\n" + "============================================================")
	fmt.Println("Example 5: Retrieve all session IDs with pagination loop")
	fmt.Println("============================================================")

	var allSessionIds []string
	page := 1
	pageLimit := int32(2)

	for {
		result, err := client.List(
			map[string]string{"owner": "demo-user"},
			&page,
			&pageLimit,
		)

		if err != nil {
			fmt.Printf("❌ Error on page %d: %v\n", page, err)
			break
		}

		fmt.Printf("📄 Page %d: Found %d session IDs\n", page, len(result.SessionIds))
		allSessionIds = append(allSessionIds, result.SessionIds...)

		// Break if no more pages
		if result.NextToken == "" {
			break
		}

		page++
	}

	fmt.Printf("\n✅ Retrieved %d total session IDs across %d pages\n", len(allSessionIds), page)
	for i, sessionId := range allSessionIds {
		fmt.Printf("   %d. Session ID: %s\n", i+1, sessionId)
	}
}
