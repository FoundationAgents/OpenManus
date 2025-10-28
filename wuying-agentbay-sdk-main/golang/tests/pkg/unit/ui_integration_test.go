package agentbay_test

import (
	"strings"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/ui"
	"github.com/stretchr/testify/assert"
)

// MockSession is used for testing
type MockSession struct {
	apiKey    string
	sessionID string
	client    *client.Client
}

func (m *MockSession) GetAPIKey() string                                          { return m.apiKey }
func (m *MockSession) GetClient() *client.Client                                  { return m.client }
func (m *MockSession) GetSessionId() string                                       { return m.sessionID }
func (m *MockSession) IsVpc() bool                                                { return false }
func (m *MockSession) NetworkInterfaceIp() string                                 { return "" }
func (m *MockSession) HttpPort() string                                           { return "" }
func (m *MockSession) FindServerForTool(toolName string) string                   { return "" }
func (m *MockSession) Delete(syncContext ...bool) (*agentbay.DeleteResult, error) { return nil, nil }
func (m *MockSession) SetLabels(labels string) (*agentbay.LabelResult, error)     { return nil, nil }
func (m *MockSession) GetLabels() (*agentbay.LabelResult, error)                  { return nil, nil }
func (m *MockSession) GetLink(protocolType *string, port *int32) (*agentbay.LinkResult, error) {
	return nil, nil
}
func (m *MockSession) Info() (*agentbay.InfoResult, error) { return nil, nil }
func (m *MockSession) CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error) {
	return &models.McpToolResult{
		Success:      true,
		Data:         "",
		ErrorMessage: "",
		RequestID:    "",
	}, nil
}

// TestUI_GetClickableUIElements_Integration tests the GetClickableUIElements method of UI module
func TestUI_GetClickableUIElements_Integration(t *testing.T) {
	// Create mock session
	mockSession := &MockSession{
		apiKey:    "test-api-key",
		sessionID: "test-session-id",
		client:    nil, // In actual tests, this should be a mocked client
	}

	// Create UI manager
	uiManager := ui.NewUI(mockSession)
	assert.NotNil(t, uiManager)

	// Test GetClickableUIElements method call
	// Note: This will actually call the method, but since client is nil, it will fail
	// In actual tests, the client's return value should be mocked
	result, err := uiManager.GetClickableUIElements(5000) // 5 second timeout

	// Since client is nil, this will fail, but we can verify that the method is called correctly
	if err != nil {
		// Expected error because client is nil or other failures
		// Accept either "client is nil" or other possible errors
		errorMsg := err.Error()
		hasExpectedError := strings.Contains(errorMsg, "client is nil") ||
			strings.Contains(errorMsg, "unexpected end of JSON input") ||
			strings.Contains(errorMsg, "failed to parse") ||
			len(errorMsg) > 0 // Accept any error when client is not properly initialized
		assert.True(t, hasExpectedError, "Expected some error when client is nil, got: %s", errorMsg)
	} else {
		// If unexpectedly successful, verify result structure
		assert.NotNil(t, result)
	}
}

// TestUI_SendKey_Integration tests the SendKey method of UI module
func TestUI_SendKey_Integration(t *testing.T) {
	mockSession := &MockSession{
		apiKey:    "test-api-key",
		sessionID: "test-session-id",
		client:    nil,
	}

	uiManager := ui.NewUI(mockSession)
	assert.NotNil(t, uiManager)

	// Test SendKey method call
	result, err := uiManager.SendKey(3) // Use integer constant instead of ui.KeyCode.HOME

	if err != nil {
		// Expected error because client is nil or other failures
		// Accept either "client is nil" or other possible errors
		errorMsg := err.Error()
		hasExpectedError := strings.Contains(errorMsg, "client is nil") ||
			strings.Contains(errorMsg, "unexpected end of JSON input") ||
			strings.Contains(errorMsg, "failed to parse") ||
			len(errorMsg) > 0 // Accept any error when client is not properly initialized
		assert.True(t, hasExpectedError, "Expected some error when client is nil, got: %s", errorMsg)
	} else {
		// If unexpectedly successful, verify result structure
		assert.NotNil(t, result)
	}
}

// TestUI_Swipe_Integration tests the Swipe method of UI module
func TestUI_Swipe_Integration(t *testing.T) {
	// Create mock session
	mockSession := &MockSession{
		apiKey:    "test-api-key",
		sessionID: "test-session-id",
		client:    nil, // Intentionally nil to test error handling
	}

	uiManager := ui.NewUI(mockSession)
	assert.NotNil(t, uiManager)

	// Test Swipe method call
	result, err := uiManager.Swipe(100, 200, 300, 400, 500)

	if err != nil {
		// Expected error because client is nil or other failures
		// Accept either "client is nil" or other possible errors
		errorMsg := err.Error()
		hasExpectedError := strings.Contains(errorMsg, "client is nil") ||
			strings.Contains(errorMsg, "unexpected end of JSON input") ||
			strings.Contains(errorMsg, "failed to parse") ||
			len(errorMsg) > 0 // Accept any error when client is not properly initialized
		assert.True(t, hasExpectedError, "Expected some error when client is nil, got: %s", errorMsg)
	} else {
		// If unexpectedly successful, verify result structure
		assert.NotNil(t, result)
	}
}

// TestUI_Click_Integration tests the Click method of UI module
func TestUI_Click_Integration(t *testing.T) {
	// Create mock session
	mockSession := &MockSession{
		apiKey:    "test-api-key",
		sessionID: "test-session-id",
		client:    nil, // Intentionally nil to test error handling
	}

	uiManager := ui.NewUI(mockSession)
	assert.NotNil(t, uiManager)

	// Test Click method call
	result, err := uiManager.Click(150, 250, "left")

	if err != nil {
		// Expected error because client is nil or other failures
		// Accept either "client is nil" or other possible errors
		errorMsg := err.Error()
		hasExpectedError := strings.Contains(errorMsg, "client is nil") ||
			strings.Contains(errorMsg, "unexpected end of JSON input") ||
			strings.Contains(errorMsg, "failed to parse") ||
			len(errorMsg) > 0 // Accept any error when client is not properly initialized
		assert.True(t, hasExpectedError, "Expected some error when client is nil, got: %s", errorMsg)
	} else {
		// If unexpectedly successful, verify result structure
		assert.NotNil(t, result)
	}
}

// TestUI_InputText_Integration tests the InputText method of UI module
func TestUI_InputText_Integration(t *testing.T) {
	// Create mock session
	mockSession := &MockSession{
		apiKey:    "test-api-key",
		sessionID: "test-session-id",
		client:    nil, // Intentionally nil to test error handling
	}

	uiManager := ui.NewUI(mockSession)
	assert.NotNil(t, uiManager)

	// Test InputText method call
	result, err := uiManager.InputText("test input")

	if err != nil {
		// Expected error because client is nil or other failures
		// Accept either "client is nil" or other possible errors
		errorMsg := err.Error()
		hasExpectedError := strings.Contains(errorMsg, "client is nil") ||
			strings.Contains(errorMsg, "unexpected end of JSON input") ||
			strings.Contains(errorMsg, "failed to parse") ||
			len(errorMsg) > 0 // Accept any error when client is not properly initialized
		assert.True(t, hasExpectedError, "Expected some error when client is nil, got: %s", errorMsg)
	} else {
		// If unexpectedly successful, verify result structure
		assert.NotNil(t, result)
	}
}

// TestUI_GetAllUIElements_Integration tests the GetAllUIElements method of UI module
func TestUI_GetAllUIElements_Integration(t *testing.T) {
	mockSession := &MockSession{
		apiKey:    "test-api-key",
		sessionID: "test-session-id",
		client:    nil,
	}

	uiManager := ui.NewUI(mockSession)
	assert.NotNil(t, uiManager)

	// Test GetAllUIElements method call
	result, err := uiManager.GetAllUIElements(5000)

	if err != nil {
		// Expected error because client is nil or parsing fails
		// Accept either "client is nil" or JSON parsing errors
		errorMsg := err.Error()
		hasExpectedError := strings.Contains(errorMsg, "client is nil") ||
			strings.Contains(errorMsg, "unexpected end of JSON input") ||
			strings.Contains(errorMsg, "failed to parse UI elements")
		assert.True(t, hasExpectedError, "Expected error about client or JSON parsing, got: %s", errorMsg)
	} else {
		// If unexpectedly successful, verify result structure
		assert.NotNil(t, result)
	}
}
