package agentbay_test

import (
	"encoding/json"
	"errors"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/unit/mock"
	"github.com/golang/mock/gomock"
	"github.com/stretchr/testify/assert"
)

func TestSession_GetAPIKey_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Set expected behavior
	mockSession.EXPECT().GetAPIKey().Return("test_api_key")

	// Test GetAPIKey method call
	result := mockSession.GetAPIKey()

	// Verify call success
	assert.Equal(t, "test_api_key", result)
}

func TestSession_GetClient_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Set expected behavior
	expectedClient := &client.Client{}
	mockSession.EXPECT().GetClient().Return(expectedClient)

	// Test GetClient method call
	result := mockSession.GetClient()

	// Verify call success
	assert.NotNil(t, result)
	assert.Equal(t, expectedClient, result)
}

func TestSession_GetSessionId_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Set expected behavior
	mockSession.EXPECT().GetSessionId().Return("test_session_id")

	// Test GetSessionId method call
	result := mockSession.GetSessionId()

	// Verify call success
	assert.Equal(t, "test_session_id", result)
}

func TestSession_Delete_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Set expected behavior
	expectedResult := &agentbay.DeleteResult{
		Success: true,
	}
	mockSession.EXPECT().Delete().Return(expectedResult, nil)

	// Test Delete method call
	result, err := mockSession.Delete()

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.True(t, result.Success)
}

func TestSession_SetLabels_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Set expected behavior
	labels := map[string]string{"key1": "label1", "key2": "label2"}
	expectedResult := &agentbay.LabelResult{
		Labels: "label1,label2",
	}
	mockSession.EXPECT().SetLabels(labels).Return(expectedResult, nil)

	// Test SetLabels method call
	result, err := mockSession.SetLabels(labels)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "label1,label2", result.Labels)
}

func TestSession_GetLabels_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Set expected behavior
	expectedResult := &agentbay.LabelResult{
		Labels: "existing_label",
	}
	mockSession.EXPECT().GetLabels().Return(expectedResult, nil)

	// Test GetLabels method call
	result, err := mockSession.GetLabels()

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "existing_label", result.Labels)
}

func TestSession_GetLink_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Set expected behavior with valid port in range [30100, 30199]
	protocolType := "https"
	port := int32(30150)
	expectedResult := &agentbay.LinkResult{
		Link: "https://example.com:30150",
	}
	mockSession.EXPECT().GetLink(&protocolType, &port).Return(expectedResult, nil)

	// Test GetLink method call
	result, err := mockSession.GetLink(&protocolType, &port)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "https://example.com:30150", result.Link)
}

func TestSession_GetLink_ValidPortRange_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Test cases for valid port range [30100, 30199]
	testCases := []struct {
		name         string
		protocolType string
		port         int32
		expectedLink string
	}{
		{
			name:         "MinValidPort",
			protocolType: "http",
			port:         30100,
			expectedLink: "http://example.com:30100",
		},
		{
			name:         "MaxValidPort",
			protocolType: "https",
			port:         30199,
			expectedLink: "https://example.com:30199",
		},
		{
			name:         "MidValidPort",
			protocolType: "wss",
			port:         30150,
			expectedLink: "wss://example.com:30150",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			// Set expected behavior
			expectedResult := &agentbay.LinkResult{
				Link: tc.expectedLink,
			}
			mockSession.EXPECT().GetLink(&tc.protocolType, &tc.port).Return(expectedResult, nil)

			// Test GetLink method call
			result, err := mockSession.GetLink(&tc.protocolType, &tc.port)

			// Verify call success
			assert.NoError(t, err)
			assert.NotNil(t, result)
			assert.Equal(t, tc.expectedLink, result.Link)
		})
	}
}

func TestSession_GetLink_InvalidPortRange_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Test cases for invalid port range (outside [30100, 30199])
	testCases := []struct {
		name         string
		protocolType string
		port         int32
		expectedErr  string
	}{
		{
			name:         "PortTooLow",
			protocolType: "http",
			port:         30099,
			expectedErr:  "invalid port value: 30099. Port must be an integer in the range [30100, 30199]",
		},
		{
			name:         "PortTooHigh",
			protocolType: "https",
			port:         30200,
			expectedErr:  "invalid port value: 30200. Port must be an integer in the range [30100, 30199]",
		},
		{
			name:         "CommonPort80",
			protocolType: "http",
			port:         80,
			expectedErr:  "invalid port value: 80. Port must be an integer in the range [30100, 30199]",
		},
		{
			name:         "CommonPort443",
			protocolType: "https",
			port:         443,
			expectedErr:  "invalid port value: 443. Port must be an integer in the range [30100, 30199]",
		},
		{
			name:         "CommonPort8080",
			protocolType: "http",
			port:         8080,
			expectedErr:  "invalid port value: 8080. Port must be an integer in the range [30100, 30199]",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			// Set expected behavior - return error for invalid port
			expectedErr := errors.New(tc.expectedErr)
			mockSession.EXPECT().GetLink(&tc.protocolType, &tc.port).Return(nil, expectedErr)

			// Test GetLink method call
			result, err := mockSession.GetLink(&tc.protocolType, &tc.port)

			// Verify error handling
			assert.Error(t, err)
			assert.Nil(t, result)
			assert.Equal(t, tc.expectedErr, err.Error())
		})
	}
}

func TestSession_GetLink_NilPort_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Test with nil port (should be valid)
	protocolType := "https"
	expectedResult := &agentbay.LinkResult{
		Link: "https://example.com",
	}
	mockSession.EXPECT().GetLink(&protocolType, nil).Return(expectedResult, nil)

	// Test GetLink method call
	result, err := mockSession.GetLink(&protocolType, nil)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "https://example.com", result.Link)
}

func TestSession_Info_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Set expected behavior
	expectedResult := &agentbay.InfoResult{
		Info: &agentbay.SessionInfo{
			SessionId:   "test_session_id",
			ResourceUrl: "http://example.com",
		},
	}
	mockSession.EXPECT().Info().Return(expectedResult, nil)

	// Test Info method call
	result, err := mockSession.Info()

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "test_session_id", result.Info.SessionId)
	assert.Equal(t, "http://example.com", result.Info.ResourceUrl)
}

func TestSession_Error_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Set expected behavior - return error
	mockSession.EXPECT().Delete().Return(nil, assert.AnError)

	// Test error case
	result, err := mockSession.Delete()

	// Verify error handling
	assert.Error(t, err)
	assert.Nil(t, result)
}

func TestSession_Delete_APIFailure_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Set expected behavior - return failure response
	expectedResult := &agentbay.DeleteResult{
		Success: false,
	}
	mockSession.EXPECT().Delete().Return(expectedResult, nil)

	// Test Delete method call
	result, err := mockSession.Delete()

	// Verify call success but with failure result
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.False(t, result.Success)
}

func TestSession_SetLabels_APIError_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Set expected behavior - return error
	labels := map[string]string{"key1": "value1"}
	mockSession.EXPECT().SetLabels(labels).Return(nil, assert.AnError)

	// Test error case
	result, err := mockSession.SetLabels(labels)

	// Verify error handling
	assert.Error(t, err)
	assert.Nil(t, result)
}

func TestSession_GetLabels_APIError_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Set expected behavior - return error
	mockSession.EXPECT().GetLabels().Return(nil, assert.AnError)

	// Test error case
	result, err := mockSession.GetLabels()

	// Verify error handling
	assert.Error(t, err)
	assert.Nil(t, result)
}

func TestSession_GetLink_APIError_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Set expected behavior - return error
	protocolType := "http"
	port := int32(8080)
	mockSession.EXPECT().GetLink(&protocolType, &port).Return(nil, assert.AnError)

	// Test error case
	result, err := mockSession.GetLink(&protocolType, &port)

	// Verify error handling
	assert.Error(t, err)
	assert.Nil(t, result)
}

func TestSession_Info_APIError_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Set expected behavior - return error
	mockSession.EXPECT().Info().Return(nil, assert.AnError)

	// Test error case
	result, err := mockSession.Info()

	// Verify error handling
	assert.Error(t, err)
	assert.Nil(t, result)
}

func TestSession_ListMcpTools_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Session
	mockSession := mock.NewMockSessionInterface(ctrl)

	// Set expected behavior based on the actual API response from integration test
	tools := []agentbay.McpTool{
		{
			Name:        "get_resource",
			Description: "The command to retrieve  a wuying mcp runtime URL when user wants to get access to this runtime. Each retrieved URL will expire after a single use",
			InputSchema: map[string]interface{}{
				"type":       "object",
				"properties": map[string]interface{}{},
				"required":   []interface{}{},
			},
			Server: "mcp-server",
			Tool:   "get_resource",
		},
		{
			Name:        "system_screenshot",
			Description: "Captures a full-screen screenshot of the current display and returns a shareable URL. The screenshot is automatically processed and stored securely. The generated URL will expire after 64 minutes for security purposes.",
			InputSchema: map[string]interface{}{
				"type":       "object",
				"properties": map[string]interface{}{},
				"required":   []interface{}{},
			},
			Server: "mcp-server",
			Tool:   "system_screenshot",
		},
	}
	expectedResult := &agentbay.McpToolsResult{
		Tools: tools,
	}
	expectedResult.RequestID = "test-request-id"

	mockSession.EXPECT().ListMcpTools().Return(expectedResult, nil)

	// Test ListMcpTools method call
	result, err := mockSession.ListMcpTools()

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "test-request-id", result.RequestID)
	assert.Len(t, result.Tools, 2)
	assert.Equal(t, "get_resource", result.Tools[0].Name)
	assert.Equal(t, "The command to retrieve  a wuying mcp runtime URL when user wants to get access to this runtime. Each retrieved URL will expire after a single use", result.Tools[0].Description)
	assert.Equal(t, "mcp-server", result.Tools[0].Server)
	assert.Equal(t, "get_resource", result.Tools[0].Tool)
	assert.Equal(t, "system_screenshot", result.Tools[1].Name)
	assert.Equal(t, "Captures a full-screen screenshot of the current display and returns a shareable URL. The screenshot is automatically processed and stored securely. The generated URL will expire after 64 minutes for security purposes.", result.Tools[1].Description)
	assert.Equal(t, "mcp-server", result.Tools[1].Server)
	assert.Equal(t, "system_screenshot", result.Tools[1].Tool)
}

// Models related tests
func TestModels_AppManagerRule_Creation(t *testing.T) {
	// Test app manager rule creation
	appRule := &models.AppManagerRule{
		RuleType: "White",
		AppPackageNameList: []string{
			"com.android.settings",
			"com.example.test.app",
		},
	}

	assert.Equal(t, "White", appRule.RuleType)
	assert.Equal(t, 2, len(appRule.AppPackageNameList))
}

func TestModels_MobileExtraConfig_Creation(t *testing.T) {
	appRule := &models.AppManagerRule{
		RuleType:           "White",
		AppPackageNameList: []string{"com.example.app"},
	}

	mobileConfig := &models.MobileExtraConfig{
		LockResolution: true,
		AppManagerRule: appRule,
	}

	assert.True(t, mobileConfig.LockResolution)
	assert.NotNil(t, mobileConfig.AppManagerRule)
	assert.Equal(t, "White", mobileConfig.AppManagerRule.RuleType)
}

func TestModels_ExtraConfigs_ToJSON(t *testing.T) {
	// Test with nil ExtraConfigs
	var nilConfigs *models.ExtraConfigs
	jsonStr, err := nilConfigs.ToJSON()
	assert.NoError(t, err)
	assert.Equal(t, "", jsonStr)

	// Test with mobile configuration
	appRule := &models.AppManagerRule{
		RuleType: "White",
		AppPackageNameList: []string{
			"com.android.settings",
			"com.example.app",
		},
	}
	mobileConfig := &models.MobileExtraConfig{
		LockResolution: true,
		AppManagerRule: appRule,
	}
	extraConfigs := &models.ExtraConfigs{
		Mobile: mobileConfig,
	}

	jsonStr, err = extraConfigs.ToJSON()
	assert.NoError(t, err)
	assert.NotEmpty(t, jsonStr)

	// Verify JSON structure
	var parsed map[string]interface{}
	err = json.Unmarshal([]byte(jsonStr), &parsed)
	assert.NoError(t, err)

	mobile, exists := parsed["mobile"]
	assert.True(t, exists)

	mobileMap, ok := mobile.(map[string]interface{})
	assert.True(t, ok)

	lockResolution, exists := mobileMap["lock_resolution"]
	assert.True(t, exists)
	assert.Equal(t, true, lockResolution)
}

func TestModels_ExtraConfigs_FromJSON(t *testing.T) {
	jsonStr := `{
		"mobile": {
			"lock_resolution": true,
			"app_manager_rule": {
				"rule_type": "White",
				"app_package_name_list": ["com.android.settings", "com.example.app"]
			}
		}
	}`

	extraConfigs := &models.ExtraConfigs{}
	err := extraConfigs.FromJSON(jsonStr)
	assert.NoError(t, err)

	assert.NotNil(t, extraConfigs.Mobile)
	assert.True(t, extraConfigs.Mobile.LockResolution)
	assert.NotNil(t, extraConfigs.Mobile.AppManagerRule)
	assert.Equal(t, "White", extraConfigs.Mobile.AppManagerRule.RuleType)

	expectedPackages := []string{"com.android.settings", "com.example.app"}
	assert.Equal(t, len(expectedPackages), len(extraConfigs.Mobile.AppManagerRule.AppPackageNameList))

	// Test with empty JSON
	emptyConfigs := &models.ExtraConfigs{}
	err = emptyConfigs.FromJSON("")
	assert.NoError(t, err)
}

func TestModels_ExtraConfigs_JSONRoundTrip(t *testing.T) {
	// Create original configuration with lock resolution
	appRule := &models.AppManagerRule{
		RuleType:           "White",
		AppPackageNameList: []string{"com.android.settings", "com.example.app"},
	}
	mobileConfig := &models.MobileExtraConfig{
		LockResolution: true,
		AppManagerRule: appRule,
	}
	originalConfigs := &models.ExtraConfigs{
		Mobile: mobileConfig,
	}

	// Convert to JSON
	jsonStr, err := originalConfigs.ToJSON()
	assert.NoError(t, err)

	// Convert back from JSON
	newConfigs := &models.ExtraConfigs{}
	err = newConfigs.FromJSON(jsonStr)
	assert.NoError(t, err)

	// Verify the round trip preserved the data including lock resolution
	assert.NotNil(t, newConfigs.Mobile)
	assert.Equal(t, originalConfigs.Mobile.LockResolution, newConfigs.Mobile.LockResolution)
	assert.True(t, newConfigs.Mobile.LockResolution)
	assert.Equal(t, originalConfigs.Mobile.AppManagerRule.RuleType, newConfigs.Mobile.AppManagerRule.RuleType)
	assert.Equal(t, len(originalConfigs.Mobile.AppManagerRule.AppPackageNameList), len(newConfigs.Mobile.AppManagerRule.AppPackageNameList))
}
