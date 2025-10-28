package testutil

import (
	"encoding/json"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

// MockContextManager implements a mock version of the context manager for testing
type MockContextManager struct {
	SessionID string
	// Add customizable response data for testing different scenarios
	InfoResponse *agentbay.ContextInfoResult
	SyncResponse *agentbay.ContextSyncResult
	InfoError    error
	SyncError    error
	// Store raw JSON for testing
	RawContextStatusJSON string
}

// Info returns mock context info
func (m *MockContextManager) Info() (*agentbay.ContextInfoResult, error) {
	if m.InfoError != nil {
		return nil, m.InfoError
	}

	if m.InfoResponse != nil {
		return m.InfoResponse, nil
	}

	return &agentbay.ContextInfoResult{
		ApiResponse: models.ApiResponse{
			RequestID: "mock-request-id-info",
		},
		ContextStatusData: []agentbay.ContextStatusData{
			{
				ContextId:    "mock-context-id",
				Path:         "/mock/path",
				ErrorMessage: "",
				Status:       "Success",
				StartTime:    1600000000,
				FinishTime:   1600000100,
				TaskType:     "download",
			},
		},
	}, nil
}

// InfoWithParams returns mock context info with parameters
func (m *MockContextManager) InfoWithParams(contextId, path, taskType string) (*agentbay.ContextInfoResult, error) {
	if m.InfoError != nil {
		return nil, m.InfoError
	}

	if m.InfoResponse != nil {
		// If custom response is set, filter it based on the parameters
		if m.InfoResponse.ContextStatusData != nil && len(m.InfoResponse.ContextStatusData) > 0 {
			filteredData := []agentbay.ContextStatusData{}

			for _, data := range m.InfoResponse.ContextStatusData {
				matches := true

				if contextId != "" && data.ContextId != contextId {
					matches = false
				}

				if path != "" && data.Path != path {
					matches = false
				}

				if taskType != "" && data.TaskType != taskType {
					matches = false
				}

				if matches {
					filteredData = append(filteredData, data)
				}
			}

			return &agentbay.ContextInfoResult{
				ApiResponse:       m.InfoResponse.ApiResponse,
				ContextStatusData: filteredData,
			}, nil
		}

		return m.InfoResponse, nil
	}

	// Default mock response
	return &agentbay.ContextInfoResult{
		ApiResponse: models.ApiResponse{
			RequestID: "mock-request-id-info-params",
		},
		ContextStatusData: []agentbay.ContextStatusData{
			{
				ContextId:    contextId,
				Path:         path,
				ErrorMessage: "",
				Status:       "Success",
				StartTime:    1600000000,
				FinishTime:   1600000100,
				TaskType:     taskType,
			},
		},
	}, nil
}

// Sync returns a mock sync result
func (m *MockContextManager) Sync() (*agentbay.ContextSyncResult, error) {
	if m.SyncError != nil {
		return nil, m.SyncError
	}

	if m.SyncResponse != nil {
		return m.SyncResponse, nil
	}

	return &agentbay.ContextSyncResult{
		ApiResponse: models.ApiResponse{
			RequestID: "mock-request-id-sync",
		},
		Success: true,
	}, nil
}

// SyncWithParams returns a mock sync result with parameters
func (m *MockContextManager) SyncWithParams(contextId, path, mode string) (*agentbay.ContextSyncResult, error) {
	if m.SyncError != nil {
		return nil, m.SyncError
	}

	if m.SyncResponse != nil {
		return m.SyncResponse, nil
	}

	return &agentbay.ContextSyncResult{
		ApiResponse: models.ApiResponse{
			RequestID: "mock-request-id-sync-params",
		},
		Success: true,
	}, nil
}

// MockSession implements a mock version of the Session for testing
type MockSession struct {
	SessionID string
	Context   *MockContextManager
}

// NewMockSession creates a new mock session for testing
func NewMockSession() *MockSession {
	sessionID := "mock-session-id"
	return &MockSession{
		SessionID: sessionID,
		Context:   &MockContextManager{SessionID: sessionID},
	}
}

// NewMockSessionWithComplexContextStatus creates a mock session with complex nested context status data
func NewMockSessionWithComplexContextStatus() *MockSession {
	sessionID := "mock-session-id"

	// Create nested JSON structure similar to what the API returns
	contextStatusItems := []map[string]interface{}{
		{
			"type": "data",
			"data": "[{\"contextId\":\"ctx-123\",\"path\":\"/home/user1\",\"status\":\"Success\",\"startTime\":1600000000,\"finishTime\":1600000100,\"taskType\":\"download\"},{\"contextId\":\"ctx-456\",\"path\":\"/home/user2\",\"status\":\"Failed\",\"errorMessage\":\"Some error\",\"startTime\":1600000200,\"finishTime\":1600000300,\"taskType\":\"upload\"}]",
		},
		{
			"type": "log",
			"data": "Some log data",
		},
	}

	contextStatusJSON, _ := json.Marshal(contextStatusItems)

	// Create the expected parsed result
	expectedData := []agentbay.ContextStatusData{
		{
			ContextId:  "ctx-123",
			Path:       "/home/user1",
			Status:     "Success",
			StartTime:  1600000000,
			FinishTime: 1600000100,
			TaskType:   "download",
		},
		{
			ContextId:    "ctx-456",
			Path:         "/home/user2",
			Status:       "Failed",
			ErrorMessage: "Some error",
			StartTime:    1600000200,
			FinishTime:   1600000300,
			TaskType:     "upload",
		},
	}

	mockContextManager := &MockContextManager{
		SessionID: sessionID,
		InfoResponse: &agentbay.ContextInfoResult{
			ApiResponse: models.ApiResponse{
				RequestID: "mock-request-id-complex",
			},
			ContextStatusData: expectedData,
		},
		RawContextStatusJSON: string(contextStatusJSON),
	}

	return &MockSession{
		SessionID: sessionID,
		Context:   mockContextManager,
	}
}

// GetSessionId returns the session ID
func (m *MockSession) GetSessionId() string {
	return m.SessionID
}

// GetAPIKey returns a mock API key
func (m *MockSession) GetAPIKey() string {
	return "mock-api-key"
}

// GetClient returns a mock client
func (m *MockSession) GetClient() interface{} {
	return nil
}
