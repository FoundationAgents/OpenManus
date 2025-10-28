package main

import (
	"fmt"
	"os"
	"strings"

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

	// Create session parameters with ImageId set to code_latest to support code execution
	params := agentbay.NewCreateSessionParams().WithImageId("code_latest")

	// Create a new session
	fmt.Println("\nCreating a new session with code_latest image...")
	sessionResult, err := agentBay.Create(params)
	if err != nil {
		fmt.Printf("\nError creating session: %v\n", err)
		os.Exit(1)
	}
	session := sessionResult.Session
	fmt.Printf("\nSession created with ID: %s\n", session.SessionID)
	defer func() {
		// Clean up by deleting the session when we're done
		fmt.Println("\nDeleting the session...")
		deleteResult, err := session.Delete()
		if err != nil {
			fmt.Printf("Error deleting session: %v\n", err)
		} else {
			fmt.Printf("Session deleted successfully (RequestID: %s)\n", deleteResult.RequestID)
		}
	}()

	// 1. Execute simple shell command
	fmt.Println("\n1. Executing simple shell command (echo)...")
	echoCommand := "echo 'Hello from AgentBay SDK!'"
	result, err := session.Command.ExecuteCommand(echoCommand)
	if err != nil {
		fmt.Printf("Error executing echo command: %v\n", err)
	} else {
		fmt.Printf("Echo command output:\n%s\n", result.Output)
		fmt.Printf("Command executed successfully (RequestID: %s)\n", result.RequestID)
	}

	// 2. Execute command with longer timeout
	fmt.Println("\n2. Executing command with custom timeout...")
	lsCommand := "ls -la /etc"
	timeoutMs := 5000 // 5 seconds timeout
	result, err = session.Command.ExecuteCommand(lsCommand, timeoutMs)
	if err != nil {
		fmt.Printf("Error executing ls command: %v\n", err)
	} else {
		fmt.Printf("Directory listing (first few lines):\n%s\n", truncateOutput(result.Output, 5))
		fmt.Printf("Command executed successfully (RequestID: %s)\n", result.RequestID)
	}

	// 3. Execute Python code
	fmt.Println("\n3. Running Python code...")
	pythonCode := `
import platform
import sys

print(f"Python version: {platform.python_version()}")
print(f"System info: {platform.system()} {platform.release()}")
print("Working with numbers in Python:")
for i in range(1, 6):
    print(f"{i} squared is {i*i}")
`
	codeResult, err := session.Code.RunCode(pythonCode, "python")
	if err != nil {
		fmt.Printf("Error running Python code: %v\n", err)
	} else {
		fmt.Printf("Python code output:\n%s\n", codeResult.Output)
		fmt.Printf("Python code executed successfully (RequestID: %s)\n", codeResult.RequestID)
	}

	// 4. Execute JavaScript code with custom timeout
	fmt.Println("\n4. Running JavaScript code with custom timeout...")
	jsCode := `
console.log("JavaScript execution in AgentBay");
console.log("Basic operations:");

// Simple array operations
const numbers = [1, 2, 3, 4, 5];
console.log("Original array:", numbers);

const doubled = numbers.map(n => n * 2);
console.log("Doubled values:", doubled);

const sum = numbers.reduce((total, n) => total + n, 0);
console.log("Sum of array:", sum);
`
	timeoutS := 10 // 10 seconds timeout
	codeResult, err = session.Code.RunCode(jsCode, "javascript", timeoutS)
	if err != nil {
		fmt.Printf("Error running JavaScript code: %v\n", err)
	} else {
		fmt.Printf("JavaScript code output:\n%s\n", codeResult.Output)
		fmt.Printf("JavaScript code executed successfully (RequestID: %s)\n", codeResult.RequestID)
	}

	// 5. Execute a more complex shell command sequence
	fmt.Println("\n5. Executing a sequence of shell commands...")
	complexCommand := `
echo "Current working directory:"
pwd
echo "\nSystem information:"
uname -a
echo "\nMemory usage:"
free -h 2>/dev/null || vm_stat 2>/dev/null || echo "Memory info not available"
echo "\nDisk usage:"
df -h | head -5
`
	result, err = session.Command.ExecuteCommand(complexCommand)
	if err != nil {
		fmt.Printf("Error executing complex command: %v\n", err)
	} else {
		fmt.Printf("Complex command output:\n%s\n", truncateOutput(result.Output, 15))
		fmt.Printf("Complex command executed successfully (RequestID: %s)\n", result.RequestID)
	}

	fmt.Println("\nCommand examples completed successfully!")
}

// Helper function to truncate long output text
func truncateOutput(output string, maxLines int) string {
	lines := strings.Split(output, "\n")
	if len(lines) <= maxLines {
		return output
	}

	truncated := lines[:maxLines]
	return strings.Join(truncated, "\n") + "\n... (output truncated)"
}
