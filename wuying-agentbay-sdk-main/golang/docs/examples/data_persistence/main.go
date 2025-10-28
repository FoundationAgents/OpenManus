package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

// ConfigData represents the configuration data structure
type ConfigData struct {
	AppName   string   `json:"app_name"`
	Version   string   `json:"version"`
	CreatedAt string   `json:"created_at"`
	SessionID string   `json:"session_id"`
	Features  []string `json:"features"`
}

func main() {
	fmt.Println("🗄️ AgentBay Data Persistence Example")

	// Get API key from environment variable
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		apiKey = "akm-xxx" // Replace with your actual API key
	}

	// Initialize AgentBay client
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		log.Fatalf("Failed to create AgentBay client: %v", err)
	}

	// Run the complete data persistence demonstration
	if err := dataPersistenceDemo(agentBay); err != nil {
		log.Fatalf("❌ Example execution failed: %v", err)
	}

	fmt.Println("✅ Data persistence example completed")
}

func dataPersistenceDemo(agentBay *agentbay.AgentBay) error {
	fmt.Println("\n🔄 === Data Persistence Demonstration ===")

	// Step 1: Create a context for persistent storage
	fmt.Println("\n📦 Step 1: Creating context for persistent storage...")
	contextName := "persistence-demo-" + fmt.Sprintf("%d", time.Now().Unix())
	contextResult, err := agentBay.Context.Get(contextName, true)
	if err != nil {
		return fmt.Errorf("context creation failed: %v", err)
	}

	if contextResult.Context == nil {
		return fmt.Errorf("context not found and could not be created")
	}

	context := contextResult.Context
	fmt.Printf("✅ Context created successfully: %s\n", context.ID)
	fmt.Printf("   Name: %s\n", context.Name)
	fmt.Printf("   State: %s\n", context.State)

	// Step 2: Create first session with context sync
	fmt.Println("\n🔧 Step 2: Creating first session with context synchronization...")

	// Create sync policy for context synchronization
	syncPolicy := agentbay.NewSyncPolicy()

	// Create context sync configuration
	contextSync, _ := agentbay.NewContextSync(context.ID, "/tmp/persistent_data", syncPolicy)

	// Create session with context sync
	sessionParams1 := agentbay.NewCreateSessionParams()
	sessionParams1.AddContextSyncConfig(contextSync)
	sessionParams1.WithLabels(map[string]string{
		"example": "data-persistence",
		"phase":   "first-session",
	})

	session1Result, err := agentBay.Create(sessionParams1)
	if err != nil {
		return fmt.Errorf("first session creation failed: %v", err)
	}

	session1 := session1Result.Session
	fmt.Printf("✅ First session created successfully: %s\n", session1.SessionID)

	// Step 3: Write persistent data in first session
	fmt.Println("\n💾 Step 3: Writing persistent data in first session...")

	// Create directory structure
	_, err = session1.Command.ExecuteCommand("mkdir -p /tmp/persistent_data/config")
	if err != nil {
		log.Printf("Warning: Failed to create config directory: %v", err)
	}

	_, err = session1.Command.ExecuteCommand("mkdir -p /tmp/persistent_data/logs")
	if err != nil {
		log.Printf("Warning: Failed to create logs directory: %v", err)
	}

	// Write configuration file
	configData := ConfigData{
		AppName:   "AgentBay Demo",
		Version:   "1.0.0",
		CreatedAt: time.Now().Format("2006-01-02 15:04:05"),
		SessionID: session1.SessionID,
		Features:  []string{"data_persistence", "context_sync", "multi_session"},
	}

	configJSON, err := json.MarshalIndent(configData, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal config data: %v", err)
	}

	configResult, err := session1.FileSystem.WriteFile("/tmp/persistent_data/config/app.json", string(configJSON), "overwrite")
	if err != nil {
		log.Printf("❌ Failed to write config file: %v", err)
	} else if configResult.Success {
		fmt.Println("✅ Configuration file written successfully")
	} else {
		fmt.Printf("❌ Failed to write config file")
	}

	// Write a log file
	logContent := fmt.Sprintf(`Application Log - Session 1
Created: %s
Session ID: %s
Operation: Data persistence demonstration
Status: Files created successfully
`, time.Now().Format("2006-01-02 15:04:05"), session1.SessionID)

	logResult, err := session1.FileSystem.WriteFile("/tmp/persistent_data/logs/session1.log", logContent, "overwrite")
	if err != nil {
		log.Printf("❌ Failed to write log file: %v", err)
	} else if logResult.Success {
		fmt.Println("✅ Log file written successfully")
	} else {
		fmt.Printf("❌ Failed to write log file")
	}

	// Write a data file
	dataContent := "This is persistent data that should be available across sessions.\nIt demonstrates the context synchronization functionality."

	dataResult, err := session1.FileSystem.WriteFile("/tmp/persistent_data/shared_data.txt", dataContent, "overwrite")
	if err != nil {
		log.Printf("❌ Failed to write data file: %v", err)
	} else if dataResult.Success {
		fmt.Println("✅ Data file written successfully")
	} else {
		fmt.Printf("❌ Failed to write data file")
	}

	// List files to verify
	fmt.Println("\n📋 Files created in first session:")
	listResult, err := session1.Command.ExecuteCommand("find /tmp/persistent_data -type f -ls")
	if err != nil {
		log.Printf("Warning: Failed to list files: %v", err)
	} else {
		fmt.Println(listResult.Output)
	}

	fmt.Println("⏳ Waiting for context synchronization...")
	time.Sleep(3 * time.Second) // Allow time for sync

	// Clean up first session
	fmt.Println("\n🧹 Cleaning up first session...")
	deleteResult1, err := agentBay.Delete(session1, true) // Sync before deletion
	if err != nil {
		log.Printf("❌ First session deletion failed: %v", err)
	} else if deleteResult1.Success {
		fmt.Printf("✅ First session deleted successfully (with context sync): %s\n", deleteResult1.RequestID)
	} else {
		fmt.Printf("❌ First session deletion failed")
	}

	// Step 4: Create second session to verify persistence
	fmt.Println("\n🔧 Step 4: Creating second session to verify data persistence...")

	// Create second session with same context sync
	sessionParams2 := agentbay.NewCreateSessionParams()
	sessionParams2.AddContextSyncConfig(contextSync)
	sessionParams2.WithLabels(map[string]string{
		"example": "data-persistence",
		"phase":   "second-session",
	})

	session2Result, err := agentBay.Create(sessionParams2)
	if err != nil {
		return fmt.Errorf("second session creation failed: %v", err)
	}

	session2 := session2Result.Session
	fmt.Printf("✅ Second session created successfully: %s\n", session2.SessionID)

	// Step 5: Verify persistent data in second session
	fmt.Println("\n🔍 Step 5: Verifying persistent data in second session...")

	// Note: agentBay.Create() already waits for context synchronization to complete
	fmt.Println("✅ Context synchronization completed (handled by agentBay.Create())")

	// Check if files exist
	filesToCheck := []string{
		"/tmp/persistent_data/config/app.json",
		"/tmp/persistent_data/logs/session1.log",
		"/tmp/persistent_data/shared_data.txt",
	}

	persistentFilesFound := 0

	for _, filePath := range filesToCheck {
		fmt.Printf("\n🔍 Checking file: %s\n", filePath)
		readResult, err := session2.FileSystem.ReadFile(filePath)

		if err != nil {
			fmt.Printf("❌ File not found or not readable: %v\n", err)
		} else {
			fmt.Println("✅ File found and readable!")
			if filePath == "/tmp/persistent_data/config/app.json" {
				var configData ConfigData
				if err := json.Unmarshal([]byte(readResult.Content), &configData); err == nil {
					fmt.Printf("   📄 Config data: %s v%s\n", configData.AppName, configData.Version)
					fmt.Printf("   🕒 Created by session: %s\n", configData.SessionID)
				} else {
					content := readResult.Content
					if len(content) > 100 {
						content = content[:100] + "..."
					}
					fmt.Printf("   📄 Content: %s\n", content)
				}
			} else {
				content := readResult.Content
				if len(content) > 100 {
					content = content[:100] + "..."
				}
				fmt.Printf("   📄 Content preview: %s\n", content)
			}
			persistentFilesFound++
		}
	}

	// Add new data in second session
	fmt.Printf("\n💾 Adding new data in second session...\n")
	session2Log := fmt.Sprintf(`Application Log - Session 2
Created: %s
Session ID: %s
Operation: Data persistence verification
Persistent files found: %d/%d
Status: Persistence verification completed
`, time.Now().Format("2006-01-02 15:04:05"), session2.SessionID, persistentFilesFound, len(filesToCheck))

	session2LogResult, err := session2.FileSystem.WriteFile("/tmp/persistent_data/logs/session2.log", session2Log, "overwrite")
	if err != nil {
		log.Printf("Warning: Failed to write session2 log: %v", err)
	} else if session2LogResult.Success {
		fmt.Println("✅ Second session log written successfully")
	}

	// Summary
	fmt.Printf("\n📊 === Persistence Verification Summary ===\n")
	fmt.Printf("✅ Context ID: %s\n", context.ID)
	fmt.Printf("✅ First session: %s (deleted)\n", session1.SessionID)
	fmt.Printf("✅ Second session: %s (active)\n", session2.SessionID)
	fmt.Printf("✅ Persistent files found: %d/%d\n", persistentFilesFound, len(filesToCheck))

	if persistentFilesFound == len(filesToCheck) {
		fmt.Println("🎉 Data persistence verification SUCCESSFUL!")
		fmt.Println("   Files created in first session are accessible in second session")
	} else {
		fmt.Println("⚠️  Data persistence verification PARTIAL")
		fmt.Println("   Some files may still be syncing or failed to persist")
	}

	// Clean up second session
	fmt.Println("\n🧹 Cleaning up second session...")
	deleteResult2, err := agentBay.Delete(session2, true)
	if err != nil {
		log.Printf("❌ Second session deletion failed: %v", err)
	} else if deleteResult2.Success {
		fmt.Printf("✅ Second session deleted successfully (with context sync): %s\n", deleteResult2.RequestID)
	} else {
		fmt.Printf("❌ Second session deletion failed")
	}

	// Clean up context
	fmt.Println("\n🧹 Cleaning up context...")
	deleteContextResult, err := agentBay.Context.Delete(context)
	if err != nil {
		log.Printf("❌ Context deletion failed: %v", err)
	} else if deleteContextResult.Success {
		fmt.Printf("✅ Context deleted successfully: %s\n", deleteContextResult.RequestID)
	} else {
		fmt.Printf("❌ Context deletion failed")
	}

	return nil
}
