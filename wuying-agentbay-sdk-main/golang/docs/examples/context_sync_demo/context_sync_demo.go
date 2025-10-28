package main

import (
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

// Context Sync Dual-Mode Example for Go SDK
//
// This example demonstrates the dual-mode context.sync() functionality:
// 1. Async mode with callback - immediate return, result handled via callback
// 2. Sync mode with wait - waits for completion before returning

func contextSyncWithCallbackUploadDemo(agentBay *agentbay.AgentBay) error {
	fmt.Println("🔄 Starting context sync with callback demo...")

	// Step 1: Create context for persistent storage
	fmt.Println("\n📦 Creating context for persistent storage...")
	contextResult, err := agentBay.Context.Get("sync-callback-demo", true)
	if err != nil {
		return fmt.Errorf("context creation failed: %w", err)
	}
	context := contextResult.Context
	fmt.Printf("✅ Context created: %s\n", context.ID)

	// Step 2: Create session with context sync
	fmt.Println("\n📦 Creating session with context sync...")
	syncPolicy := agentbay.NewSyncPolicy()
	contextSync, _ := agentbay.NewContextSync(
		context.ID,
		"/tmp/sync_data",
		syncPolicy,
	)

	params := &agentbay.CreateSessionParams{
		ImageId:     "imgc-0a9mg1h2a96j5zxie",
		ContextSync: []*agentbay.ContextSync{contextSync},
	}
	sessionResult, err := agentBay.Create(params)
	if err != nil {
		return fmt.Errorf("failed to create session: %w", err)
	}
	session := sessionResult.Session
	fmt.Printf("✅ Session created: %s\n", session.GetSessionId())

	// Step 3: Create test data
	fmt.Println("\n💾 Creating test data...")
	_, err = session.Command.ExecuteCommand("mkdir -p /tmp/sync_data/test_files")
	if err != nil {
		return fmt.Errorf("failed to create directory: %w", err)
	}

	testFiles := []struct {
		path    string
		content string
	}{
		{
			path:    "/tmp/sync_data/test_files/small.txt",
			content: generateContent("Small test file content\n", 10),
		},
		{
			path:    "/tmp/sync_data/test_files/medium.txt",
			content: generateContent("Medium test file content\n", 100),
		},
		{
			path: "/tmp/sync_data/config.json",
			content: func() string {
				config := map[string]interface{}{
					"sync_demo":  true,
					"created_at": time.Now().Format(time.RFC3339),
					"session_id": session.GetSessionId(),
				}
				jsonData, _ := json.MarshalIndent(config, "", "  ")
				return string(jsonData)
			}(),
		},
	}

	createdFiles := 0
	for _, file := range testFiles {
		writeResult, err := session.FileSystem.WriteFile(file.path, file.content, "overwrite")
		if err != nil {
			fmt.Printf("❌ Failed to create file %s: %v\n", file.path, err)
		} else if writeResult.Success {
			fmt.Printf("✅ Created file: %s\n", file.path)
			createdFiles++
		} else {
			fmt.Printf("❌ Failed to create file %s\n", file.path)
		}
	}

	fmt.Printf("📊 Created %d/%d test files\n", createdFiles, len(testFiles))

	// Method 1: Async interface with callback
	fmt.Println("\n📞 Calling context.sync() with callback...")
	syncStartTime := time.Now()

	// Use callback mode - function returns immediately
	syncResult, err := session.Context.SyncWithCallback(
		"", "", "upload", // contextId, path, mode
		func(success bool) {
			callbackTime := time.Now()
			duration := callbackTime.Sub(syncStartTime)

			if success {
				fmt.Printf("✅ Context sync completed successfully in %v\n", duration)
			} else {
				fmt.Printf("❌ Context sync completed with failures in %v\n", duration)
			}

			// Delete session in callback
			fmt.Println("🗑️  Deleting session from callback...")
			_, deleteErr := session.Delete(false) // Don't sync again since we already did
			if deleteErr != nil {
				fmt.Printf("❌ Failed to delete session from callback: %v\n", deleteErr)
			} else {
				fmt.Println("✅ Session deleted successfully from callback")
			}
		},
		150, 1500, // maxRetries, retryInterval (milliseconds)
	)

	if err != nil {
		return fmt.Errorf("context sync with callback failed: %w", err)
	}

	fmt.Printf("📤 Sync initiation result: success=%t, requestId=%s\n", syncResult.Success, syncResult.RequestID)
	fmt.Println("⏳ Waiting for callback to complete...")

	// Wait a bit for the callback to complete
	time.Sleep(10 * time.Second)

	return nil
}

func contextSyncWithCallbackDownloadDemo(agentBay *agentbay.AgentBay) error {
	fmt.Println("🔄 Starting context sync with callback download demo...")

	// Step 1: Create context for persistent storage
	// fmt.Println("\n📦 Creating context for persistent storage...")
	// contextResult, err := agentBay.Context.Get("sync-callback-download-demo", true)
	// if err != nil {
	// 	return fmt.Errorf("context creation failed: %w", err)
	// }
	// context := contextResult.Context
	// fmt.Printf("✅ Context created: %s\n", context.ID)

	// Step 2: Create session with context sync
	fmt.Println("\n📦 Creating session with context sync...")
	syncPolicy := agentbay.NewSyncPolicy()
	contextSync, _ := agentbay.NewContextSync(
		"SdkCtx-04bdvpz4zzyyzbo5p",
		"/home/wuying",
		syncPolicy,
	)

	params := &agentbay.CreateSessionParams{
		ImageId:     "imgc-0ab5takfwxakoei4g",
		ContextSync: []*agentbay.ContextSync{contextSync},
	}
	sessionResult, err := agentBay.Create(params)
	if err != nil {
		return fmt.Errorf("failed to create session: %w", err)
	}
	session := sessionResult.Session
	fmt.Printf("✅ Session created: %s\n", session.GetSessionId())

	// Step 3: Create sync directory (no test files needed for download)
	// fmt.Println("\n📁 Creating sync directory...")
	// _, err = session.Command.ExecuteCommand("mkdir -p /tmp/sync_data")
	// if err != nil {
	// 	return fmt.Errorf("failed to create directory: %w", err)
	// }
	// fmt.Println("✅ Sync directory created")

	// Method 1: Async interface with callback (download mode)
	fmt.Println("\n📞 Calling context.sync() with callback (download mode)...")
	syncStartTime := time.Now()

	// Use callback mode - function returns immediately
	syncResult, err := session.Context.SyncWithCallback(
		"", "", "download", // contextId, path, mode
		func(success bool) {
			callbackTime := time.Now()
			duration := callbackTime.Sub(syncStartTime)

			if success {
				fmt.Printf("✅ Context sync download completed successfully in %v\n", duration)
			} else {
				fmt.Printf("❌ Context sync download completed with failures in %v\n", duration)
			}

			// Delete session in callback
			fmt.Println("🗑️  Deleting session from callback...")
			_, deleteErr := session.Delete(false) // Don't sync again since we already did
			if deleteErr != nil {
				fmt.Printf("❌ Failed to delete session from callback: %v\n", deleteErr)
			} else {
				fmt.Println("✅ Session deleted successfully from callback")
			}
		},
		150, 1500, // maxRetries, retryInterval (milliseconds)
	)

	if err != nil {
		return fmt.Errorf("context sync with callback download failed: %w", err)
	}

	fmt.Printf("📤 Sync download initiation result: success=%t, requestId=%s\n", syncResult.Success, syncResult.RequestID)
	fmt.Println("⏳ Waiting for callback to complete...")

	// Wait a bit for the callback to complete
	time.Sleep(10 * time.Second)

	return nil
}

func contextSyncDemo(agentBay *agentbay.AgentBay) error {
	fmt.Println("🔄 Starting context sync demo...")

	// Step 1: Create context for persistent storage
	fmt.Println("\n📦 Creating context for persistent storage...")
	contextResult, err := agentBay.Context.Get("sync-await-demo", true)
	if err != nil {
		return fmt.Errorf("context creation failed: %w", err)
	}
	context := contextResult.Context
	fmt.Printf("✅ Context created: %s\n", context.ID)

	// Step 2: Create session with context sync
	fmt.Println("\n📦 Creating session with context sync...")
	syncPolicy := agentbay.NewSyncPolicy()
	contextSync, _ := agentbay.NewContextSync(
		context.ID,
		"/tmp/sync_data",
		syncPolicy,
	)

	params := &agentbay.CreateSessionParams{
		ImageId:     "imgc-0a9mg1h2a96j5zxie",
		ContextSync: []*agentbay.ContextSync{contextSync},
	}
	sessionResult, err := agentBay.Create(params)
	if err != nil {
		return fmt.Errorf("failed to create session: %w", err)
	}
	session := sessionResult.Session
	fmt.Printf("✅ Session created: %s\n", session.GetSessionId())

	// Step 3: Create test data
	fmt.Println("\n💾 Creating test data...")
	_, err = session.Command.ExecuteCommand("mkdir -p /tmp/sync_data/test_files")
	if err != nil {
		return fmt.Errorf("failed to create directory: %w", err)
	}

	testFiles := []struct {
		path    string
		content string
	}{
		{
			path:    "/tmp/sync_data/test_files/small.txt",
			content: generateContent("Small test file content\n", 10),
		},
		{
			path:    "/tmp/sync_data/test_files/medium.txt",
			content: generateContent("Medium test file content\n", 100),
		},
		{
			path: "/tmp/sync_data/config.json",
			content: func() string {
				config := map[string]interface{}{
					"sync_demo":  true,
					"created_at": time.Now().Format(time.RFC3339),
					"session_id": session.GetSessionId(),
				}
				jsonData, _ := json.MarshalIndent(config, "", "  ")
				return string(jsonData)
			}(),
		},
	}

	createdFiles := 0
	for _, file := range testFiles {
		writeResult, err := session.FileSystem.WriteFile(file.path, file.content, "overwrite")
		if err != nil {
			fmt.Printf("❌ Failed to create file %s: %v\n", file.path, err)
		} else if writeResult.Success {
			fmt.Printf("✅ Created file: %s\n", file.path)
			createdFiles++
		} else {
			fmt.Printf("❌ Failed to create file %s\n", file.path)
		}
	}

	fmt.Printf("📊 Created %d/%d test files\n", createdFiles, len(testFiles))

	// Method 2: Sync interface with wait
	fmt.Println("\n⏳ Calling context.sync() with wait...")
	syncStartTime := time.Now()

	// Use wait mode - function waits for completion
	syncResult, err := session.Context.SyncWithCallback("", "", "upload", nil, 150, 1500)
	if err != nil {
		return fmt.Errorf("context sync failed: %w", err)
	}

	syncDuration := time.Since(syncStartTime)

	if syncResult.Success {
		fmt.Printf("✅ Context sync completed successfully in %v\n", syncDuration)
	} else {
		fmt.Printf("❌ Context sync completed with failures in %v\n", syncDuration)
	}

	fmt.Printf("📤 Sync result: success=%t, requestId=%s\n", syncResult.Success, syncResult.RequestID)

	// Delete session
	fmt.Println("🗑️  Deleting session...")
	_, err = session.Delete(false) // Don't sync again since we already did
	if err != nil {
		return fmt.Errorf("failed to delete session: %w", err)
	}
	fmt.Println("✅ Session deleted successfully")

	return nil
}

func main() {
	fmt.Println("🔄 AgentBay Context Sync Dual-Mode Example (Go)")

	// Initialize AgentBay client
	agentBay, err := agentbay.NewAgentBay("")
	if err != nil {
		log.Fatalf("Failed to initialize AgentBay: %v", err)
	}

	// Method 1: Async interface with callback (upload)
	fmt.Println("\n" + "=" + repeat("=", 59))
	fmt.Println("🔄 Method 1: context_sync_with_callback_upload (Async with callback)")
	fmt.Println("=" + repeat("=", 59))

	// Start the first demo without waiting for it to complete
	go func() {
		if err := contextSyncWithCallbackUploadDemo(agentBay); err != nil {
			fmt.Printf("❌ Context sync with callback upload demo failed: %v\n", err)
		}
		fmt.Println("contextSyncWithCallbackUploadDemo completed")
		fmt.Println("=" + repeat("=", 59))
	}()

	// Sleep 3 seconds
	fmt.Println("\n⏳ Sleeping 3 seconds before next demo...")
	time.Sleep(3 * time.Second)

	// Method 2: Async interface with callback (download)
	fmt.Println("\n" + "=" + repeat("=", 59))
	fmt.Println("🔄 Method 2: context_sync_with_callback_download (Async with callback)")
	fmt.Println("=" + repeat("=", 59))

	// Start the second demo without waiting for it to complete
	go func() {
		if err := contextSyncWithCallbackDownloadDemo(agentBay); err != nil {
			fmt.Printf("❌ Context sync with callback download demo failed: %v\n", err)
		}
		fmt.Println("contextSyncWithCallbackDownloadDemo completed")
		fmt.Println("=" + repeat("=", 59))
	}()

	// Sleep 3 seconds
	fmt.Println("\n⏳ Sleeping 3 seconds before next demo...")
	time.Sleep(3 * time.Second)

	// Method 3: Sync interface with wait
	fmt.Println("\n" + "=" + repeat("=", 59))
	fmt.Println("🔄 Method 3: context_sync (Sync with wait)")
	fmt.Println("=" + repeat("=", 59))

	if err := contextSyncDemo(agentBay); err != nil {
		fmt.Printf("❌ Context sync demo failed: %v\n", err)
	}

	// Wait for the async demos to complete
	fmt.Println("\n⏳ Waiting for async demos to complete...")
	time.Sleep(15 * time.Second)

	fmt.Println("✅ Context sync dual-mode example completed")
}

// Helper functions
func generateContent(text string, count int) string {
	result := ""
	for i := 0; i < count; i++ {
		result += text
	}
	return result
}

func repeat(s string, count int) string {
	result := ""
	for i := 0; i < count; i++ {
		result += s
	}
	return result
}
