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
	ab, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	var session *agentbay.Session
	var linuxSession *agentbay.Session

	// Create a new session with default parameters
	fmt.Println("\nCreating a new session...")
	params := agentbay.NewCreateSessionParams().WithImageId("browser_latest")
	result, err := ab.Create(params)
	if err != nil {
		fmt.Printf("\nError creating session: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("\nSession created with ID: %s (RequestID: %s)\n",
		result.Session.SessionID, result.RequestID)

	// Store session for convenience
	session = result.Session

	// Execute command
	fmt.Println("\nExecute command...")
	cmdResult, err := session.Command.ExecuteCommand("ls")
	if err != nil {
		fmt.Printf("Error execute command: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Execute command result: %s (RequestID: %s)\n",
		cmdResult.Output, cmdResult.RequestID)

	// Create a directory to demonstrate filesystem operations
	fmt.Println("\nCreating a directory...")
	dirResult, err := session.FileSystem.CreateDirectory("/tmp/test_dir")
	if err != nil {
		fmt.Printf("Error creating directory: %v\n", err)
	} else {
		fmt.Printf("Directory created successfully (RequestID: %s)\n",
			dirResult.RequestID)
	}

	// Write a file
	fmt.Println("\nWriting a file...")
	writeResult, err := session.FileSystem.WriteFile("/tmp/test_file.txt", "Hello AgentBay SDK!", "overwrite")
	if err != nil {
		fmt.Printf("Error writing file: %v\n", err)
	} else {
		fmt.Printf("File written successfully (RequestID: %s)\n",
			writeResult.RequestID)
	}

	// Read a file
	fmt.Println("\nReading a file...")
	fileResult, err := session.FileSystem.ReadFile("/etc/hosts")
	if err != nil {
		fmt.Printf("Error reading file: %v\n", err)
	} else {
		fmt.Printf("File content: %s (RequestID: %s)\n",
			fileResult.Content, fileResult.RequestID)
	}

	// Get session link (no parameters)
	fmt.Println("\nGetting session link...")
	linkResult, err := session.GetLink(nil, nil)
	if err != nil {
		fmt.Printf("Error getting session link: %v\n", err)
	} else {
		fmt.Printf("Session link: %s (RequestID: %s)\n",
			linkResult.Link, linkResult.RequestID)
	}

	// Test GetLink with valid port in range [30100, 30199]
	fmt.Println("\nTesting GetLink with valid port 30150...")
	var validPort int32 = 30150
	linkResultValidPort, err := session.GetLink(nil, &validPort)
	if err != nil {
		fmt.Printf("Error getting link with valid port 30150: %v\n", err)
	} else {
		fmt.Printf("Link with valid port 30150: %s (RequestID: %s)\n",
			linkResultValidPort.Link, linkResultValidPort.RequestID)
	}

	// Test GetLink with invalid port (for demonstration)
	fmt.Println("\nTesting GetLink with invalid port 8080 (should fail)...")
	var invalidPort int32 = 8080
	linkResultInvalidPort, err := session.GetLink(nil, &invalidPort)
	if err != nil {
		fmt.Printf("Expected error with invalid port 8080: %v\n", err)
	} else {
		fmt.Printf("Unexpected success with invalid port: %s (RequestID: %s)\n",
			linkResultInvalidPort.Link, linkResultInvalidPort.RequestID)
	}

	// Create a new Linux session for testing GetLink with parameters
	fmt.Println("\n=== Testing Linux Session with GetLink parameters ===")
	linuxParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	fmt.Println("Creating a linux_latest session...")
	linuxResult, err := ab.Create(linuxParams)
	if err != nil {
		fmt.Printf("Error creating Linux session: %v\n", err)
	} else {
		fmt.Printf("Linux session created with ID: %s (RequestID: %s)\n",
			linuxResult.Session.SessionID, linuxResult.RequestID)

		// Store Linux session for convenience
		linuxSession = linuxResult.Session

		// Test GetLink with valid parameters (protocol_type="https", port=30199)
		fmt.Println("\nTesting GetLink with valid parameters (https, 30199)...")
		httpsProtocol := "https"
		var validHttpsPort int32 = 30199
		linkResultWithValidParams, err := linuxSession.GetLink(&httpsProtocol, &validHttpsPort)
		if err != nil {
			fmt.Printf("Error getting link with valid params: %v\n", err)
		} else {
			fmt.Printf("Link with valid params: %s (RequestID: %s)\n",
				linkResultWithValidParams.Link, linkResultWithValidParams.RequestID)
		}

		// Test GetLink with invalid parameters (for demonstration)
		fmt.Println("\nTesting GetLink with invalid parameters (https, 443) - should fail...")
		var invalidHttpsPort int32 = 443
		linkResultWithInvalidParams, err := linuxSession.GetLink(&httpsProtocol, &invalidHttpsPort)
		if err != nil {
			fmt.Printf("Expected error with invalid port 443: %v\n", err)
		} else {
			fmt.Printf("Unexpected success with invalid port: %s (RequestID: %s)\n",
				linkResultWithInvalidParams.Link, linkResultWithInvalidParams.RequestID)
		}
	}

	// Get context information
	fmt.Println("\nGetting context information...")

	contextResult, err := ab.Context.List(agentbay.NewContextListParams())
	if err != nil {
		fmt.Printf("Error listing contexts: %v\n", err)
	} else {
		fmt.Printf("Found %d contexts (RequestID: %s)\n",
			len(contextResult.Contexts), contextResult.RequestID)
	}

	// Delete the browser session
	fmt.Println("\nDeleting the browser session...")
	deleteResult, err := ab.Delete(session)
	if err != nil {
		fmt.Printf("Error deleting browser session: %v\n", err)
	} else {
		fmt.Printf("Browser session deleted successfully (RequestID: %s)\n",
			deleteResult.RequestID)
	}

	// Delete the Linux session if it was created
	if linuxSession != nil {
		fmt.Println("\nDeleting the Linux session...")
		linuxDeleteResult, err := ab.Delete(linuxSession)
		if err != nil {
			fmt.Printf("Error deleting Linux session: %v\n", err)
		} else {
			fmt.Printf("Linux session deleted successfully (RequestID: %s)\n",
				linuxDeleteResult.RequestID)
		}
	}
}
