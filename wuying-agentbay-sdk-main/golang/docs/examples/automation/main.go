package main

import (
	"fmt"
	"log"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

// AgentBay SDK - Automation Features Example (Golang)
//
// This example demonstrates how to use AgentBay SDK automation features, including:
// - Command execution
// - Code execution

func main() {
	fmt.Println("🚀 AgentBay Automation Features Example (Golang)")

	// Initialize AgentBay client
	client, err := agentbay.NewAgentBay("", nil)
	if err != nil {
		log.Fatalf("❌ Client initialization failed: %v", err)
	}

	// Create session
	fmt.Println("\n📱 Creating session...")
	sessionResult, err := client.Create(agentbay.NewCreateSessionParams().WithImageId("code_latest"))
	if err != nil {
		fmt.Printf("❌ Session creation failed: %v\n", err)
		return
	}

	session := sessionResult.Session
	fmt.Printf("✅ Session created successfully: %s\n", session.SessionID)

	defer func() {
		// Clean up session
		fmt.Printf("\n🧹 Cleaning up session: %s\n", session.SessionID)
		client.Delete(session)
		fmt.Println("✅ Example execution completed")
	}()

	// 1. Command execution example
	commandExecutionExample(session)

	// 2. Code execution example
	codeExecutionExample(session)
}

func commandExecutionExample(session *agentbay.Session) {
	fmt.Println("\n💻 === Command Execution Example ===")

	// Basic command execution
	commands := []string{
		"whoami",
		"pwd",
		"ls -la /tmp",
		"echo 'Hello AgentBay!'",
	}

	for _, cmd := range commands {
		fmt.Printf("\n🔄 Executing command: %s\n", cmd)
		result, err := session.Command.ExecuteCommand(cmd)

		if err == nil {
			fmt.Printf("✅ Output: %s\n", result.Output)
		} else {
			fmt.Printf("❌ Command failed: %v\n", err)
		}
	}

	// Command execution with timeout
	fmt.Println("\n🔄 Executing command with timeout...")
	timeoutResult, err := session.Command.ExecuteCommand("sleep 2", 5000) // 5 second timeout, in milliseconds
	if err == nil {
		fmt.Println("✅ Timeout command execution successful")
		fmt.Printf("Output: %s\n", timeoutResult.Output)
	} else {
		fmt.Printf("❌ Timeout command failed: %v\n", err)
	}
}

func codeExecutionExample(session *agentbay.Session) {
	fmt.Println("\n🐍 === Code Execution Example ===")

	// Python code execution
	pythonCode := `
import sys
import os
import json
from datetime import datetime

# System information
system_info = {
    "python_version": sys.version,
    "current_directory": os.getcwd(),
    "timestamp": datetime.now().isoformat(),
    "environment_vars": len(os.environ)
}

print("Python code execution successful!")
print(f"System info: {json.dumps(system_info, indent=2)}")

# Simple calculation
numbers = list(range(1, 11))
total = sum(numbers)
print(f"Sum of 1 to 10: {total}")
`

	fmt.Println("🔄 Executing Python code...")
	pythonResult, err := session.Code.RunCode(pythonCode, "python")
	if err == nil {
		fmt.Println("✅ Python code execution successful:")
		fmt.Println(pythonResult.Output)
	} else {
		fmt.Printf("❌ Python code execution failed: %v\n", err)
	}

	// JavaScript code execution
	jsCode := `
console.log("JavaScript code execution successful!");

// Get system information
const os = require('os');
const systemInfo = {
    platform: os.platform(),
    arch: os.arch(),
    nodeVersion: process.version,
    memory: Math.round(os.totalmem() / 1024 / 1024) + ' MB'
};

console.log("System info:", JSON.stringify(systemInfo, null, 2));

// Array operations
const numbers = [1, 2, 3, 4, 5];
const doubled = numbers.map(n => n * 2);
console.log("Original array:", numbers);
console.log("After doubling:", doubled);
`

	fmt.Println("\n🔄 Executing JavaScript code...")
	jsResult, err := session.Code.RunCode(jsCode, "javascript")
	if err == nil {
		fmt.Println("✅ JavaScript code execution successful:")
		fmt.Println(jsResult.Output)
	} else {
		fmt.Printf("❌ JavaScript code execution failed: %v\n", err)
	}
}
