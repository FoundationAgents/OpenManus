package main

import (
	"fmt"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/filesystem"
)

func main() {
	// Get API key from environment variable
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		fmt.Println("❌ Please set the AGENTBAY_API_KEY environment variable")
		return
	}

	fmt.Println("🚀 Watch Directory Example")
	fmt.Println(strings.Repeat("=", 50))

	// Initialize AgentBay client
	agentBayClient, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		fmt.Printf("❌ Failed to create AgentBay client: %v\n", err)
		return
	}
	fmt.Println("✅ AgentBay client initialized")

	// Create session with code_latest ImageId
	sessionParams := &agentbay.CreateSessionParams{
		ImageId: "code_latest",
	}
	sessionResult, err := agentBayClient.Create(sessionParams)
	if err != nil {
		fmt.Printf("❌ Failed to create session: %v\n", err)
		return
	}
	// SessionResult doesn't have Success field, check if Session is nil
	if sessionResult.Session == nil {
		fmt.Printf("❌ Failed to create session\n")
		return
	}

	session := sessionResult.Session
	fmt.Printf("✅ Session created: %s\n", session.GetSessionId())

	// Ensure cleanup on exit
	defer func() {
		fmt.Println("\n🧹 Cleaning up...")
		deleteResult, err := agentBayClient.Delete(session)
		if err != nil {
			fmt.Printf("⚠️  Error during cleanup: %v\n", err)
		} else if deleteResult.Success {
			fmt.Println("✅ Session cleaned up successfully")
		} else {
			fmt.Println("⚠️  Session cleanup failed")
		}
	}()

	// Create a test directory to monitor
	testDir := "/tmp/watch_example"
	fmt.Printf("\n📁 Creating test directory: %s\n", testDir)

	createResult, err := session.FileSystem.CreateDirectory(testDir)
	if err != nil {
		fmt.Printf("❌ Failed to create directory: %v\n", err)
		return
	}
	if !createResult.Success {
		fmt.Printf("❌ Failed to create directory\n")
		return
	}
	fmt.Println("✅ Test directory created")

	// Set up file change monitoring
	var detectedChanges []*filesystem.FileChangeEvent
	var mu sync.Mutex

	onFileChange := func(events []*filesystem.FileChangeEvent) {
		mu.Lock()
		defer mu.Unlock()

		fmt.Printf("\n🔔 Detected %d file changes:\n", len(events))
		for _, event := range events {
			fmt.Printf("   📄 %s: %s (%s)\n",
				strings.ToUpper(event.EventType), event.Path, event.PathType)
		}
		detectedChanges = append(detectedChanges, events...)
	}

	fmt.Println("\n👁️  Starting directory monitoring...")
	fmt.Println("   Press Ctrl+C to stop monitoring")

	// Start monitoring
	stopCh := make(chan struct{})
	wg := session.FileSystem.WatchDirectory(
		testDir,
		onFileChange,
		500*time.Millisecond, // Check every 500ms (updated default)
		stopCh,
	)
	fmt.Println("✅ Directory monitoring started")

	// Set up signal handling for graceful shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	// Start a goroutine to demonstrate file operations
	go func() {
		time.Sleep(2 * time.Second) // Wait for monitoring to start

		fmt.Println("\n🔨 Demonstrating file operations...")

		// Create some files
		filesToCreate := []struct {
			name    string
			content string
		}{
			{"example1.txt", "Hello, World!"},
			{"example2.txt", "This is a test file."},
			{"config.json", `{"setting": "value"}`},
		}

		for _, file := range filesToCreate {
			filepath := fmt.Sprintf("%s/%s", testDir, file.name)
			fmt.Printf("   Creating: %s\n", file.name)

			writeResult, err := session.FileSystem.WriteFile(filepath, file.content, "")
			if err != nil {
				fmt.Printf("   ❌ Failed to create %s: %v\n", file.name, err)
			} else if writeResult.Success {
				fmt.Printf("   ✅ Created: %s\n", file.name)
			} else {
				fmt.Printf("   ❌ Failed to create %s\n", file.name)
			}

			time.Sleep(1500 * time.Millisecond) // Give time for monitoring to detect changes
		}

		// Modify a file
		fmt.Println("\n   Modifying example1.txt...")
		modifyResult, err := session.FileSystem.WriteFile(
			fmt.Sprintf("%s/example1.txt", testDir),
			"Hello, World! - Modified content",
			"",
		)
		if err != nil {
			fmt.Printf("   ❌ Failed to modify file: %v\n", err)
		} else if modifyResult.Success {
			fmt.Println("   ✅ Modified example1.txt")
		} else {
			fmt.Printf("   ❌ Failed to modify file\n")
		}

		// Wait a bit more to capture all events
		fmt.Println("\n⏳ Waiting for final events...")
		time.Sleep(3 * time.Second)
	}()

	// Wait for interrupt signal
	<-sigCh
	fmt.Println("\n\n🛑 Stopping directory monitoring...")

	// Stop monitoring
	close(stopCh)
	wg.Wait()
	fmt.Println("✅ Directory monitoring stopped")

	// Summary
	mu.Lock()
	defer mu.Unlock()

	fmt.Printf("\n📊 Summary:\n")
	fmt.Printf("   Total events detected: %d\n", len(detectedChanges))

	if len(detectedChanges) > 0 {
		fmt.Println("   Event breakdown:")
		eventTypes := make(map[string]int)
		for _, event := range detectedChanges {
			eventTypes[event.EventType]++
		}

		for eventType, count := range eventTypes {
			fmt.Printf("     %s: %d\n", eventType, count)
		}
	}

	fmt.Println("\n✨ Example completed successfully!")
}
