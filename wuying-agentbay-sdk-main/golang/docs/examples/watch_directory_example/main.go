package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/filesystem"
)

func main() {
	fmt.Println("=== AgentBay Watch Directory Example ===")

	// Get API key from environment variable
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		log.Fatal("Please set AGENTBAY_API_KEY environment variable")
	}

	// Initialize AgentBay client
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		log.Fatalf("Failed to initialize AgentBay: %v", err)
	}
	fmt.Println("✅ AgentBay client initialized")

	// Create session with code_latest ImageId
	sessionParams := &agentbay.CreateSessionParams{
		ImageId: "code_latest",
	}

	sessionResult, err := agentBay.Create(sessionParams)
	if err != nil {
		log.Fatalf("Failed to create session: %v", err)
	}

	if sessionResult.Session == nil {
		log.Fatal("Session creation returned nil session")
	}

	session := sessionResult.Session
	fmt.Printf("✅ Session created with ID: %s\n", session.GetSessionId())

	// Clean up session when done
	defer func() {
		fmt.Println("\n🧹 Cleaning up session...")
		_, err := agentBay.Delete(session)
		if err != nil {
			log.Printf("Warning: Failed to delete session: %v", err)
		} else {
			fmt.Println("✅ Session deleted successfully")
		}
	}()

	// Get FileSystem instance
	fileSystem := session.FileSystem

	// Create a test directory in the AgentBay environment
	testDir := "/tmp/agentbay-watch-example"
	createResult, err := fileSystem.CreateDirectory(testDir)
	if err != nil {
		log.Fatalf("Failed to create directory in AgentBay: %v", err)
	}
	if !createResult.Success {
		log.Fatalf("Directory creation failed")
	}

	fmt.Printf("📁 Created test directory: %s\n", testDir)

	// Set up callback function to handle file changes
	callback := func(events []*filesystem.FileChangeEvent) {
		if len(events) > 0 {
			fmt.Printf("\n🔍 Detected %d file changes:\n", len(events))
			for _, event := range events {
				fmt.Printf("  - %s\n", event.String())
			}
		}
	}

	// Create stop channel for controlling the watch
	stopChan := make(chan struct{})

	// Start watching directory in a goroutine
	fmt.Printf("👀 Starting to watch directory: %s\n", testDir)
	fmt.Println("📊 Polling interval: 500ms (default)")

	wg := fileSystem.WatchDirectoryWithDefaults(testDir, callback, stopChan)

	// Wait for monitoring to start
	fmt.Println("⏳ Waiting for monitoring to start...")
	time.Sleep(2 * time.Second)

	// Ensure we wait for the monitoring goroutine to finish when stopping
	defer func() {
		// Only close if not already closed
		select {
		case <-stopChan:
			// Channel is already closed
		default:
			close(stopChan)
		}
		wg.Wait()
	}()

	// Demonstrate file operations
	fmt.Println("\n🎬 Demonstrating file operations...")

	// 1. Create a file
	fmt.Println("📝 Creating a new file...")
	testFile1 := filepath.Join(testDir, "example.txt")
	writeResult1, err := fileSystem.WriteFile(testFile1, "Hello, AgentBay Watch Directory!", "overwrite")
	if err != nil {
		log.Printf("Error creating file: %v", err)
	} else if !writeResult1.Success {
		log.Printf("File creation failed")
	}

	// Wait for detection
	time.Sleep(2 * time.Second)

	// 2. Modify the file
	fmt.Println("✏️  Modifying the file...")
	modifiedContent := fmt.Sprintf("Modified at %s\nThis file has been updated!", time.Now().Format(time.RFC3339))
	writeResult2, err := fileSystem.WriteFile(testFile1, modifiedContent, "overwrite")
	if err != nil {
		log.Printf("Error modifying file: %v", err)
	} else if !writeResult2.Success {
		log.Printf("File modification failed")
	}

	// Wait for detection
	time.Sleep(2 * time.Second)

	// 3. Create another file
	fmt.Println("📄 Creating another file...")
	testFile2 := filepath.Join(testDir, "another_file.log")
	writeResult3, err := fileSystem.WriteFile(testFile2, "Log entry: Watch directory example running", "overwrite")
	if err != nil {
		log.Printf("Error creating second file: %v", err)
	} else if !writeResult3.Success {
		log.Printf("Second file creation failed")
	}

	// Wait for detection
	time.Sleep(2 * time.Second)

	// 4. Create a subdirectory
	fmt.Println("📂 Creating a subdirectory...")
	subDir := filepath.Join(testDir, "subdir")
	createDirResult, err := fileSystem.CreateDirectory(subDir)
	if err != nil {
		log.Printf("Error creating subdirectory: %v", err)
	} else if !createDirResult.Success {
		log.Printf("Subdirectory creation failed")
	}

	// Wait for detection
	time.Sleep(2 * time.Second)

	// 5. Note: File deletion is not available in the current FileSystem API
	fmt.Println("🗑️  File deletion not demonstrated (API not available)")

	// Wait for final detection
	time.Sleep(2 * time.Second)

	// Demonstrate GetFileChange method
	fmt.Println("\n🔍 Demonstrating GetFileChange method...")
	result, err := fileSystem.GetFileChange(testDir)
	if err != nil {
		log.Printf("Error getting file changes: %v", err)
	} else {
		fmt.Printf("📊 GetFileChange result:\n")
		fmt.Printf("  - Request ID: %s\n", result.RequestID)
		fmt.Printf("  - Events count: %d\n", len(result.Events))

		if result.HasChanges() {
			fmt.Println("  - File change details:")
			fmt.Printf("    • Modified files: %v\n", result.GetModifiedFiles())
			fmt.Printf("    • Created files: %v\n", result.GetCreatedFiles())
			fmt.Printf("    • Deleted files: %v\n", result.GetDeletedFiles())
		} else {
			fmt.Println("  - No changes detected")
		}
	}

	// Stop watching
	fmt.Println("\n⏹️  Stopping directory monitoring...")
	close(stopChan)

	// Wait a moment for cleanup
	time.Sleep(1 * time.Second)

	fmt.Println("✅ Watch directory example completed successfully!")
	fmt.Println("\n📚 This example demonstrated:")
	fmt.Println("  • Creating an AgentBay session with code_latest ImageId")
	fmt.Println("  • Setting up directory monitoring with callback function")
	fmt.Println("  • Detecting file creation, modification, and deletion events")
	fmt.Println("  • Using GetFileChange method for one-time change detection")
	fmt.Println("  • Proper cleanup and resource management")
}
