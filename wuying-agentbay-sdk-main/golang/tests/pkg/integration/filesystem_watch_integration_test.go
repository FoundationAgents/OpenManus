package integration

import (
	"fmt"
	"os"
	"sync"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/filesystem"
	"github.com/stretchr/testify/assert"
)

func getAPIKey() (string, error) {
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		return "", fmt.Errorf("AGENTBAY_API_KEY environment variable not set")
	}
	return apiKey, nil
}

func TestWatchDirectoryIntegration(t *testing.T) {
	// Skip if no API key
	apiKey, err := getAPIKey()
	if err != nil {
		t.Skip("Skipping integration test: " + err.Error())
	}

	fmt.Println("=== Testing watch_directory functionality ===")

	// Initialize AgentBay client
	ab, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Failed to create AgentBay client: %v", err)
	}
	fmt.Println("✅ AgentBay client initialized")

	// Create session with code_latest ImageId
	sessionParams := &agentbay.CreateSessionParams{
		ImageId: "code_latest",
	}
	sessionResult, err := ab.Create(sessionParams)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	if sessionResult.Session == nil {
		t.Fatalf("Session creation returned nil session")
	}

	session := sessionResult.Session
	fmt.Printf("✅ Session created successfully with ID: %s\n", session.GetSessionId())

	defer func() {
		// Clean up
		fmt.Println("\n7. Cleaning up session...")
		deleteResult, err := ab.Delete(session)
		if err != nil {
			fmt.Printf("❌ Error deleting session: %v\n", err)
		} else if deleteResult.Success {
			fmt.Println("✅ Session deleted successfully")
		} else {
			fmt.Printf("❌ Failed to delete session\n")
		}
	}()

	// Create the test directory
	testDir := "/tmp/watch_test_integration"
	fmt.Printf("\n1. Creating test directory: %s\n", testDir)
	createDirResult, err := session.FileSystem.CreateDirectory(testDir)
	if err != nil {
		t.Fatalf("Failed to create directory: %v", err)
	}
	if !createDirResult.Success {
		t.Fatalf("Directory creation failed")
	}
	fmt.Printf("✅ Test directory created\n")

	// Callback function to handle file changes
	var detectedEvents []*filesystem.FileChangeEvent
	var callbackCalls []int
	var mu sync.Mutex

	fileChangeCallback := func(events []*filesystem.FileChangeEvent) {
		mu.Lock()
		defer mu.Unlock()
		callbackCalls = append(callbackCalls, len(events))
		detectedEvents = append(detectedEvents, events...)
		fmt.Printf("\n🔔 Callback triggered with %d events:\n", len(events))
		for _, event := range events {
			fmt.Printf("   - %s: %s (%s)\n", event.EventType, event.Path, event.PathType)
		}
	}

	// Start directory monitoring
	fmt.Println("\n2. Starting directory monitoring...")
	stopCh := make(chan struct{})
	wg := session.FileSystem.WatchDirectory(
		testDir,
		fileChangeCallback,
		500*time.Millisecond, // Poll every 0.5 seconds for faster testing
		stopCh,
	)
	fmt.Println("✅ Directory monitoring started")

	// Wait a moment for monitoring to initialize
	time.Sleep(1 * time.Second)

	// Test 1: Create a new file
	fmt.Println("\n3. Creating a new file...")
	writeResult, err := session.FileSystem.WriteFile(testDir+"/test1.txt", "Initial content", "")
	if err != nil {
		t.Errorf("Failed to write file: %v", err)
	} else {
		fmt.Printf("Write file result: %t\n", writeResult.Success)
		assert.True(t, writeResult.Success, "File write should succeed")
	}

	// Wait for detection
	time.Sleep(2 * time.Second)

	// Test 2: Modify the file
	fmt.Println("\n4. Modifying the file...")
	modifyResult, err := session.FileSystem.WriteFile(testDir+"/test1.txt", "Modified content", "")
	if err != nil {
		t.Errorf("Failed to modify file: %v", err)
	} else {
		fmt.Printf("Modify file result: %t\n", modifyResult.Success)
		assert.True(t, modifyResult.Success, "File modify should succeed")
	}

	// Wait for detection
	time.Sleep(2 * time.Second)

	// Test 3: Create another file
	fmt.Println("\n5. Creating another file...")
	writeResult2, err := session.FileSystem.WriteFile(testDir+"/test2.txt", "Second file content", "")
	if err != nil {
		t.Errorf("Failed to write second file: %v", err)
	} else {
		fmt.Printf("Write second file result: %t\n", writeResult2.Success)
		assert.True(t, writeResult2.Success, "Second file write should succeed")
	}

	// Wait for detection
	time.Sleep(2 * time.Second)

	// Stop monitoring
	fmt.Println("\n6. Stopping directory monitoring...")
	close(stopCh)
	wg.Wait()
	fmt.Println("✅ Directory monitoring stopped")

	// Analyze results
	mu.Lock()
	defer mu.Unlock()

	fmt.Println("\n=== RESULTS ===")
	fmt.Printf("Total callback calls: %d\n", len(callbackCalls))
	fmt.Printf("Total events detected: %d\n", len(detectedEvents))
	fmt.Printf("Callback call sizes: %v\n", callbackCalls)

	fmt.Println("\nDetected events:")
	for i, event := range detectedEvents {
		fmt.Printf("  %d. %s\n", i+1, event.String())
	}

	// Verify exact number of events - must be exactly 5
	// WriteFile to non-existent file produces: create + modify (2 events)
	// WriteFile to existing file produces: modify (1 event)
	// Expected: test1.txt creation (create+modify) + test1.txt modification (modify) + test2.txt creation (create+modify) = 5 events
	expectedEvents := 5
	if len(detectedEvents) != expectedEvents {
		t.Errorf("Expected exactly %d events, got %d", expectedEvents, len(detectedEvents))
		fmt.Printf("❌ Expected exactly %d events, got %d\n", expectedEvents, len(detectedEvents))
		fmt.Println("Expected breakdown:")
		fmt.Println("  - WriteFile test1.txt (new): create + modify = 2 events")
		fmt.Println("  - WriteFile test1.txt (existing): modify = 1 event")
		fmt.Println("  - WriteFile test2.txt (new): create + modify = 2 events")
		fmt.Println("  - Total: 2 + 1 + 2 = 5 events")
	} else {
		fmt.Printf("✅ Captured expected number of events: %d\n", len(detectedEvents))
	}

	// Verify event types and counts
	createEvents := 0
	modifyEvents := 0
	for _, event := range detectedEvents {
		switch event.EventType {
		case "create":
			createEvents++
		case "modify":
			modifyEvents++
		}
	}

	fmt.Println("\nEvent type breakdown:")
	fmt.Printf("  Create events: %d (expected: 2)\n", createEvents)
	fmt.Printf("  Modify events: %d (expected: 3)\n", modifyEvents)

	// Strict validation of event types
	expectedCreateEvents := 2
	expectedModifyEvents := 3

	assert.Equal(t, expectedCreateEvents, createEvents, "Must have exactly %d create events", expectedCreateEvents)
	assert.Equal(t, expectedModifyEvents, modifyEvents, "Must have exactly %d modify events", expectedModifyEvents)
	assert.Equal(t, expectedEvents, len(detectedEvents), "Must have exactly %d total events", expectedEvents)

	if createEvents == expectedCreateEvents && modifyEvents == expectedModifyEvents {
		fmt.Println("✅ Event type distribution is correct")
	} else {
		fmt.Println("❌ Event type distribution is incorrect")
		t.Errorf("Event type validation failed: got %d create + %d modify, expected %d create + %d modify",
			createEvents, modifyEvents, expectedCreateEvents, expectedModifyEvents)
	}

	// Verify deduplication
	eventKeys := make(map[string]bool)
	duplicates := 0
	for _, event := range detectedEvents {
		eventKey := fmt.Sprintf("%s:%s:%s", event.EventType, event.Path, event.PathType)
		if eventKeys[eventKey] {
			duplicates++
		} else {
			eventKeys[eventKey] = true
		}
	}

	fmt.Println("\nDeduplication check:")
	fmt.Printf("  Unique events: %d\n", len(eventKeys))
	fmt.Printf("  Duplicate events: %d\n", duplicates)

	if duplicates == 0 {
		fmt.Println("✅ Event deduplication is working correctly")
	} else {
		fmt.Println("⚠️  Some duplicate events were detected")
	}

	// Summary
	if len(detectedEvents) == expectedEvents && createEvents == expectedCreateEvents && modifyEvents == expectedModifyEvents {
		fmt.Println("\n✅ watch_directory integration test completed successfully!")
		fmt.Println("All expected events were detected with correct types.")
	} else {
		fmt.Println("\n❌ watch_directory integration test failed!")
		fmt.Printf("Expected %d events (%d create + %d modify), got %d events (%d create + %d modify)\n",
			expectedEvents, expectedCreateEvents, expectedModifyEvents,
			len(detectedEvents), createEvents, modifyEvents)
		t.Errorf("Integration test validation failed")
	}
}

func TestWatchDirectoryFileModificationIntegration(t *testing.T) {
	// Skip if no API key
	apiKey, err := getAPIKey()
	if err != nil {
		t.Skip("Skipping integration test: " + err.Error())
	}

	fmt.Println("=== Testing file modification monitoring ===")

	// Initialize AgentBay client
	ab, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Failed to create AgentBay client: %v", err)
	}
	fmt.Println("✅ AgentBay client initialized")

	// Create session with code_latest ImageId
	sessionParams := &agentbay.CreateSessionParams{
		ImageId: "code_latest",
	}
	sessionResult, err := ab.Create(sessionParams)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	if sessionResult.Session == nil {
		t.Fatalf("Session creation returned nil session")
	}

	session := sessionResult.Session
	fmt.Printf("✅ Session created successfully with ID: %s\n", session.GetSessionId())

	defer func() {
		// Clean up session
		fmt.Println("\n7. Cleaning up session...")
		deleteResult, err := ab.Delete(session)
		if err != nil {
			fmt.Printf("❌ Error deleting session: %v\n", err)
		} else if deleteResult.Success {
			fmt.Println("✅ Session deleted successfully")
		} else {
			fmt.Printf("❌ Failed to delete session\n")
		}
	}()

	// Create test directory and initial file
	testDir := fmt.Sprintf("/tmp/test_modify_watch_%d", time.Now().Unix())
	fmt.Printf("\n1. Creating test directory: %s\n", testDir)
	createDirResult, err := session.FileSystem.CreateDirectory(testDir)
	if err != nil {
		t.Fatalf("Failed to create directory: %v", err)
	}
	if !createDirResult.Success {
		t.Fatalf("Failed to create directory")
	}
	fmt.Println("✅ Test directory created")

	// Create initial file
	testFile := fmt.Sprintf("%s/modify_test.txt", testDir)
	fmt.Printf("\n2. Creating initial file: %s\n", testFile)
	writeResult, err := session.FileSystem.WriteFile(testFile, "Initial content", "")
	if err != nil {
		t.Fatalf("Failed to create initial file: %v", err)
	}
	if !writeResult.Success {
		t.Fatalf("Failed to create initial file")
	}
	fmt.Println("✅ Initial file created")

	// Storage for captured events
	var capturedEvents []*filesystem.FileChangeEvent
	var mu sync.Mutex

	onFileModified := func(events []*filesystem.FileChangeEvent) {
		mu.Lock()
		defer mu.Unlock()
		// Filter only modify events
		for _, event := range events {
			if event.EventType == "modify" {
				capturedEvents = append(capturedEvents, event)
				fmt.Printf("🔔 Captured modify event: %s (%s)\n", event.Path, event.PathType)
			}
		}
	}

	// Start monitoring
	fmt.Println("\n3. Starting directory monitoring...")
	stopCh := make(chan struct{})
	wg := session.FileSystem.WatchDirectory(
		testDir,
		onFileModified,
		500*time.Millisecond, // Faster polling for more reliable detection
		stopCh,
	)
	fmt.Println("✅ Directory monitoring started")
	time.Sleep(1 * time.Second) // Wait for monitoring to start

	// Modify file multiple times
	fmt.Println("\n4. Modifying file multiple times...")
	for i := 0; i < 3; i++ {
		content := fmt.Sprintf("Modified content version %d", i+1)
		fmt.Printf("   Modification %d: Writing '%s'\n", i+1, content)
		modifyResult, err := session.FileSystem.WriteFile(testFile, content, "")
		if err != nil {
			fmt.Printf("❌ Failed to modify file (attempt %d): %v\n", i+1, err)
		} else if !modifyResult.Success {
			fmt.Printf("❌ Failed to modify file (attempt %d)\n", i+1)
		} else {
			fmt.Printf("✅ File modified successfully (attempt %d)\n", i+1)
		}
		time.Sleep(2 * time.Second) // Ensure events are captured and processed
	}

	// Wait a bit more for final events
	time.Sleep(2 * time.Second)

	// Stop monitoring
	fmt.Println("\n6. Stopping directory monitoring...")
	close(stopCh)
	wg.Wait()
	fmt.Println("✅ Directory monitoring stopped")

	// Verify events
	fmt.Println("\n5. Verifying captured events...")
	mu.Lock()
	defer mu.Unlock()

	fmt.Printf("Total modify events captured: %d\n", len(capturedEvents))

	// Check exact number of events - must be exactly 3
	expectedEvents := 3
	if len(capturedEvents) != expectedEvents {
		t.Errorf("Expected exactly %d modify events, got %d", expectedEvents, len(capturedEvents))
		fmt.Printf("❌ Expected exactly %d modify events, got %d\n", expectedEvents, len(capturedEvents))
		fmt.Println("Each file modification should generate exactly one modify event")
	} else {
		fmt.Printf("✅ Captured expected number of modify events: %d\n", len(capturedEvents))
	}

	// Verify event properties
	validEvents := 0
	for i, event := range capturedEvents {
		fmt.Printf("   Event %d: %s\n", i+1, event.String())

		// Check event type is modify
		if event.EventType != "modify" {
			fmt.Printf("❌ Event %d type should be 'modify', got '%s'\n", i+1, event.EventType)
			continue
		}

		// Check path contains test file
		if event.Path != testFile {
			fmt.Printf("❌ Event %d path should be '%s', got '%s'\n", i+1, testFile, event.Path)
			continue
		}

		validEvents++
		fmt.Printf("✅ Event %d is valid\n", i+1)
	}

	fmt.Println("\nValidation summary:")
	fmt.Printf("  Total events: %d\n", len(capturedEvents))
	fmt.Printf("  Valid events: %d\n", validEvents)

	// Strict assertions for test validity
	assert.Equal(t, expectedEvents, len(capturedEvents), "Must capture exactly %d modify events", expectedEvents)
	assert.Equal(t, expectedEvents, validEvents, "All captured events must be valid modify events")

	if validEvents == expectedEvents && len(capturedEvents) == expectedEvents {
		fmt.Println("✅ File modification monitoring test passed!")
	} else {
		fmt.Println("❌ File modification monitoring test failed!")
		t.Errorf("Test failed: expected %d valid events, got %d valid out of %d total",
			expectedEvents, validEvents, len(capturedEvents))
	}

	fmt.Println("\n=== File modification monitoring test completed ===")
}
