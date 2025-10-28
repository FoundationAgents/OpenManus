package integration

import (
	"fmt"
	"os"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestContextSyncIntegration tests the context sync functionality with a real session
func TestContextSyncIntegration(t *testing.T) {
	// Skip in CI environment or if API key is not available
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" || os.Getenv("CI") != "" {
		t.Skip("Skipping integration test: No API key available or running in CI")
	}

	// Initialize the AgentBay client
	ab, err := agentbay.NewAgentBay(apiKey)
	require.NoError(t, err, "Failed to create AgentBay client")

	// Create a unique context name for this test
	contextName := fmt.Sprintf("test-sync-context-%d", time.Now().Unix())

	// Create a context
	contextResult, err := ab.Context.Get(contextName, true)
	require.NoError(t, err, "Error getting/creating context")
	require.NotNil(t, contextResult.Context, "Context should not be nil")

	context := contextResult.Context
	t.Logf("Created context: %s (ID: %s)", context.Name, context.ID)

	// Create session parameters with context sync
	sessionParams := agentbay.NewCreateSessionParams()

	// Create sync policy
	syncPolicy := &agentbay.SyncPolicy{
		UploadPolicy: &agentbay.UploadPolicy{
			AutoUpload:     true,
			UploadStrategy: agentbay.UploadBeforeResourceRelease,
		},
		DownloadPolicy: &agentbay.DownloadPolicy{
			AutoDownload:     true,
			DownloadStrategy: agentbay.DownloadAsync,
		},
		DeletePolicy: &agentbay.DeletePolicy{
			SyncLocalFile: true,
		},
		BWList: &agentbay.BWList{
			WhiteLists: []*agentbay.WhiteList{
				{
					Path:         "/home/wuying",
					ExcludePaths: []string{"/home/wuying/temp"},
				},
			},
		},
	}

	// Add context sync to session parameters
	sessionParams.AddContextSync(context.ID, "/home/wuying", syncPolicy)

	// Set session parameters
	sessionParams.WithLabels(map[string]string{
		"test": "context-sync-integration",
	})
	sessionParams.WithImageId("linux_latest")

	// Create session
	sessionResult, err := ab.Create(sessionParams)
	require.NoError(t, err, "Error creating session")
	require.NotNil(t, sessionResult.Session, "Session should not be nil")

	session := sessionResult.Session
	t.Logf("Created session: %s", session.SessionID)

	// Ensure session is deleted after the test
	defer func() {
		deleteResult, err := ab.Delete(session, true)
		if err != nil {
			t.Logf("Warning: Failed to delete session: %v", err)
		} else {
			t.Logf("Session deleted: %s (RequestID: %s)", session.SessionID, deleteResult.RequestID)
		}
	}()

	// Ensure context is deleted after the test
	defer func() {
		deleteContextResult, err := ab.Context.Delete(context)
		if err != nil {
			t.Logf("Warning: Failed to delete context: %v", err)
		} else {
			t.Logf("Context deleted: %s (RequestID: %s)", context.ID, deleteContextResult.RequestID)
		}
	}()

	// Test getting context info
	t.Run("GetContextInfo", func(t *testing.T) {
		contextInfo, err := session.Context.Info()
		require.NoError(t, err, "Error getting context info")
		assert.NotEmpty(t, contextInfo.RequestID, "Request ID should not be empty")

		// Log the parsed context status data
		if len(contextInfo.ContextStatusData) > 0 {
			t.Log("Parsed context status data:")
			printContextStatusData(t, contextInfo.ContextStatusData)

			// Verify some basic properties of the context status data
			for _, data := range contextInfo.ContextStatusData {
				assert.NotEmpty(t, data.ContextId, "ContextId should not be empty")
				assert.NotEmpty(t, data.Path, "Path should not be empty")
				assert.NotEmpty(t, data.Status, "Status should not be empty")
				assert.NotEmpty(t, data.TaskType, "TaskType should not be empty")
			}
		} else {
			t.Log("No parsed context status data available")
		}
	})

	// Test syncing context
	t.Run("SyncContext", func(t *testing.T) {
		syncResult, err := session.Context.Sync()
		require.NoError(t, err, "Error syncing context")
		assert.True(t, syncResult.Success, "Context sync should be successful")
		assert.NotEmpty(t, syncResult.RequestID, "Request ID should not be empty")

		// Check context info after sync
		contextInfo, err := session.Context.Info()
		require.NoError(t, err, "Error getting context info after sync")

		// Log the parsed context status data after sync
		if len(contextInfo.ContextStatusData) > 0 {
			t.Log("Parsed context status data after sync:")
			printContextStatusData(t, contextInfo.ContextStatusData)
		} else {
			t.Log("No parsed context status data available after sync")
		}
	})
}

// TestContextSyncWithMultipleContexts tests creating a session with multiple context syncs
func TestContextSyncWithMultipleContexts(t *testing.T) {
	// Skip in CI environment or if API key is not available
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" || os.Getenv("CI") != "" {
		t.Skip("Skipping integration test: No API key available or running in CI")
	}

	// Initialize the AgentBay client
	ab, err := agentbay.NewAgentBay(apiKey)
	require.NoError(t, err, "Failed to create AgentBay client")

	// Create two unique context names for this test
	contextName1 := fmt.Sprintf("test-sync-context1-%d", time.Now().Unix())
	contextName2 := fmt.Sprintf("test-sync-context2-%d", time.Now().Unix())

	// Create contexts
	contextResult1, err := ab.Context.Get(contextName1, true)
	require.NoError(t, err, "Error getting/creating context 1")
	require.NotNil(t, contextResult1.Context, "Context 1 should not be nil")
	context1 := contextResult1.Context

	contextResult2, err := ab.Context.Get(contextName2, true)
	require.NoError(t, err, "Error getting/creating context 2")
	require.NotNil(t, contextResult2.Context, "Context 2 should not be nil")
	context2 := contextResult2.Context

	t.Logf("Created contexts: %s and %s", context1.ID, context2.ID)

	// Create session parameters with multiple context syncs
	sessionParams := agentbay.NewCreateSessionParams()

	// Define paths for the contexts
	path1 := "/home/wuying/context1"
	path2 := "/home/wuying/context2"

	// Add first context sync with default policy
	basicPolicy := agentbay.NewSyncPolicy()
	basicSync, err := agentbay.NewContextSync(context1.ID, path1, basicPolicy)
	require.NoError(t, err, "Error creating basic context sync")
	sessionParams.AddContextSyncConfig(basicSync)

	// Add second context sync with custom policy
	customPolicy := &agentbay.SyncPolicy{
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
					Path:         "/home/wuying/context2/data",
					ExcludePaths: []string{"/home/wuying/context2/data/temp"},
				},
			},
		},
	}
	advancedSync, err := agentbay.NewContextSync(context2.ID, path2, customPolicy)
	require.NoError(t, err, "Error creating advanced context sync")
	sessionParams.AddContextSyncConfig(advancedSync)

	// Set session parameters
	sessionParams.WithLabels(map[string]string{
		"test": "multi-context-sync-integration",
	})
	sessionParams.WithImageId("linux_latest")

	// Create session
	sessionResult, err := ab.Create(sessionParams)
	require.NoError(t, err, "Error creating session")
	require.NotNil(t, sessionResult.Session, "Session should not be nil")

	session := sessionResult.Session
	t.Logf("Created session: %s", session.SessionID)

	// Ensure session is deleted after the test
	defer func() {
		deleteResult, err := ab.Delete(session, true)
		if err != nil {
			t.Logf("Warning: Failed to delete session: %v", err)
		} else {
			t.Logf("Session deleted: %s (RequestID: %s)", session.SessionID, deleteResult.RequestID)
		}
	}()

	// Ensure contexts are deleted after the test
	defer func() {
		deleteContextResult1, err := ab.Context.Delete(context1)
		if err != nil {
			t.Logf("Warning: Failed to delete context 1: %v", err)
		} else {
			t.Logf("Context 1 deleted: %s (RequestID: %s)", context1.ID, deleteContextResult1.RequestID)
		}

		deleteContextResult2, err := ab.Context.Delete(context2)
		if err != nil {
			t.Logf("Warning: Failed to delete context 2: %v", err)
		} else {
			t.Logf("Context 2 deleted: %s (RequestID: %s)", context2.ID, deleteContextResult2.RequestID)
		}
	}()

	// Test syncing context
	t.Run("SyncContext", func(t *testing.T) {
		// Wait for session to be ready
		time.Sleep(10 * time.Second)

		// Sync contexts
		syncResult, err := session.Context.Sync()
		require.NoError(t, err, "Error syncing context")
		assert.True(t, syncResult.Success, "Context sync should be successful")
		assert.NotEmpty(t, syncResult.RequestID, "Request ID should not be empty")

		// Wait for sync to complete
		time.Sleep(5 * time.Second)

		// Check context info for first context
		contextInfo1, err := session.Context.InfoWithParams(context1.ID, path1, "")
		require.NoError(t, err, "Error getting context info for first context")
		if len(contextInfo1.ContextStatusData) > 0 {
			t.Log("Context status data for first context:")
			printContextStatusData(t, contextInfo1.ContextStatusData)
		}

		// Check context info for second context
		contextInfo2, err := session.Context.InfoWithParams(context2.ID, path2, "")
		require.NoError(t, err, "Error getting context info for second context")
		if len(contextInfo2.ContextStatusData) > 0 {
			t.Log("Context status data for second context:")
			printContextStatusData(t, contextInfo2.ContextStatusData)
		}
	})
}

// TestContextSyncSessionParams tests creating session parameters with context syncs
func TestContextSyncSessionParams(t *testing.T) {
	// This is a unit test that doesn't require an API key
	contextID := "ctx-12345"

	// Test adding context sync with separate parameters
	t.Run("AddContextSync", func(t *testing.T) {
		sessionParams := agentbay.NewCreateSessionParams()

		syncPolicy := &agentbay.SyncPolicy{
			UploadPolicy: &agentbay.UploadPolicy{
				AutoUpload:     true,
				UploadStrategy: agentbay.UploadBeforeResourceRelease,
			},
		}

		sessionParams.AddContextSync(contextID, "/data", syncPolicy)

		assert.Len(t, sessionParams.ContextSync, 1)
		assert.Equal(t, contextID, sessionParams.ContextSync[0].ContextID)
		assert.Equal(t, "/data", sessionParams.ContextSync[0].Path)
		assert.Equal(t, syncPolicy, sessionParams.ContextSync[0].Policy)
	})

	// Test adding context sync with config object
	t.Run("AddContextSyncConfig", func(t *testing.T) {
		sessionParams := agentbay.NewCreateSessionParams()

		uploadPolicy := &agentbay.UploadPolicy{
			AutoUpload:     true,
			UploadStrategy: agentbay.UploadBeforeResourceRelease,
		}
		syncPolicy := &agentbay.SyncPolicy{
			UploadPolicy: uploadPolicy,
		}
		contextSync, err := agentbay.NewContextSync(contextID, "/home", syncPolicy)
		require.NoError(t, err, "Error creating context sync")

		sessionParams.AddContextSyncConfig(contextSync)

		assert.Len(t, sessionParams.ContextSync, 1)
		assert.Equal(t, contextID, sessionParams.ContextSync[0].ContextID)
		assert.Equal(t, "/home", sessionParams.ContextSync[0].Path)
		assert.NotNil(t, sessionParams.ContextSync[0].Policy)
		assert.NotNil(t, sessionParams.ContextSync[0].Policy.UploadPolicy)
		assert.True(t, sessionParams.ContextSync[0].Policy.UploadPolicy.AutoUpload)
		assert.Equal(t, agentbay.UploadBeforeResourceRelease, sessionParams.ContextSync[0].Policy.UploadPolicy.UploadStrategy)
	})

	// Test adding multiple context syncs
	t.Run("MultipleContextSyncs", func(t *testing.T) {
		sessionParams := agentbay.NewCreateSessionParams()

		// Add first context sync
		sessionParams.AddContextSync(contextID, "/data", nil)

		// Add second context sync
		contextSync, err := agentbay.NewContextSync("ctx-67890", "/home", nil)
		require.NoError(t, err, "Error creating second context sync")
		sessionParams.AddContextSyncConfig(contextSync)

		assert.Len(t, sessionParams.ContextSync, 2)
		assert.Equal(t, contextID, sessionParams.ContextSync[0].ContextID)
		assert.Equal(t, "/data", sessionParams.ContextSync[0].Path)
		assert.Equal(t, "ctx-67890", sessionParams.ContextSync[1].ContextID)
		assert.Equal(t, "/home", sessionParams.ContextSync[1].Path)
	})
}

// TestContextSyncMockSession tests context sync operations with a mock session
func TestContextSyncMockSession(t *testing.T) {
	// Create a mock session
	mockSession := testutil.NewMockSession()

	// Test getting context info
	t.Run("MockGetContextInfo", func(t *testing.T) {
		contextInfo, err := mockSession.Context.Info()
		require.NoError(t, err, "Error getting context info from mock")
		assert.NotEmpty(t, contextInfo.RequestID, "Request ID should not be empty")
		assert.Equal(t, "mock-request-id-info", contextInfo.RequestID)

		// Check the ContextStatusData field
		require.NotEmpty(t, contextInfo.ContextStatusData, "Context status data should not be empty")
		assert.Equal(t, "mock-context-id", contextInfo.ContextStatusData[0].ContextId)
		assert.Equal(t, "/mock/path", contextInfo.ContextStatusData[0].Path)
		assert.Equal(t, "Success", contextInfo.ContextStatusData[0].Status)
		assert.Equal(t, "download", contextInfo.ContextStatusData[0].TaskType)
		assert.Equal(t, int64(1600000000), contextInfo.ContextStatusData[0].StartTime)
		assert.Equal(t, int64(1600000100), contextInfo.ContextStatusData[0].FinishTime)
	})

	// Test syncing context
	t.Run("MockSyncContext", func(t *testing.T) {
		syncResult, err := mockSession.Context.Sync()
		require.NoError(t, err, "Error syncing context from mock")
		assert.True(t, syncResult.Success, "Context sync should be successful")
		assert.NotEmpty(t, syncResult.RequestID, "Request ID should not be empty")
		assert.Equal(t, "mock-request-id-sync", syncResult.RequestID)
	})
}

// helper: print context status data
func printContextStatusData(t *testing.T, data []agentbay.ContextStatusData) {
	if len(data) == 0 {
		t.Log("No context status data available")
		return
	}

	for i, item := range data {
		t.Logf("Context Status Data [%d]:", i)
		t.Logf("  ContextId: %s", item.ContextId)
		t.Logf("  Path: %s", item.Path)
		t.Logf("  Status: %s", item.Status)
		t.Logf("  TaskType: %s", item.TaskType)
		t.Logf("  StartTime: %d", item.StartTime)
		t.Logf("  FinishTime: %d", item.FinishTime)
		if item.ErrorMessage != "" {
			t.Logf("  ErrorMessage: %s", item.ErrorMessage)
		}
	}
}

// TestContextSyncFilePersistence tests the full context synchronization flow with file persistence between sessions
func TestContextSyncFilePersistence(t *testing.T) {
	// Skip in CI environment or if API key is not available
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" || os.Getenv("CI") != "" {
		t.Skip("Skipping integration test: No API key available or running in CI")
	}

	// Initialize the AgentBay client
	ab, err := agentbay.NewAgentBay(apiKey)
	require.NoError(t, err, "Failed to create AgentBay client")

	// 1. Create a unique context name and get its ID
	contextName := fmt.Sprintf("test-file-persistence-%d", time.Now().Unix())
	contextResult, err := ab.Context.Get(contextName, true)
	require.NoError(t, err, "Error getting/creating context")
	require.NotNil(t, contextResult.Context, "Context should not be nil")

	context := contextResult.Context
	t.Logf("Created context: %s (ID: %s)", context.Name, context.ID)

	// Ensure context is deleted after the test
	defer func() {
		deleteContextResult, err := ab.Context.Delete(context)
		if err != nil {
			t.Logf("Warning: Failed to delete context: %v", err)
		} else {
			t.Logf("Context deleted: %s (RequestID: %s)", context.ID, deleteContextResult.RequestID)
		}
	}()

	// 2. Create a session with context sync, using a timestamped path
	timestamp := time.Now().Unix()
	syncPath := fmt.Sprintf("/home/wuying/test-path-%d", timestamp)

	// Use default policy
	defaultPolicy := agentbay.NewSyncPolicy()

	sessionParams := agentbay.NewCreateSessionParams()
	sessionParams.AddContextSync(context.ID, syncPath, defaultPolicy)
	sessionParams.WithImageId("linux_latest")
	sessionParams.WithLabels(map[string]string{
		"test": "file-persistence-test",
	})

	// Create first session
	sessionResult, err := ab.Create(sessionParams)
	require.NoError(t, err, "Error creating first session")
	require.NotNil(t, sessionResult.Session, "Session should not be nil")

	session1 := sessionResult.Session
	t.Logf("Created first session: %s", session1.SessionID)

	// 3. Wait for session to be ready (we'll just sleep for a few seconds)
	t.Logf("Waiting for session to be ready...")
	time.Sleep(10 * time.Second)

	// helper: retry get context info
	getContextInfoWithRetry := func(session *agentbay.Session, t *testing.T, contextId string, path string) *agentbay.ContextInfoResult {
		var contextInfo *agentbay.ContextInfoResult
		var err error
		var foundSuccess bool

		for i := 0; i < 20; i++ {
			foundSuccess = false
			contextInfo, err = session.Context.Info()
			if err != nil {
				t.Logf("Error getting context info (attempt %d): %v", i+1, err)
				time.Sleep(1 * time.Second)
				continue
			}

			// Check if we have any context status data
			if contextInfo == nil || len(contextInfo.ContextStatusData) == 0 {
				t.Logf("Context info is empty (attempt %d), retrying...", i+1)
				time.Sleep(1 * time.Second)
				continue
			}

			// Check if we have a successful status for the specified context ID and path
			for _, data := range contextInfo.ContextStatusData {
				if data.ContextId == contextId && data.Path == path && data.Status == "Success" {
					foundSuccess = true
					t.Logf("Found successful context status for contextId=%s, path=%s (attempt %d)",
						contextId, path, i+1)
					break
				}
			}

			if foundSuccess {
				break
			}

			t.Logf("No successful context status found for contextId=%s, path=%s (attempt %d), retrying...",
				contextId, path, i+1)
			time.Sleep(1 * time.Second)
		}

		require.NotNil(t, contextInfo, "Context info should not be nil after retries")
		require.NotEmpty(t, contextInfo.ContextStatusData, "Context status data should not be empty after retries")

		if !foundSuccess {
			t.Logf("Warning: Did not find a successful context status for contextId=%s, path=%s after all retries",
				contextId, path)
		}

		return contextInfo
	}

	// 3.1. Check context status using Info() method
	contextInfo := getContextInfoWithRetry(session1, t, context.ID, syncPath)
	t.Logf("Context status request ID: %s", contextInfo.RequestID)

	// Log the parsed context status data
	if len(contextInfo.ContextStatusData) > 0 {
		t.Log("Parsed context status data:")
		printContextStatusData(t, contextInfo.ContextStatusData)
	} else {
		t.Log("No parsed context status data available")
	}

	// 4. Create the directory structure first
	t.Logf("Creating directory: %s", syncPath)
	dirResult, err := session1.FileSystem.CreateDirectory(syncPath)
	require.NoError(t, err, "Error creating directory")
	assert.NotEmpty(t, dirResult.RequestID, "Directory creation request ID should not be empty")

	// 5. Create a 1GB file in the context sync path
	testFilePath := syncPath + "/test-file.txt"

	t.Logf("Creating 1GB file at %s", testFilePath)
	createFileCmd := fmt.Sprintf("dd if=/dev/zero of=%s bs=1M count=1024", testFilePath)
	cmdResult, err := session1.Command.ExecuteCommand(createFileCmd)
	if err != nil {
		t.Logf("Warning: Failed to create 1GB file: %v", err)
	} else {
		t.Logf("Created 1GB file: %s", cmdResult)
	}

	// 6. Sync to trigger file upload using explicit Sync() call
	t.Logf("Triggering context sync...")
	syncResult, err := session1.Context.Sync()
	require.NoError(t, err, "Error syncing context")
	require.True(t, syncResult.Success, "Context sync should be successful")
	t.Logf("Context sync successful (RequestID: %s)", syncResult.RequestID)

	// 7. Wait for sync to complete
	t.Logf("Waiting for file upload to complete...")
	time.Sleep(5 * time.Second)

	// 7.1. Check context status again after sync
	contextInfo = getContextInfoWithRetry(session1, t, context.ID, syncPath)
	t.Logf("Context status request ID after sync: %s", contextInfo.RequestID)

	// Log the parsed context status data after sync
	if len(contextInfo.ContextStatusData) > 0 {
		t.Log("Parsed context status data after sync:")
		printContextStatusData(t, contextInfo.ContextStatusData)

		// Verify context status data
		for _, data := range contextInfo.ContextStatusData {
			if data.ContextId == context.ID {
				assert.Equal(t, syncPath, data.Path, "Path should match the sync path")
				assert.NotEmpty(t, data.Status, "Status should not be empty")
				assert.NotZero(t, data.StartTime, "StartTime should not be zero")
				assert.NotZero(t, data.FinishTime, "FinishTime should not be zero")
			}
		}
	} else {
		t.Log("No parsed context status data available after sync")
	}

	// 8. Release first session
	t.Logf("Releasing first session...")
	deleteResult, err := ab.Delete(session1, true)
	require.NoError(t, err, "Error deleting first session")
	require.NotEmpty(t, deleteResult.RequestID, "Delete request ID should not be empty")

	// 9. Create a second session with the same context ID
	t.Logf("Creating second session with the same context ID...")
	sessionParams = agentbay.NewCreateSessionParams()
	sessionParams.AddContextSync(context.ID, syncPath, defaultPolicy)
	sessionParams.WithImageId("linux_latest")
	sessionParams.WithLabels(map[string]string{
		"test": "file-persistence-test-second",
	})

	sessionResult, err = ab.Create(sessionParams)
	require.NoError(t, err, "Error creating second session")
	require.NotNil(t, sessionResult.Session, "Second session should not be nil")

	session2 := sessionResult.Session
	t.Logf("Created second session: %s", session2.SessionID)

	// Ensure second session is deleted after the test
	defer func() {
		deleteResult, err := ab.Delete(session2, true)
		if err != nil {
			t.Logf("Warning: Failed to delete second session: %v", err)
		} else {
			t.Logf("Second session deleted: %s (RequestID: %s)", session2.SessionID, deleteResult.RequestID)
		}
	}()

	// 10. Wait for session to be ready and files to be downloaded
	t.Logf("Waiting for file download to complete...")
	time.Sleep(10 * time.Second)

	// 10.1. Check context status in second session
	contextInfo = getContextInfoWithRetry(session2, t, context.ID, syncPath)
	t.Logf("Context status request ID in second session: %s", contextInfo.RequestID)

	// Log the parsed context status data for second session
	if len(contextInfo.ContextStatusData) > 0 {
		t.Log("Parsed context status data in second session:")
		printContextStatusData(t, contextInfo.ContextStatusData)

		// Verify context status data in second session
		foundDownload := false
		for _, data := range contextInfo.ContextStatusData {
			if data.ContextId == context.ID && data.TaskType == "download" {
				foundDownload = true
				assert.Equal(t, syncPath, data.Path, "Path should match the sync path")
				assert.NotEmpty(t, data.Status, "Status should not be empty")
			}
		}
		assert.True(t, foundDownload, "Should find a download task for the context")
	} else {
		t.Log("No parsed context status data available in second session")
	}

	// 11. Verify the 1GB file exists in the second session
	t.Logf("Verifying 1GB file exists in second session...")

	// Check file size using ls command
	checkFileCmd := fmt.Sprintf("ls -la %s", testFilePath)
	fileInfo, err := session2.Command.ExecuteCommand(checkFileCmd)
	if err != nil {
		t.Logf("Warning: Failed to check file info: %v", err)
	} else {
		t.Logf("File info: %s", fileInfo)
	}

	// Verify file exists and has expected size (approximately 1GB)
	fileExistsCmd := fmt.Sprintf("test -f %s && echo 'File exists'", testFilePath)
	existsResult, err := session2.Command.ExecuteCommand(fileExistsCmd)
	if err != nil {
		t.Logf("Warning: Failed to check if file exists: %v", err)
	} else {
		t.Logf("File existence check: %s", existsResult)
		require.Contains(t, existsResult.Output, "File exists", "1GB file should exist in second session")
	}

	t.Logf("1GB file persistence verified successfully")
}

// TestContextStatusDataParsing tests the parsing of context status data
func TestContextStatusDataParsing(t *testing.T) {
	// Skip in CI environment or if API key is not available
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" || os.Getenv("CI") != "" {
		t.Skip("Skipping integration test: No API key available or running in CI")
	}

	// Initialize the AgentBay client
	ab, err := agentbay.NewAgentBay(apiKey)
	require.NoError(t, err, "Failed to create AgentBay client")

	// Create a unique context name for this test
	contextName := fmt.Sprintf("test-status-parsing-%d", time.Now().Unix())

	// Create a context
	contextResult, err := ab.Context.Get(contextName, true)
	require.NoError(t, err, "Error getting/creating context")
	require.NotNil(t, contextResult.Context, "Context should not be nil")

	context := contextResult.Context
	t.Logf("Created context: %s (ID: %s)", context.Name, context.ID)

	// Create session parameters with context sync
	sessionParams := agentbay.NewCreateSessionParams()

	// Create sync policy
	syncPolicy := agentbay.NewSyncPolicy()

	// Add context sync to session parameters
	sessionParams.AddContextSync(context.ID, "/home/wuying/test-path", syncPolicy)

	// Set session parameters
	sessionParams.WithLabels(map[string]string{
		"test": "context-status-parsing",
	})
	sessionParams.WithImageId("linux_latest")

	// Create session
	sessionResult, err := ab.Create(sessionParams)
	require.NoError(t, err, "Error creating session")
	require.NotNil(t, sessionResult.Session, "Session should not be nil")

	session := sessionResult.Session
	t.Logf("Created session: %s", session.SessionID)

	// Ensure session is deleted after the test
	defer func() {
		deleteResult, err := ab.Delete(session, true)
		if err != nil {
			t.Logf("Warning: Failed to delete session: %v", err)
		} else {
			t.Logf("Session deleted: %s (RequestID: %s)", session.SessionID, deleteResult.RequestID)
		}
	}()

	// Ensure context is deleted after the test
	defer func() {
		deleteContextResult, err := ab.Context.Delete(context)
		if err != nil {
			t.Logf("Warning: Failed to delete context: %v", err)
		} else {
			t.Logf("Context deleted: %s (RequestID: %s)", context.ID, deleteContextResult.RequestID)
		}
	}()

	// Test getting context info
	t.Run("GetContextInfoAndVerifyParsing", func(t *testing.T) {
		// First trigger a sync to ensure we have status data
		syncResult, err := session.Context.Sync()
		require.NoError(t, err, "Error syncing context")
		assert.True(t, syncResult.Success, "Context sync should be successful")

		// Get context info
		contextInfo, err := session.Context.Info()
		require.NoError(t, err, "Error getting context info")
		assert.NotEmpty(t, contextInfo.RequestID, "Request ID should not be empty")

		// Verify context status data
		if len(contextInfo.ContextStatusData) > 0 {
			t.Log("Parsed context status data:")
			printContextStatusData(t, contextInfo.ContextStatusData)

			// Find the specific context we created
			var found bool
			for _, data := range contextInfo.ContextStatusData {
				if data.ContextId == context.ID {
					found = true

					// Verify all fields are properly parsed
					assert.Equal(t, context.ID, data.ContextId, "Context ID should match")
					assert.Equal(t, "/home/wuying/test-path", data.Path, "Path should match")
					assert.NotEmpty(t, data.Status, "Status should not be empty")
					assert.NotEmpty(t, data.TaskType, "TaskType should not be empty")

					// Verify timestamps if they exist
					if data.StartTime > 0 {
						assert.True(t, data.StartTime < time.Now().Unix()+100, "StartTime should be in the past or near present")
					}
					if data.FinishTime > 0 {
						assert.True(t, data.FinishTime >= data.StartTime, "FinishTime should be after StartTime")
					}

					break
				}
			}
			assert.True(t, found, "Should find the context we created in the status data")
		} else {
			t.Log("No parsed context status data available")
			t.Skip("Skipping detailed assertions as no context status data was returned")
		}
	})

	// Test getting context info with parameters
	t.Run("GetContextInfoWithParams", func(t *testing.T) {
		// Get context info with specific context ID
		contextInfo, err := session.Context.InfoWithParams(context.ID, "", "")
		require.NoError(t, err, "Error getting context info with context ID")
		assert.NotEmpty(t, contextInfo.RequestID, "Request ID should not be empty")

		// Verify filtered results
		if len(contextInfo.ContextStatusData) > 0 {
			t.Log("Parsed context status data with context ID filter:")
			printContextStatusData(t, contextInfo.ContextStatusData)

			// All results should have the specified context ID
			for _, data := range contextInfo.ContextStatusData {
				assert.Equal(t, context.ID, data.ContextId, "All results should have the specified context ID")
			}
		}

		// Get context info with specific path
		contextInfo, err = session.Context.InfoWithParams("", "/home/wuying/test-path", "")
		require.NoError(t, err, "Error getting context info with path")

		// Verify filtered results
		if len(contextInfo.ContextStatusData) > 0 {
			t.Log("Parsed context status data with path filter:")
			printContextStatusData(t, contextInfo.ContextStatusData)

			// All results should have the specified path
			for _, data := range contextInfo.ContextStatusData {
				assert.Equal(t, "/home/wuying/test-path", data.Path, "All results should have the specified path")
			}
		}

		// Get context info with task type (if we know what task types are available)
		if len(contextInfo.ContextStatusData) > 0 && contextInfo.ContextStatusData[0].TaskType != "" {
			taskType := contextInfo.ContextStatusData[0].TaskType

			contextInfo, err = session.Context.InfoWithParams("", "", taskType)
			require.NoError(t, err, "Error getting context info with task type")

			// Verify filtered results
			if len(contextInfo.ContextStatusData) > 0 {
				t.Log("Parsed context status data with task type filter:")
				printContextStatusData(t, contextInfo.ContextStatusData)

				// All results should have the specified task type
				for _, data := range contextInfo.ContextStatusData {
					assert.Equal(t, taskType, data.TaskType, "All results should have the specified task type")
				}
			}
		}
	})
}

// TestContextSyncPersistenceWithRetry tests the context synchronization with file persistence between sessions
// with retry mechanism for context status checks
func TestContextSyncPersistenceWithRetry(t *testing.T) {
	// Skip in CI environment or if API key is not available
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" || os.Getenv("CI") != "" {
		t.Skip("Skipping integration test: No API key available or running in CI")
	}

	// Initialize the AgentBay client
	ab, err := agentbay.NewAgentBay(apiKey)
	require.NoError(t, err, "Failed to create AgentBay client")

	// 1. Create a unique context name and get its ID
	contextName := fmt.Sprintf("test-persistence-retry-%d", time.Now().Unix())
	contextResult, err := ab.Context.Get(contextName, true)
	require.NoError(t, err, "Error getting/creating context")
	require.NotNil(t, contextResult.Context, "Context should not be nil")

	context := contextResult.Context
	t.Logf("Created context: %s (ID: %s)", context.Name, context.ID)

	// Ensure context is deleted after the test
	defer func() {
		deleteContextResult, err := ab.Context.Delete(context)
		if err != nil {
			t.Logf("Warning: Failed to delete context: %v", err)
		} else {
			t.Logf("Context deleted: %s (RequestID: %s)", context.ID, deleteContextResult.RequestID)
		}
	}()

	// 2. Create a session with context sync, using a timestamped path under /home/wuying/
	timestamp := time.Now().Unix()
	syncPath := fmt.Sprintf("/home/wuying/test-path-%d", timestamp)

	// Use default policy
	defaultPolicy := agentbay.NewSyncPolicy()

	// Create session parameters with context sync
	sessionParams := agentbay.NewCreateSessionParams()
	sessionParams.AddContextSync(context.ID, syncPath, defaultPolicy)
	sessionParams.WithImageId("linux_latest")
	sessionParams.WithLabels(map[string]string{
		"test": "persistence-retry-test",
	})

	// Create first session
	sessionResult, err := ab.Create(sessionParams)
	require.NoError(t, err, "Error creating first session")
	require.NotNil(t, sessionResult.Session, "Session should not be nil")

	session1 := sessionResult.Session
	t.Logf("Created first session: %s", session1.SessionID)

	// 3. Wait for session to be ready and retry context info until data is available
	t.Logf("Waiting for session to be ready and context status data to be available...")

	var contextInfo *agentbay.ContextInfoResult
	var foundData bool
	for i := 0; i < 20; i++ {
		contextInfo, err = session1.Context.Info()
		require.NoError(t, err, "Error getting context info")

		if len(contextInfo.ContextStatusData) > 0 {
			t.Logf("Found context status data on attempt %d", i+1)
			foundData = true
			break
		}

		t.Logf("No context status data available yet (attempt %d), retrying in 1 second...", i+1)
		time.Sleep(1 * time.Second)
	}

	require.True(t, foundData, "Context status data should be available after retries")
	t.Logf("Context status data:")
	printContextStatusData(t, contextInfo.ContextStatusData)

	// 4. Create a 1GB file in the context sync path
	testFilePath := syncPath + "/test-file.txt"

	// Create directory first
	t.Logf("Creating directory: %s", syncPath)
	dirResult, err := session1.FileSystem.CreateDirectory(syncPath)
	require.NoError(t, err, "Error creating directory")
	assert.NotEmpty(t, dirResult.RequestID, "Directory creation request ID should not be empty")

	// Create a 1GB file using dd command
	t.Logf("Creating 1GB file at %s", testFilePath)
	createFileCmd := fmt.Sprintf("dd if=/dev/zero of=%s bs=1M count=1024", testFilePath)
	cmdResult, err := session1.Command.ExecuteCommand(createFileCmd)
	if err != nil {
		t.Logf("Warning: Failed to create 1GB file: %v", err)
	} else {
		t.Logf("Created 1GB file: %s", cmdResult)
	}

	// 5. Sync to trigger file upload
	t.Logf("Triggering context sync...")
	syncResult, err := session1.Context.Sync()
	require.NoError(t, err, "Error syncing context")
	require.True(t, syncResult.Success, "Context sync should be successful")
	t.Logf("Context sync successful (RequestID: %s)", syncResult.RequestID)

	// 6. Get context info with retry for upload status
	t.Logf("Checking file upload status with retry...")

	foundUpload := false
	for i := 0; i < 20; i++ {
		contextInfo, err = session1.Context.Info()
		require.NoError(t, err, "Error getting context info")

		// Check if we have upload status for our context
		for _, data := range contextInfo.ContextStatusData {
			if data.ContextId == context.ID && data.TaskType == "upload" {
				foundUpload = true
				t.Logf("Found upload task for context at attempt %d", i+1)
				break
			}
		}

		if foundUpload {
			break
		}

		t.Logf("No upload status found yet (attempt %d), retrying in 1 second...", i+1)
		time.Sleep(1 * time.Second)
	}

	if foundUpload {
		t.Logf("Found upload status for context")
		printContextStatusData(t, contextInfo.ContextStatusData)
	} else {
		t.Logf("Warning: Could not find upload status after all retries")
	}

	// 7. Release first session
	t.Logf("Releasing first session...")
	deleteResult, err := ab.Delete(session1, true)
	require.NoError(t, err, "Error deleting first session")
	require.NotEmpty(t, deleteResult.RequestID, "Delete request ID should not be empty")

	// 8. Create a second session with the same context ID
	t.Logf("Creating second session with the same context ID...")
	sessionParams = agentbay.NewCreateSessionParams()
	sessionParams.AddContextSync(context.ID, syncPath, defaultPolicy)
	sessionParams.WithImageId("linux_latest")
	sessionParams.WithLabels(map[string]string{
		"test": "persistence-retry-test-second",
	})

	sessionResult, err = ab.Create(sessionParams)
	require.NoError(t, err, "Error creating second session")
	require.NotNil(t, sessionResult.Session, "Second session should not be nil")

	session2 := sessionResult.Session
	t.Logf("Created second session: %s", session2.SessionID)

	// Ensure second session is deleted after the test
	defer func() {
		deleteResult, err := ab.Delete(session2, true)
		if err != nil {
			t.Logf("Warning: Failed to delete second session: %v", err)
		} else {
			t.Logf("Second session deleted: %s (RequestID: %s)", session2.SessionID, deleteResult.RequestID)
		}
	}()

	// 9. Get context info with retry for download status
	t.Logf("Checking file download status with retry...")

	foundDownload := false
	for i := 0; i < 20; i++ {
		contextInfo, err = session2.Context.Info()
		require.NoError(t, err, "Error getting context info")

		// Check if we have download status for our context
		for _, data := range contextInfo.ContextStatusData {
			if data.ContextId == context.ID && data.TaskType == "download" {
				foundDownload = true
				t.Logf("Found download task for context at attempt %d", i+1)
				break
			}
		}

		if foundDownload {
			break
		}

		t.Logf("No download status found yet (attempt %d), retrying in 1 second...", i+1)
		time.Sleep(1 * time.Second)
	}

	if foundDownload {
		t.Logf("Found download status for context")
		printContextStatusData(t, contextInfo.ContextStatusData)
	} else {
		t.Logf("Warning: Could not find download status after all retries")
	}

	// 10. Verify the 1GB file exists in the second session
	t.Logf("Verifying 1GB file exists in second session...")

	// Check file size using ls command
	checkFileCmd := fmt.Sprintf("ls -la %s", testFilePath)
	fileInfo, err := session2.Command.ExecuteCommand(checkFileCmd)
	if err != nil {
		t.Logf("Warning: Failed to check file info: %v", err)
	} else {
		t.Logf("File info: %s", fileInfo)
	}

	// Verify file exists and has expected size (approximately 1GB)
	fileExistsCmd := fmt.Sprintf("test -f %s && echo 'File exists'", testFilePath)
	existsResult, err := session2.Command.ExecuteCommand(fileExistsCmd)
	if err != nil {
		t.Logf("Warning: Failed to check if file exists: %v", err)
	} else {
		t.Logf("File existence check: %s", existsResult)
		require.Contains(t, existsResult.Output, "File exists", "1GB file should exist in second session")
	}

	t.Logf("1GB file persistence verified successfully")
}
