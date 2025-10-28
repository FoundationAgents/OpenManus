package main

import (
	"fmt"
	"os"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

// Basic example of using the Agent module to execute tasks.
// This example demonstrates:
// - Creating a session with Agent capabilities
// - Executing a simple task using natural language
// - Handling task results

func main() {
	// Get API key from environment variable
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		fmt.Println("Error: AGENTBAY_API_KEY environment variable not set")
		return
	}

	// Initialize AgentBay client
	fmt.Println("Initializing AgentBay client...")
	client, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		return
	}

	// Create a session
	fmt.Println("Creating a new session...")
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("windows_latest")
	sessionResult, err := client.Create(sessionParams)
	if err != nil {
		fmt.Printf("Error creating session: %v\n", err)
		return
	}

	session := sessionResult.Session
	fmt.Printf("Session created with ID: %s\n", session.SessionID)

	// Execute a task using the Agent
	taskDescription := "Calculate the square root of 144"
	fmt.Printf("Executing task: %s\n", taskDescription)

	executionResult := session.Agent.ExecuteTask(taskDescription, 5)

	if executionResult.Success {
		fmt.Println("Task completed successfully!")
		fmt.Printf("Task ID: %s\n", executionResult.TaskID)
		fmt.Printf("Task status: %s\n", executionResult.TaskStatus)
	} else {
		fmt.Printf("Task failed: %s\n", executionResult.ErrorMessage)
		if executionResult.TaskID != "" {
			fmt.Printf("Task ID: %s\n", executionResult.TaskID)
		}
	}

	// Clean up - delete the session
	deleteResult, err := client.Delete(session)
	if err != nil {
		fmt.Printf("Error deleting session: %v\n", err)
		return
	}

	if deleteResult.Success {
		fmt.Println("Session deleted successfully")
	} else {
		fmt.Printf("Failed to delete session: %s\n", deleteResult.RequestID)
	}
}
