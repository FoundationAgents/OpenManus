package main

import (
	"fmt"
	"log"
	"os"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	fmt.Println("🗄️ RecyclePolicy Example - Data Lifecycle Management")

	// Get API key from environment variable
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		log.Fatal("AGENTBAY_API_KEY environment variable is required")
	}

	// Initialize AgentBay client
	client, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		log.Fatalf("Failed to create AgentBay client: %v", err)
	}

	// Run example
	if err := recyclePolicyExample(client); err != nil {
		log.Fatalf("❌ Example execution failed: %v", err)
	}

	fmt.Println("✅ RecyclePolicy example completed successfully")
}

func recyclePolicyExample(client *agentbay.AgentBay) error {
	fmt.Println("\n=== RecyclePolicy Example ===")

	// Step 1: Create a context
	contextName := fmt.Sprintf("recycle-demo-%d", time.Now().Unix())
	fmt.Printf("\n📦 Creating context: %s\n", contextName)

	contextResult, err := client.Context.Get(contextName, true)
	if err != nil {
		return fmt.Errorf("failed to create context: %v", err)
	}

	context := contextResult.Context
	fmt.Printf("✅ Context created: %s\n", context.ID)

	// Ensure cleanup
	defer func() {
		fmt.Println("\n🧹 Cleaning up context...")
		if _, err := client.Context.Delete(context); err != nil {
			log.Printf("Warning: Failed to delete context: %v", err)
		} else {
			fmt.Println("✅ Context deleted")
		}
	}()

	// Step 2: Create RecyclePolicy with 1 day lifecycle
	fmt.Println("\n📋 Creating RecyclePolicy with 1 day lifecycle...")
	recyclePolicy := &agentbay.RecyclePolicy{
		Lifecycle: agentbay.Lifecycle1Day,
		Paths:     []string{""}, // Apply to all paths
	}

	// Step 3: Create SyncPolicy with RecyclePolicy
	syncPolicy := agentbay.NewSyncPolicy()
	syncPolicy.RecyclePolicy = recyclePolicy

	fmt.Printf("   Lifecycle: %s\n", syncPolicy.RecyclePolicy.Lifecycle)
	fmt.Printf("   Paths: %v\n", syncPolicy.RecyclePolicy.Paths)

	// Step 4: Create ContextSync
	contextSync, err := agentbay.NewContextSync(context.ID, "/tmp/recycle_data", syncPolicy)
	if err != nil {
		return fmt.Errorf("failed to create context sync: %v", err)
	}

	// Step 5: Create session with context sync
	fmt.Println("\n🔧 Creating session with RecyclePolicy...")
	params := agentbay.NewCreateSessionParams().
		WithLabels(map[string]string{
			"example":   "recycle_policy",
			"lifecycle": "1day",
		}).
		AddContextSyncConfig(contextSync)

	sessionResult, err := client.Create(params)
	if err != nil {
		return fmt.Errorf("failed to create session: %v", err)
	}

	session := sessionResult.Session
	fmt.Printf("✅ Session created: %s\n", session.SessionID)

	// Ensure cleanup
	defer func() {
		fmt.Println("\n🧹 Cleaning up session...")
		if _, err := client.Delete(session); err != nil {
			log.Printf("Warning: Failed to delete session: %v", err)
		} else {
			fmt.Println("✅ Session deleted")
		}
	}()

	// Step 6: Write some test data
	fmt.Println("\n💾 Writing test data...")

	// Create directory
	_, err = session.Command.ExecuteCommand("mkdir -p /tmp/recycle_data")
	if err != nil {
		log.Printf("Warning: Failed to create directory: %v", err)
	}

	// Write test file
	testContent := fmt.Sprintf("This data has RecyclePolicy with Lifecycle_1Day\nCreated at: %s\nSession: %s",
		time.Now().Format("2006-01-02 15:04:05"),
		session.SessionID)

	writeResult, err := session.FileSystem.WriteFile("/tmp/recycle_data/test.txt", testContent, "overwrite")
	if err != nil {
		return fmt.Errorf("failed to write test file: %v", err)
	}

	if writeResult.Success {
		fmt.Println("✅ Test data written successfully")
	} else {
		return fmt.Errorf("failed to write test data")
	}

	// Step 7: Verify file was written
	fmt.Println("\n🔍 Verifying file content...")
	readResult, err := session.FileSystem.ReadFile("/tmp/recycle_data/test.txt")
	if err != nil {
		return fmt.Errorf("failed to read test file: %v", err)
	}

	fmt.Printf("✅ File content verified:\n%s\n", readResult.Content)

	// Step 8: Show RecyclePolicy details
	fmt.Println("\n📊 RecyclePolicy Details:")
	fmt.Printf("   • Lifecycle: %s (data will be deleted after 1 day)\n", recyclePolicy.Lifecycle)
	fmt.Printf("   • Paths: %v (applies to all paths)\n", recyclePolicy.Paths)
	fmt.Println("   • This policy will automatically delete old data to save storage")

	return nil
}
