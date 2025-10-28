package main

import (
	"fmt"
	"log"
	"os"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	// Get API key from environment variable
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		log.Fatal("AGENTBAY_API_KEY environment variable is not set")
	}

	// Initialize AgentBay client
	client, err := agentbay.NewAgentBay(apiKey, nil)
	if err != nil {
		log.Fatalf("Failed to initialize AgentBay client: %v", err)
	}

	// For demonstration, first create a session
	fmt.Println("Creating a session...")
	createResult, err := client.Create(nil)
	if err != nil {
		log.Fatalf("Failed to create session: %v", err)
	}
	sessionId := createResult.Session.SessionID
	fmt.Printf("Created session with ID: %s\n", sessionId)

	// Retrieve the session by ID using Get API
	fmt.Println("\nRetrieving session using Get API...")
	getResult, err := client.Get(sessionId)
	if err != nil {
		log.Fatalf("Failed to get session: %v", err)
	}

	if !getResult.Success || getResult.Session == nil {
		log.Fatalf("Failed to get session: %s", getResult.ErrorMessage)
	}

	session := getResult.Session

	// Display session information
	fmt.Printf("Successfully retrieved session:\n")
	fmt.Printf("  Session ID: %s\n", session.SessionID)
	fmt.Printf("  Request ID: %s\n", getResult.RequestID)

	// The session object can be used for further operations
	// For example, you can execute commands, work with files, etc.
	fmt.Println("\nSession is ready for use")

	// Clean up: Delete the session when done
	fmt.Println("\nCleaning up...")
	deleteResult, err := session.Delete()
	if err != nil {
		log.Fatalf("Failed to delete session: %v", err)
	}

	if deleteResult.Success {
		fmt.Printf("Session %s deleted successfully\n", sessionId)
	} else {
		fmt.Printf("Failed to delete session %s\n", sessionId)
	}
}
