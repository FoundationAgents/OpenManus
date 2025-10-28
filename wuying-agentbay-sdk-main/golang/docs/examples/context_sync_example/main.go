package main

import (
	"fmt"
	"log"
	"os"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	// Get API key from environment variable
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		apiKey = "akm-xxx" // Replace with your actual API key
	}
	// Initialize the AgentBay client
	ab, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		log.Fatalf("Failed to create AgentBay client: %v", err)
	}

	// Example 1: Create a new context
	fmt.Println("Example 1: Creating a new context...")
	// Use timestamp in context name to ensure uniqueness for each test run
	contextName := "my-sync-context-" + fmt.Sprintf("%d", time.Now().Unix())
	contextResult, err := ab.Context.Get(contextName, true)
	if err != nil {
		log.Fatalf("Error getting context: %v", err)
	}

	if contextResult.Context == nil {
		log.Fatalf("Context not found and could not be created")
	}

	context := contextResult.Context
	fmt.Printf("Context created/retrieved: %s (ID: %s)\n", context.Name, context.ID)

	// Example 2: Creating a basic context sync configuration
	fmt.Println("\nExample 2: Creating a basic context sync configuration...")
	basicPolicy := agentbay.NewSyncPolicy()
	basicSync, _ := agentbay.NewContextSync(context.ID, "/tmp", basicPolicy)
	fmt.Printf("Basic sync - ContextID: %s, Path: %s\n", basicSync.ContextID, basicSync.Path)

	// Example 3: Create an advanced context sync configuration with policies
	fmt.Println("\nExample 3: Creating an advanced context sync configuration...")

	// Create upload policy
	uploadPolicy := &agentbay.UploadPolicy{
		AutoUpload:     true,
		UploadStrategy: agentbay.UploadBeforeResourceRelease,
	}

	// Create download policy
	downloadPolicy := &agentbay.DownloadPolicy{
		AutoDownload:     true,
		DownloadStrategy: agentbay.DownloadAsync,
	}

	// Create delete policy
	deletePolicy := &agentbay.DeletePolicy{
		SyncLocalFile: true,
	}

	// Create white list
	whiteList := &agentbay.WhiteList{
		Path:         "/important",               // Relative directory  /home/wuying/important
		ExcludePaths: []string{"/temp", "/logs"}, // Relative directory /home/wuying/important/temp,/home/wuying/important/logs
	}

	// Create BW list
	bwList := &agentbay.BWList{
		WhiteLists: []*agentbay.WhiteList{whiteList},
	}

	// Create sync policy
	syncPolicy := &agentbay.SyncPolicy{
		UploadPolicy:   uploadPolicy,
		DownloadPolicy: downloadPolicy,
		DeletePolicy:   deletePolicy,
		BWList:         bwList,
	}

	// Create advanced sync configuration
	advancedSync, _ := agentbay.NewContextSync(context.ID, "/home/wuying", syncPolicy)

	fmt.Printf("Advanced sync - ContextID: %s, Path: %s\n", advancedSync.ContextID, advancedSync.Path)
	fmt.Printf("  - Upload: Auto=%t, Strategy=%s\n",
		advancedSync.Policy.UploadPolicy.AutoUpload,
		advancedSync.Policy.UploadPolicy.UploadStrategy)
	fmt.Printf("  - Download: Auto=%t, Strategy=%s\n",
		advancedSync.Policy.DownloadPolicy.AutoDownload,
		advancedSync.Policy.DownloadPolicy.DownloadStrategy)
	fmt.Printf("  - Delete: SyncLocalFile=%t\n", advancedSync.Policy.DeletePolicy.SyncLocalFile)
	fmt.Printf("  - WhiteList: Path=%s, ExcludePaths=%v\n",
		advancedSync.Policy.BWList.WhiteLists[0].Path,
		advancedSync.Policy.BWList.WhiteLists[0].ExcludePaths)

	// Example 4: Create session parameters with context sync
	fmt.Println("\nExample 4: Creating session parameters with context sync...")
	sessionParams := agentbay.NewCreateSessionParams()

	// Method 1: Add context sync using AddContextSync
	sessionParams.AddContextSync(context.ID, "/var", basicPolicy)

	// Method 2: Add context sync using AddContextSyncConfig
	sessionParams.AddContextSyncConfig(basicSync)

	// Set labels for the session
	sessionParams.WithLabels(map[string]string{
		"username": "alice",
		"project":  "context-sync-example",
	})

	sessionParams.WithImageId("linux_latest")

	fmt.Printf("Session params created with %d context sync configurations\n", len(sessionParams.ContextSync))

	// Example 5: Create session with context sync
	fmt.Println("\nExample 5: Creating session with context sync...")
	sessionResult, err := ab.Create(sessionParams)
	if err != nil {
		log.Fatalf("Error creating session: %v", err)
	}

	session := sessionResult.Session
	fmt.Printf("Session created with ID: %s\n", session.SessionID)
	fmt.Printf("Session creation RequestID: %s\n", sessionResult.RequestID)
	fmt.Println("Note: The Create() method automatically monitored the context status")
	fmt.Println("and only returned after all context operations were complete or reached maximum retries.")

	// Example 6: Use context manager from session
	fmt.Println("\nExample 6: Using context manager from session...")

	// Get context info
	contextInfo, err := session.Context.Info()
	if err != nil {
		log.Printf("Error getting context info: %v", err)
	} else {
		fmt.Printf("Context info RequestID: %s\n", contextInfo.RequestID)
		if len(contextInfo.ContextStatusData) > 0 {
			fmt.Printf("Found %d context status entries:\n", len(contextInfo.ContextStatusData))
			for i, statusData := range contextInfo.ContextStatusData {
				fmt.Printf("  Status[%d]: %s\n", i, statusData.Status)
			}
		} else {
			fmt.Println("No context status data available")
		}
	}

	// Sync context
	syncResult, err := session.Context.Sync()
	if err != nil {
		log.Printf("Error syncing context: %v", err)
	} else {
		fmt.Printf("Context sync success: %t (RequestID: %s)\n", syncResult.Success, syncResult.RequestID)
	}

	// Example 7: Alternative way using builder pattern
	fmt.Println("\nExample 7: Using builder pattern for context sync...")

	// Create a custom policy for the builder example
	builderPolicy := &agentbay.SyncPolicy{
		UploadPolicy: &agentbay.UploadPolicy{
			AutoUpload:     true,
			UploadStrategy: agentbay.UploadBeforeResourceRelease,
		},
		DownloadPolicy: &agentbay.DownloadPolicy{
			AutoDownload:     true,
			DownloadStrategy: agentbay.DownloadAsync,
		},
		BWList: &agentbay.BWList{
			WhiteLists: []*agentbay.WhiteList{
				{
					Path:         "/src",                    // Relative directory /workspace/src
					ExcludePaths: []string{"/node_modules"}, // Relative directory /workspace/src/node_modules
				},
			},
		},
	}

	builderSync, _ := agentbay.NewContextSync(context.ID, "/workspace", nil)
	builderSync, _ = builderSync.WithPolicy(builderPolicy)

	fmt.Printf("Builder sync - ContextID: %s, Path: %s\n",
		builderSync.ContextID, builderSync.Path)

	// Clean up
	fmt.Println("\nCleaning up...")

	// Delete the session with context synchronization
	fmt.Println("Deleting the session with context synchronization...")
	deleteResult, err := ab.Delete(session, true) // Using syncContext=true
	if err != nil {
		log.Printf("Error deleting session: %v", err)
	} else {
		fmt.Printf("Session deleted successfully with context synchronization (RequestID: %s)\n", deleteResult.RequestID)
		fmt.Println("Note: The Delete() method synchronized the context before session deletion")
		fmt.Println("and monitored all context operations until completion.")
	}

	// Alternative method using Session's Delete method:
	// deleteResult, err := session.Delete(true)

	// Delete the context
	deleteContextResult, err := ab.Context.Delete(context)
	if err != nil {
		log.Printf("Error deleting context: %v", err)
	} else {
		fmt.Printf("Context deleted successfully (RequestID: %s)\n", deleteContextResult.RequestID)
	}

	fmt.Println("\nContext sync example completed!")
}
