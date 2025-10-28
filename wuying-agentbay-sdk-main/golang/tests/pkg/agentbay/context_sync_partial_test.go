package agentbay_test

import (
	"encoding/json"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/stretchr/testify/assert"
)

func TestSyncPolicyWithPartialParameters(t *testing.T) {
	// Test SyncPolicy with only upload_policy
	uploadPolicy := &agentbay.UploadPolicy{
		AutoUpload:     false,
		UploadStrategy: agentbay.UploadBeforeResourceRelease,
	}
	syncPolicy := &agentbay.SyncPolicy{
		UploadPolicy: uploadPolicy,
	}

	// Marshal to JSON to trigger ensureDefaults
	jsonData, err := json.Marshal(syncPolicy)
	assert.NoError(t, err, "Should marshal without error")

	// Unmarshal back to verify all fields are present
	var result agentbay.SyncPolicy
	err = json.Unmarshal(jsonData, &result)
	assert.NoError(t, err, "Should unmarshal without error")

	// Verify upload_policy is set correctly
	assert.NotNil(t, result.UploadPolicy)
	assert.Equal(t, false, result.UploadPolicy.AutoUpload)
	assert.Equal(t, agentbay.UploadBeforeResourceRelease, result.UploadPolicy.UploadStrategy)

	// Verify other policies are filled with defaults
	assert.NotNil(t, result.DownloadPolicy)
	assert.NotNil(t, result.DeletePolicy)
	assert.NotNil(t, result.BWList)

	// Verify default values
	assert.True(t, result.DownloadPolicy.AutoDownload)
	assert.Equal(t, agentbay.DownloadAsync, result.DownloadPolicy.DownloadStrategy)
	assert.True(t, result.DeletePolicy.SyncLocalFile)
	assert.Len(t, result.BWList.WhiteLists, 1)
}

func TestSyncPolicyWithNoParameters(t *testing.T) {
	// Test SyncPolicy with no parameters
	syncPolicy := &agentbay.SyncPolicy{}

	// Marshal to JSON to trigger ensureDefaults
	jsonData, err := json.Marshal(syncPolicy)
	assert.NoError(t, err, "Should marshal without error")

	// Unmarshal back to verify all fields are present
	var result agentbay.SyncPolicy
	err = json.Unmarshal(jsonData, &result)
	assert.NoError(t, err, "Should unmarshal without error")

	// Verify all policies are set with defaults
	assert.NotNil(t, result.UploadPolicy)
	assert.NotNil(t, result.DownloadPolicy)
	assert.NotNil(t, result.DeletePolicy)
	assert.NotNil(t, result.BWList)

	// Verify default values
	assert.True(t, result.UploadPolicy.AutoUpload)
	assert.Equal(t, agentbay.UploadBeforeResourceRelease, result.UploadPolicy.UploadStrategy)

	assert.True(t, result.DownloadPolicy.AutoDownload)
	assert.Equal(t, agentbay.DownloadAsync, result.DownloadPolicy.DownloadStrategy)

	assert.True(t, result.DeletePolicy.SyncLocalFile)

	assert.Len(t, result.BWList.WhiteLists, 1)
	assert.Equal(t, "", result.BWList.WhiteLists[0].Path)
	assert.Empty(t, result.BWList.WhiteLists[0].ExcludePaths)
}

func TestSyncPolicyWithAllParameters(t *testing.T) {
	// Test SyncPolicy with all parameters
	uploadPolicy := &agentbay.UploadPolicy{
		AutoUpload:     false,
		UploadStrategy: agentbay.UploadBeforeResourceRelease,
	}
	downloadPolicy := &agentbay.DownloadPolicy{
		AutoDownload:     false,
		DownloadStrategy: agentbay.DownloadAsync,
	}
	deletePolicy := &agentbay.DeletePolicy{
		SyncLocalFile: false,
	}
	bwList := &agentbay.BWList{
		WhiteLists: []*agentbay.WhiteList{
			{
				Path:         "/test",
				ExcludePaths: []string{"/exclude"},
			},
		},
	}

	syncPolicy := &agentbay.SyncPolicy{
		UploadPolicy:   uploadPolicy,
		DownloadPolicy: downloadPolicy,
		DeletePolicy:   deletePolicy,
		BWList:         bwList,
	}

	// Marshal to JSON
	jsonData, err := json.Marshal(syncPolicy)
	assert.NoError(t, err, "Should marshal without error")

	// Unmarshal back to verify all fields are set correctly
	var result agentbay.SyncPolicy
	err = json.Unmarshal(jsonData, &result)
	assert.NoError(t, err, "Should unmarshal without error")

	// Verify all policies are set correctly
	assert.Equal(t, false, result.UploadPolicy.AutoUpload)

	assert.Equal(t, false, result.DownloadPolicy.AutoDownload)
	assert.Equal(t, false, result.DeletePolicy.SyncLocalFile)

	assert.Len(t, result.BWList.WhiteLists, 1)
	assert.Equal(t, "/test", result.BWList.WhiteLists[0].Path)
	assert.Equal(t, []string{"/exclude"}, result.BWList.WhiteLists[0].ExcludePaths)
}

func TestSyncPolicySerializationWithDefaults(t *testing.T) {
	// Test that SyncPolicy serializes correctly with all policies present
	syncPolicy := &agentbay.SyncPolicy{
		UploadPolicy: &agentbay.UploadPolicy{
			AutoUpload:     false,
			UploadStrategy: agentbay.UploadBeforeResourceRelease,
		},
	}

	// Serialize to JSON
	jsonData, err := json.Marshal(syncPolicy)
	assert.NoError(t, err, "Should marshal without error")

	// Parse JSON to verify structure
	var jsonMap map[string]interface{}
	err = json.Unmarshal(jsonData, &jsonMap)
	assert.NoError(t, err, "JSON should be unmarshallable")

	// Verify all policies are present in serialization
	assert.Contains(t, jsonMap, "uploadPolicy")
	assert.Contains(t, jsonMap, "downloadPolicy")
	assert.Contains(t, jsonMap, "deletePolicy")
	assert.Contains(t, jsonMap, "bwList")

	// Verify upload policy values
	uploadPolicyMap := jsonMap["uploadPolicy"].(map[string]interface{})
	assert.Equal(t, false, uploadPolicyMap["autoUpload"])
	assert.Equal(t, "UploadBeforeResourceRelease", uploadPolicyMap["uploadStrategy"])

	// Verify download policy values
	downloadPolicyMap := jsonMap["downloadPolicy"].(map[string]interface{})
	assert.Equal(t, true, downloadPolicyMap["autoDownload"])
	assert.Equal(t, "DownloadAsync", downloadPolicyMap["downloadStrategy"])

	// Verify delete policy values
	deletePolicyMap := jsonMap["deletePolicy"].(map[string]interface{})
	assert.Equal(t, true, deletePolicyMap["syncLocalFile"])

	// Verify bw list values
	bwListMap := jsonMap["bwList"].(map[string]interface{})
	whiteLists := bwListMap["whiteLists"].([]interface{})
	assert.Len(t, whiteLists, 1)
	whiteListMap := whiteLists[0].(map[string]interface{})
	assert.Equal(t, "", whiteListMap["path"])
	if excludePaths, exists := whiteListMap["excludePaths"]; exists {
		excludePathsArray := excludePaths.([]interface{})
		assert.Empty(t, excludePathsArray)
	}
}
