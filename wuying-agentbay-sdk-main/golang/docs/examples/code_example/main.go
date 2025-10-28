package main

import (
	"fmt"
	"log"
	"os"

	agentbay "github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		apiKey = "akm-xxx" // Replace with your actual API key for testing
		fmt.Println("Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for production use.")
	}
	// Initialize AgentBay with API key from environment
	ab, err := agentbay.NewAgentBay(apiKey)

	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Create a session
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("code_latest")

	sessionResult, err := ab.Create(sessionParams)
	if err != nil {
		log.Fatalf("Failed to create session: %v", err)
	}

	session := sessionResult.Session
	fmt.Printf("Session created with ID: %s\n", session.SessionID)
	fmt.Printf("Request ID: %s\n", sessionResult.RequestID)

	// Demonstrate code execution using the new Code module
	pythonCode := `
print("Hello from Python!")
result = 2 + 3
print(f"2 + 3 = {result}")
`

	fmt.Println("\n=== Running Python Code ===")
	codeResult, err := session.Code.RunCode(pythonCode, "python", 1000)
	if err != nil {
		log.Printf("Failed to run Python code: %v", err)
	} else {
		fmt.Printf("Python code executed successfully!\n")
		fmt.Printf("Request ID: %s\n", codeResult.RequestID)
		fmt.Printf("Output:\n%s\n", codeResult.Output)
	}

	// Demonstrate JavaScript code execution
	jsCode := `
console.log("Hello from JavaScript!");
const result = 2 + 3;
console.log("2 + 3 =", result);
`

	fmt.Println("\n=== Running JavaScript Code ===")
	jsResult, err := session.Code.RunCode(jsCode, "javascript", 30)
	if err != nil {
		log.Printf("Failed to run JavaScript code: %v", err)
	} else {
		fmt.Printf("JavaScript code executed successfully!\n")
		fmt.Printf("Request ID: %s\n", jsResult.RequestID)
		fmt.Printf("Output:\n%s\n", jsResult.Output)
	}

	// Demonstrate command execution (should still work)
	fmt.Println("\n=== Running Shell Command ===")
	cmdResult, err := session.Command.ExecuteCommand("echo 'Hello from shell!'", 5000)
	if err != nil {
		log.Printf("Failed to execute command: %v", err)
	} else {
		fmt.Printf("Command executed successfully!\n")
		fmt.Printf("Request ID: %s\n", cmdResult.RequestID)
		fmt.Printf("Output:\n%s\n", cmdResult.Output)
	}

	// Clean up: delete the session
	fmt.Println("\n=== Cleaning up ===")
	deleteResult, err := session.Delete()
	if err != nil {
		log.Printf("Failed to delete session: %v", err)
	} else if deleteResult.Success {
		fmt.Printf("Session deleted successfully! Request ID: %s\n", deleteResult.RequestID)
	} else {
		fmt.Printf("Failed to delete session. Request ID: %s\n", deleteResult.RequestID)
	}
}
