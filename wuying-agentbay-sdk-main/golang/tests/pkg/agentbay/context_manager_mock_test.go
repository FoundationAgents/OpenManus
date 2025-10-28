package agentbay_test

import (
	"errors"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
	"github.com/stretchr/testify/assert"
)

// TestContextManagerWithMockSession tests the context manager with a mock session
func TestContextManagerWithMockSession(t *testing.T) {
	// Create a mock session
	session := testutil.NewMockSession()

	// Test Info method
	t.Run("Info", func(t *testing.T) {
		result, err := session.Context.Info()

		assert.NoError(t, err)
		assert.NotNil(t, result)
		assert.Equal(t, "mock-request-id-info", result.RequestID)
		assert.Len(t, result.ContextStatusData, 1)
		assert.Equal(t, "mock-context-id", result.ContextStatusData[0].ContextId)
		assert.Equal(t, "/mock/path", result.ContextStatusData[0].Path)
		assert.Equal(t, "Success", result.ContextStatusData[0].Status)
		assert.Equal(t, int64(1600000000), result.ContextStatusData[0].StartTime)
		assert.Equal(t, int64(1600000100), result.ContextStatusData[0].FinishTime)
		assert.Equal(t, "download", result.ContextStatusData[0].TaskType)
	})

	// Test Sync method
	t.Run("Sync", func(t *testing.T) {
		result, err := session.Context.Sync()

		assert.NoError(t, err)
		assert.NotNil(t, result)
		assert.Equal(t, "mock-request-id-sync", result.RequestID)
		assert.True(t, result.Success)
	})
}

// TestContextManagerWithCustomMockResponses tests the context manager with custom mock responses
func TestContextManagerWithCustomMockResponses(t *testing.T) {
	// Create a mock session
	session := testutil.NewMockSession()

	// Test Info with custom response
	t.Run("InfoWithCustomResponse", func(t *testing.T) {
		// Set custom response
		session.Context.InfoResponse = &agentbay.ContextInfoResult{
			ApiResponse: models.ApiResponse{
				RequestID: "custom-request-id",
			},
			ContextStatusData: []agentbay.ContextStatusData{
				{
					ContextId:    "custom-context-id",
					Path:         "/custom/path",
					Status:       "Pending",
					ErrorMessage: "Custom error",
					StartTime:    1700000000,
					FinishTime:   1700000100,
					TaskType:     "custom",
				},
			},
		}

		result, err := session.Context.Info()

		assert.NoError(t, err)
		assert.NotNil(t, result)
		assert.Equal(t, "custom-request-id", result.RequestID)
		assert.Len(t, result.ContextStatusData, 1)
		assert.Equal(t, "custom-context-id", result.ContextStatusData[0].ContextId)
		assert.Equal(t, "/custom/path", result.ContextStatusData[0].Path)
		assert.Equal(t, "Pending", result.ContextStatusData[0].Status)
		assert.Equal(t, "Custom error", result.ContextStatusData[0].ErrorMessage)
		assert.Equal(t, int64(1700000000), result.ContextStatusData[0].StartTime)
		assert.Equal(t, int64(1700000100), result.ContextStatusData[0].FinishTime)
		assert.Equal(t, "custom", result.ContextStatusData[0].TaskType)
	})

	// Test Info with error
	t.Run("InfoWithError", func(t *testing.T) {
		// Set error
		expectedError := errors.New("mock info error")
		session.Context.InfoError = expectedError

		result, err := session.Context.Info()

		assert.Error(t, err)
		assert.Equal(t, expectedError, err)
		assert.Nil(t, result)

		// Reset error for next test
		session.Context.InfoError = nil
	})

	// Test Sync with custom response
	t.Run("SyncWithCustomResponse", func(t *testing.T) {
		// Set custom response
		session.Context.SyncResponse = &agentbay.ContextSyncResult{
			ApiResponse: models.ApiResponse{
				RequestID: "custom-sync-request-id",
			},
			Success: false,
		}

		result, err := session.Context.Sync()

		assert.NoError(t, err)
		assert.NotNil(t, result)
		assert.Equal(t, "custom-sync-request-id", result.RequestID)
		assert.False(t, result.Success)
	})

	// Test Sync with error
	t.Run("SyncWithError", func(t *testing.T) {
		// Set error
		expectedError := errors.New("mock sync error")
		session.Context.SyncError = expectedError

		result, err := session.Context.Sync()

		assert.Error(t, err)
		assert.Equal(t, expectedError, err)
		assert.Nil(t, result)
	})
}

// TestContextManagerWithComplexContextStatus tests the context manager with complex context status
func TestContextManagerWithComplexContextStatus(t *testing.T) {
	// Create a mock session with complex context status
	session := testutil.NewMockSessionWithComplexContextStatus()

	// Test Info method
	t.Run("InfoWithComplexStatus", func(t *testing.T) {
		result, err := session.Context.Info()

		assert.NoError(t, err)
		assert.NotNil(t, result)
		assert.Equal(t, "mock-request-id-complex", result.RequestID)
		assert.Len(t, result.ContextStatusData, 2)

		// First context status
		assert.Equal(t, "ctx-123", result.ContextStatusData[0].ContextId)
		assert.Equal(t, "/home/user1", result.ContextStatusData[0].Path)
		assert.Equal(t, "Success", result.ContextStatusData[0].Status)
		assert.Empty(t, result.ContextStatusData[0].ErrorMessage)
		assert.Equal(t, int64(1600000000), result.ContextStatusData[0].StartTime)
		assert.Equal(t, int64(1600000100), result.ContextStatusData[0].FinishTime)
		assert.Equal(t, "download", result.ContextStatusData[0].TaskType)

		// Second context status
		assert.Equal(t, "ctx-456", result.ContextStatusData[1].ContextId)
		assert.Equal(t, "/home/user2", result.ContextStatusData[1].Path)
		assert.Equal(t, "Failed", result.ContextStatusData[1].Status)
		assert.Equal(t, "Some error", result.ContextStatusData[1].ErrorMessage)
		assert.Equal(t, int64(1600000200), result.ContextStatusData[1].StartTime)
		assert.Equal(t, int64(1600000300), result.ContextStatusData[1].FinishTime)
		assert.Equal(t, "upload", result.ContextStatusData[1].TaskType)
	})

	// Test InfoWithParams method with filtering
	t.Run("InfoWithParamsFiltering", func(t *testing.T) {
		// Filter by context ID
		result, err := session.Context.InfoWithParams("ctx-123", "", "")

		assert.NoError(t, err)
		assert.NotNil(t, result)
		assert.Len(t, result.ContextStatusData, 1)
		assert.Equal(t, "ctx-123", result.ContextStatusData[0].ContextId)

		// Filter by path
		result, err = session.Context.InfoWithParams("", "/home/user2", "")

		assert.NoError(t, err)
		assert.NotNil(t, result)
		assert.Len(t, result.ContextStatusData, 1)
		assert.Equal(t, "/home/user2", result.ContextStatusData[0].Path)

		// Filter by task type
		result, err = session.Context.InfoWithParams("", "", "upload")

		assert.NoError(t, err)
		assert.NotNil(t, result)
		assert.Len(t, result.ContextStatusData, 1)
		assert.Equal(t, "upload", result.ContextStatusData[0].TaskType)

		// Filter with multiple parameters
		result, err = session.Context.InfoWithParams("ctx-456", "/home/user2", "upload")

		assert.NoError(t, err)
		assert.NotNil(t, result)
		assert.Len(t, result.ContextStatusData, 1)
		assert.Equal(t, "ctx-456", result.ContextStatusData[0].ContextId)
		assert.Equal(t, "/home/user2", result.ContextStatusData[0].Path)
		assert.Equal(t, "upload", result.ContextStatusData[0].TaskType)

		// Filter with no matches
		result, err = session.Context.InfoWithParams("non-existent", "", "")

		assert.NoError(t, err)
		assert.NotNil(t, result)
		assert.Empty(t, result.ContextStatusData)
	})
}
