package agentbay_test

import (
	"encoding/json"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/stretchr/testify/assert"
)

func TestNewUploadPolicy(t *testing.T) {
	policy := agentbay.NewUploadPolicy()

	assert.NotNil(t, policy)
	assert.True(t, policy.AutoUpload)
	assert.Equal(t, agentbay.UploadBeforeResourceRelease, policy.UploadStrategy)
}

func TestNewDownloadPolicy(t *testing.T) {
	policy := agentbay.NewDownloadPolicy()

	assert.NotNil(t, policy)
	assert.True(t, policy.AutoDownload)
	assert.Equal(t, agentbay.DownloadAsync, policy.DownloadStrategy)
}

func TestNewDeletePolicy(t *testing.T) {
	policy := agentbay.NewDeletePolicy()

	assert.NotNil(t, policy)
	assert.True(t, policy.SyncLocalFile)
}

func TestNewSyncPolicy(t *testing.T) {
	policy := agentbay.NewSyncPolicy()

	assert.NotNil(t, policy)
	assert.NotNil(t, policy.UploadPolicy)
	assert.NotNil(t, policy.DownloadPolicy)
	assert.NotNil(t, policy.DeletePolicy)
	assert.NotNil(t, policy.BWList)
	assert.NotNil(t, policy.BWList.WhiteLists)
	assert.Len(t, policy.BWList.WhiteLists, 1)
	assert.Equal(t, "", policy.BWList.WhiteLists[0].Path)
	assert.Empty(t, policy.BWList.WhiteLists[0].ExcludePaths)

}

func TestNewContextSync(t *testing.T) {
	contextID := "ctx-12345"
	path := "/home/user"
	policy := agentbay.NewSyncPolicy()

	sync, err := agentbay.NewContextSync(contextID, path, policy)

	assert.NoError(t, err)
	assert.NotNil(t, sync)
	assert.Equal(t, contextID, sync.ContextID)
	assert.Equal(t, path, sync.Path)
	assert.Equal(t, policy, sync.Policy)
}

func TestNewContextSyncWithNilPolicy(t *testing.T) {
	contextID := "ctx-12345"
	path := "/home/user"

	sync, err := agentbay.NewContextSync(contextID, path, nil)

	assert.NoError(t, err)
	assert.NotNil(t, sync)
	assert.Equal(t, contextID, sync.ContextID)
	assert.Equal(t, path, sync.Path)
	assert.Nil(t, sync.Policy)
}

func TestContextSyncWithPolicy(t *testing.T) {
	contextID := "ctx-12345"
	path := "/home/user"

	sync, err := agentbay.NewContextSync(contextID, path, nil)
	assert.NoError(t, err)
	assert.Nil(t, sync.Policy)

	// Create a custom policy
	policy := &agentbay.SyncPolicy{
		UploadPolicy: &agentbay.UploadPolicy{
			AutoUpload:     true,
			UploadStrategy: agentbay.UploadBeforeResourceRelease,
		},
		DownloadPolicy: &agentbay.DownloadPolicy{
			AutoDownload:     false,
			DownloadStrategy: agentbay.DownloadAsync,
		},
		DeletePolicy: &agentbay.DeletePolicy{
			SyncLocalFile: false,
		},
		BWList: &agentbay.BWList{
			WhiteLists: []*agentbay.WhiteList{
				{
					Path:         "/data",
					ExcludePaths: []string{"/data/temp"},
				},
			},
		},
	}

	// Apply the policy
	result, err := sync.WithPolicy(policy)

	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Same(t, sync, result) // Verify method chaining returns the same instance
	assert.Equal(t, policy, sync.Policy)

	// Verify upload policy
	assert.NotNil(t, sync.Policy.UploadPolicy)
	assert.True(t, sync.Policy.UploadPolicy.AutoUpload)
	assert.Equal(t, agentbay.UploadBeforeResourceRelease, sync.Policy.UploadPolicy.UploadStrategy)

	// Verify download policy
	assert.NotNil(t, sync.Policy.DownloadPolicy)
	assert.False(t, sync.Policy.DownloadPolicy.AutoDownload)
	assert.Equal(t, agentbay.DownloadAsync, sync.Policy.DownloadPolicy.DownloadStrategy)

	// Verify delete policy
	assert.NotNil(t, sync.Policy.DeletePolicy)
	assert.False(t, sync.Policy.DeletePolicy.SyncLocalFile)

	// Verify BWList
	assert.NotNil(t, sync.Policy.BWList)
	assert.Len(t, sync.Policy.BWList.WhiteLists, 1)
	assert.Equal(t, "/data", sync.Policy.BWList.WhiteLists[0].Path)
	assert.Equal(t, []string{"/data/temp"}, sync.Policy.BWList.WhiteLists[0].ExcludePaths)

}

func TestDefaultSyncPolicyMatchesRequirements(t *testing.T) {
	// Create a default sync policy
	policy := agentbay.NewSyncPolicy()

	// Verify the policy matches the exact requirements
	assert.NotNil(t, policy)

	// Verify uploadPolicy
	assert.NotNil(t, policy.UploadPolicy)
	assert.True(t, policy.UploadPolicy.AutoUpload, "uploadPolicy.autoUpload should be true")
	assert.Equal(t, agentbay.UploadBeforeResourceRelease, policy.UploadPolicy.UploadStrategy, "uploadPolicy.uploadStrategy should be 'UploadBeforeResourceRelease'")

	// Verify downloadPolicy
	assert.NotNil(t, policy.DownloadPolicy)
	assert.True(t, policy.DownloadPolicy.AutoDownload, "downloadPolicy.autoDownload should be true")
	assert.Equal(t, agentbay.DownloadAsync, policy.DownloadPolicy.DownloadStrategy, "downloadPolicy.downloadStrategy should be 'DownloadAsync'")

	// Verify deletePolicy
	assert.NotNil(t, policy.DeletePolicy)
	assert.True(t, policy.DeletePolicy.SyncLocalFile, "deletePolicy.syncLocalFile should be true")

	// Verify bwList
	assert.NotNil(t, policy.BWList)
	assert.NotNil(t, policy.BWList.WhiteLists)
	assert.Len(t, policy.BWList.WhiteLists, 1, "bwList.whiteLists should have exactly 1 element")

	whiteList := policy.BWList.WhiteLists[0]
	assert.Equal(t, "", whiteList.Path, "bwList.whiteLists[0].path should be empty string")
	assert.NotNil(t, whiteList.ExcludePaths)
	assert.Empty(t, whiteList.ExcludePaths, "bwList.whiteLists[0].excludePaths should be empty array")

	// Additional verification: test JSON marshaling to ensure the structure is correct
	jsonData, err := json.Marshal(policy)
	assert.NoError(t, err, "Policy should be marshallable to JSON")

	// Debug: print the JSON structure
	t.Logf("Generated JSON: %s", string(jsonData))

	// Verify the JSON structure matches the expected format
	var jsonMap map[string]interface{}
	err = json.Unmarshal(jsonData, &jsonMap)
	assert.NoError(t, err, "JSON should be unmarshallable")

	// Verify uploadPolicy in JSON
	uploadPolicy, exists := jsonMap["uploadPolicy"].(map[string]interface{})
	assert.True(t, exists, "uploadPolicy should exist in JSON")
	assert.Equal(t, true, uploadPolicy["autoUpload"], "JSON uploadPolicy.autoUpload should be true")
	assert.Equal(t, "UploadBeforeResourceRelease", uploadPolicy["uploadStrategy"], "JSON uploadPolicy.uploadStrategy should be 'UploadBeforeResourceRelease'")

	// Verify downloadPolicy in JSON
	downloadPolicy, exists := jsonMap["downloadPolicy"].(map[string]interface{})
	assert.True(t, exists, "downloadPolicy should exist in JSON")
	assert.Equal(t, true, downloadPolicy["autoDownload"], "JSON downloadPolicy.autoDownload should be true")
	assert.Equal(t, "DownloadAsync", downloadPolicy["downloadStrategy"], "JSON downloadPolicy.downloadStrategy should be 'DownloadAsync'")

	// Verify deletePolicy in JSON
	deletePolicy, exists := jsonMap["deletePolicy"].(map[string]interface{})
	assert.True(t, exists, "deletePolicy should exist in JSON")
	assert.Equal(t, true, deletePolicy["syncLocalFile"], "JSON deletePolicy.syncLocalFile should be true")

	// Verify bwList in JSON
	bwList, exists := jsonMap["bwList"].(map[string]interface{})
	assert.True(t, exists, "bwList should exist in JSON")

	whiteLists, exists := bwList["whiteLists"].([]interface{})
	assert.True(t, exists, "bwList.whiteLists should exist in JSON")
	assert.Len(t, whiteLists, 1, "JSON bwList.whiteLists should have exactly 1 element")

	whiteListMap := whiteLists[0].(map[string]interface{})
	assert.Equal(t, "", whiteListMap["path"], "JSON bwList.whiteLists[0].path should be empty string")

	// Check if excludePaths exists in the JSON (it might be omitted if empty)
	if excludePaths, exists := whiteListMap["excludePaths"]; exists {
		excludePathsArray, ok := excludePaths.([]interface{})
		assert.True(t, ok, "bwList.whiteLists[0].excludePaths should be an array if present")
		assert.Empty(t, excludePathsArray, "JSON bwList.whiteLists[0].excludePaths should be empty array")
	} else {
		// If excludePaths is not present in JSON (omitted due to omitempty), that's also acceptable
		t.Log("excludePaths is omitted from JSON (which is acceptable due to omitempty tag)")
	}

	// Check that syncPaths should not exist in the JSON
	_, syncPathsExists := jsonMap["syncPaths"]
	assert.False(t, syncPathsExists, "syncPaths should not exist in JSON")
}
