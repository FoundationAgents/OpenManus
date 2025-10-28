package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/mobile"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/unit/mock"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

type MobileTestSuite struct {
	suite.Suite
	mockSession *mock.MockSessionForComputer
	mobile      *mobile.Mobile
}

func (suite *MobileTestSuite) SetupTest() {
	suite.mockSession = &mock.MockSessionForComputer{}
	suite.mobile = mobile.NewMobile(suite.mockSession)
}

func (suite *MobileTestSuite) TearDownTest() {
	suite.mockSession.AssertExpectations(suite.T())
}

// Test Tap functionality
func (suite *MobileTestSuite) TestTap_Success() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      true,
		RequestID:    "test-tap-123",
		ErrorMessage: "",
	}

	suite.mockSession.On("CallMcpTool", "tap", map[string]interface{}{
		"x": 100,
		"y": 200,
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.Tap(100, 200)

	// Assert
	assert.True(suite.T(), result.Success)
	assert.Equal(suite.T(), "test-tap-123", result.RequestID)
	assert.Empty(suite.T(), result.ErrorMessage)
}

func (suite *MobileTestSuite) TestTap_McpToolError() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      false,
		RequestID:    "test-tap-error",
		ErrorMessage: "Tap failed",
	}

	suite.mockSession.On("CallMcpTool", "tap", map[string]interface{}{
		"x": 100,
		"y": 200,
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.Tap(100, 200)

	// Assert
	assert.False(suite.T(), result.Success)
	assert.Equal(suite.T(), "test-tap-error", result.RequestID)
	assert.Equal(suite.T(), "Tap failed", result.ErrorMessage)
}

// Test Swipe functionality
func (suite *MobileTestSuite) TestSwipe_Success() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      true,
		RequestID:    "test-swipe-456",
		ErrorMessage: "",
	}

	suite.mockSession.On("CallMcpTool", "swipe", map[string]interface{}{
		"start_x":     100,
		"start_y":     200,
		"end_x":       300,
		"end_y":       400,
		"duration_ms": 500,
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.Swipe(100, 200, 300, 400, 500)

	// Assert
	assert.True(suite.T(), result.Success)
	assert.Equal(suite.T(), "test-swipe-456", result.RequestID)
}

func (suite *MobileTestSuite) TestSwipe_QuickSwipe() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      true,
		RequestID:    "test-swipe-quick",
		ErrorMessage: "",
	}

	suite.mockSession.On("CallMcpTool", "swipe", map[string]interface{}{
		"start_x":     50,
		"start_y":     100,
		"end_x":       150,
		"end_y":       100,
		"duration_ms": 200,
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.Swipe(50, 100, 150, 100, 200)

	// Assert
	assert.True(suite.T(), result.Success)
	assert.Equal(suite.T(), "test-swipe-quick", result.RequestID)
}

// Test InputText functionality
func (suite *MobileTestSuite) TestInputText_Success() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      true,
		RequestID:    "test-input-789",
		ErrorMessage: "",
	}

	suite.mockSession.On("CallMcpTool", "input_text", map[string]interface{}{
		"text": "Hello Mobile",
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.InputText("Hello Mobile")

	// Assert
	assert.True(suite.T(), result.Success)
	assert.Equal(suite.T(), "test-input-789", result.RequestID)
}

func (suite *MobileTestSuite) TestInputText_EmptyText() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      true,
		RequestID:    "test-input-empty",
		ErrorMessage: "",
	}

	suite.mockSession.On("CallMcpTool", "input_text", map[string]interface{}{
		"text": "",
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.InputText("")

	// Assert
	assert.True(suite.T(), result.Success)
	assert.Equal(suite.T(), "test-input-empty", result.RequestID)
}

// Test SendKey functionality
func (suite *MobileTestSuite) TestSendKey_BackKey() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      true,
		RequestID:    "test-key-back",
		ErrorMessage: "",
	}

	suite.mockSession.On("CallMcpTool", "send_key", map[string]interface{}{
		"key": 4, // BACK key
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.SendKey(4)

	// Assert
	assert.True(suite.T(), result.Success)
	assert.Equal(suite.T(), "test-key-back", result.RequestID)
}

func (suite *MobileTestSuite) TestSendKey_HomeKey() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      true,
		RequestID:    "test-key-home",
		ErrorMessage: "",
	}

	suite.mockSession.On("CallMcpTool", "send_key", map[string]interface{}{
		"key": 3, // HOME key
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.SendKey(3)

	// Assert
	assert.True(suite.T(), result.Success)
	assert.Equal(suite.T(), "test-key-home", result.RequestID)
}

// Test GetClickableUIElements functionality
func (suite *MobileTestSuite) TestGetClickableUIElements_Success() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      true,
		RequestID:    "test-elements-abc",
		Data:         `[{"text": "Button1", "bounds": {"left": 0, "top": 0, "right": 100, "bottom": 50}}, {"text": "Button2", "bounds": {"left": 0, "top": 60, "right": 100, "bottom": 110}}]`,
		ErrorMessage: "",
	}

	suite.mockSession.On("CallMcpTool", "get_clickable_ui_elements", map[string]interface{}{
		"timeout_ms": 2000,
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.GetClickableUIElements(2000)

	// Assert
	assert.Equal(suite.T(), "test-elements-abc", result.RequestID)
	assert.Len(suite.T(), result.Elements, 2)
	assert.Equal(suite.T(), "Button1", result.Elements[0].Text)
	assert.Equal(suite.T(), "Button2", result.Elements[1].Text)
	assert.Equal(suite.T(), 0, result.Elements[0].Bounds.Left)
	assert.Equal(suite.T(), 100, result.Elements[0].Bounds.Right)
}

func (suite *MobileTestSuite) TestGetClickableUIElements_InvalidJSON() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      true,
		RequestID:    "test-elements-invalid",
		Data:         `[{"text": "Button1", "bounds": invalid}]`,
		ErrorMessage: "",
	}

	suite.mockSession.On("CallMcpTool", "get_clickable_ui_elements", map[string]interface{}{
		"timeout_ms": 2000,
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.GetClickableUIElements(2000)

	// Assert
	assert.Equal(suite.T(), "test-elements-invalid", result.RequestID)
	assert.Contains(suite.T(), result.ErrorMessage, "failed to parse UI elements")
}

// Test GetAllUIElements functionality
func (suite *MobileTestSuite) TestGetAllUIElements_Success() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      true,
		RequestID:    "test-all-elements-def",
		Data:         `[{"text": "Label", "className": "TextView", "bounds": {"left": 0, "top": 0, "right": 200, "bottom": 30}}]`,
		ErrorMessage: "",
	}

	suite.mockSession.On("CallMcpTool", "get_all_ui_elements", map[string]interface{}{
		"timeout_ms": 3000,
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.GetAllUIElements(3000)

	// Assert
	assert.Equal(suite.T(), "test-all-elements-def", result.RequestID)
	assert.Len(suite.T(), result.Elements, 1)
	assert.Equal(suite.T(), "Label", result.Elements[0].Text)
	assert.Equal(suite.T(), "TextView", result.Elements[0].ClassName)
}

// Test GetInstalledApps functionality
func (suite *MobileTestSuite) TestGetInstalledApps_Success() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      true,
		RequestID:    "test-apps-ghi",
		Data:         `[{"name": "Calculator", "start_cmd": "com.android.calculator2"}, {"name": "Camera", "start_cmd": "com.android.camera"}]`,
		ErrorMessage: "",
	}

	suite.mockSession.On("CallMcpTool", "get_installed_apps", map[string]interface{}{
		"start_menu":         false,
		"desktop":            true,
		"ignore_system_apps": true,
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.GetInstalledApps(false, true, true)

	// Assert
	assert.Equal(suite.T(), "test-apps-ghi", result.RequestID)
	assert.Len(suite.T(), result.Apps, 2)
	assert.Equal(suite.T(), "Calculator", result.Apps[0].Name)
	assert.Equal(suite.T(), "com.android.calculator2", result.Apps[0].StartCmd)
	assert.Equal(suite.T(), "Camera", result.Apps[1].Name)
}

// Test StartApp functionality
func (suite *MobileTestSuite) TestStartApp_Success() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      true,
		RequestID:    "test-start-jkl",
		Data:         `[{"pname": "calculator", "pid": 1234}]`,
		ErrorMessage: "",
	}

	suite.mockSession.On("CallMcpTool", "start_app", map[string]interface{}{
		"start_cmd":      "com.android.calculator2",
		"work_directory": "",
		"activity":       ".MainActivity",
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.StartApp("com.android.calculator2", "", ".MainActivity")

	// Assert
	assert.Equal(suite.T(), "test-start-jkl", result.RequestID)
	assert.Len(suite.T(), result.Processes, 1)
	assert.Equal(suite.T(), "calculator", result.Processes[0].PName)
	assert.Equal(suite.T(), 1234, result.Processes[0].PID)
}

func (suite *MobileTestSuite) TestStartApp_WithWorkDirectory() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      true,
		RequestID:    "test-start-workdir",
		Data:         `[{"pname": "myapp", "pid": 5678}]`,
		ErrorMessage: "",
	}

	suite.mockSession.On("CallMcpTool", "start_app", map[string]interface{}{
		"start_cmd":      "com.example.myapp",
		"work_directory": "/data/app",
		"activity":       ".SplashActivity",
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.StartApp("com.example.myapp", "/data/app", ".SplashActivity")

	// Assert
	assert.Equal(suite.T(), "test-start-workdir", result.RequestID)
	assert.Len(suite.T(), result.Processes, 1)
	assert.Equal(suite.T(), "myapp", result.Processes[0].PName)
}

// Test StopAppByPName functionality
func (suite *MobileTestSuite) TestStopAppByPName_Success() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      true,
		RequestID:    "test-stop-mno",
		ErrorMessage: "",
	}

	suite.mockSession.On("CallMcpTool", "stop_app_by_pname", map[string]interface{}{
		"pname": "calculator",
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.StopAppByPName("calculator")

	// Assert
	assert.True(suite.T(), result.Success)
	assert.Equal(suite.T(), "test-stop-mno", result.RequestID)
}

func (suite *MobileTestSuite) TestStopAppByPName_AppNotFound() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      false,
		RequestID:    "test-stop-notfound",
		ErrorMessage: "App not found",
	}

	suite.mockSession.On("CallMcpTool", "stop_app_by_pname", map[string]interface{}{
		"pname": "nonexistent",
	}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.StopAppByPName("nonexistent")

	// Assert
	assert.False(suite.T(), result.Success)
	assert.Equal(suite.T(), "test-stop-notfound", result.RequestID)
	assert.Equal(suite.T(), "App not found", result.ErrorMessage)
}

// Test Screenshot functionality
func (suite *MobileTestSuite) TestScreenshot_Success() {
	// Arrange
	expectedResult := &models.McpToolResult{
		Success:      true,
		RequestID:    "test-screenshot-pqr",
		Data:         "https://example.com/mobile-screenshot.png",
		ErrorMessage: "",
	}

	suite.mockSession.On("CallMcpTool", "system_screenshot", map[string]interface{}{}).Return(expectedResult, nil)

	// Act
	result := suite.mobile.Screenshot()

	// Assert
	assert.Equal(suite.T(), "test-screenshot-pqr", result.RequestID)
	assert.Equal(suite.T(), "https://example.com/mobile-screenshot.png", result.Data)
	assert.Empty(suite.T(), result.ErrorMessage)
}

// Test comprehensive scenarios
func (suite *MobileTestSuite) TestCompleteUserFlow() {
	// This test simulates a complete user flow: tap -> input -> swipe -> screenshot

	// Step 1: Tap on input field
	suite.mockSession.On("CallMcpTool", "tap", map[string]interface{}{
		"x": 100,
		"y": 200,
	}).Return(&models.McpToolResult{
		Success:   true,
		RequestID: "flow-tap",
	}, nil)

	// Step 2: Input text
	suite.mockSession.On("CallMcpTool", "input_text", map[string]interface{}{
		"text": "Test Input",
	}).Return(&models.McpToolResult{
		Success:   true,
		RequestID: "flow-input",
	}, nil)

	// Step 3: Swipe to scroll
	suite.mockSession.On("CallMcpTool", "swipe", map[string]interface{}{
		"start_x":     100,
		"start_y":     400,
		"end_x":       100,
		"end_y":       200,
		"duration_ms": 300,
	}).Return(&models.McpToolResult{
		Success:   true,
		RequestID: "flow-swipe",
	}, nil)

	// Step 4: Take screenshot
	suite.mockSession.On("CallMcpTool", "system_screenshot", map[string]interface{}{}).Return(&models.McpToolResult{
		Success:   true,
		RequestID: "flow-screenshot",
		Data:      "https://example.com/flow-screenshot.png",
	}, nil)

	// Execute the flow
	tapResult := suite.mobile.Tap(100, 200)
	inputResult := suite.mobile.InputText("Test Input")
	swipeResult := suite.mobile.Swipe(100, 400, 100, 200, 300)
	screenshotResult := suite.mobile.Screenshot()

	// Assert all steps succeeded
	assert.True(suite.T(), tapResult.Success)
	assert.True(suite.T(), inputResult.Success)
	assert.True(suite.T(), swipeResult.Success)
	assert.Equal(suite.T(), "https://example.com/flow-screenshot.png", screenshotResult.Data)
}

// Run the test suite
func TestMobileTestSuite(t *testing.T) {
	suite.Run(t, new(MobileTestSuite))
}
