package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/ui"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/unit/mock"
	"github.com/golang/mock/gomock"
	"github.com/stretchr/testify/assert"
)

// TestUI_GetClickableUIElements_WithMockClient tests GetClickableUIElements with mock client
func TestUI_GetClickableUIElements_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock UI
	mockUI := mock.NewMockUIInterface(ctrl)

	// Set expected behavior
	expectedResult := &ui.UIElementsResult{
		Elements: []*ui.UIElement{
			{
				Bounds: &ui.UIBounds{
					Left:   48,
					Top:    90,
					Right:  1032,
					Bottom: 630,
				},
				ClassName: "LinearLayout",
				Text:      "Sample Button",
				Type:      "clickable",
			},
		},
	}
	mockUI.EXPECT().GetClickableUIElements(5000).Return(expectedResult, nil)

	// Test GetClickableUIElements method call
	result, err := mockUI.GetClickableUIElements(5000)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Len(t, result.Elements, 1)
	assert.Equal(t, "LinearLayout", result.Elements[0].ClassName)
	assert.Equal(t, "Sample Button", result.Elements[0].Text)
	assert.Equal(t, "clickable", result.Elements[0].Type)
}

// TestUI_SendKey_WithMockClient tests SendKey with mock client
func TestUI_SendKey_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock UI
	mockUI := mock.NewMockUIInterface(ctrl)

	// Set expected behavior
	expectedResult := &ui.KeyActionResult{
		Success: true,
	}
	mockUI.EXPECT().SendKey(int(ui.KEYCODE_HOME)).Return(expectedResult, nil)

	// Test SendKey method call
	result, err := mockUI.SendKey(int(ui.KEYCODE_HOME))

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.True(t, result.Success)
}

// TestUI_Swipe_WithMockClient tests Swipe with mock client
func TestUI_Swipe_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock UI
	mockUI := mock.NewMockUIInterface(ctrl)

	// Set expected behavior
	expectedResult := &ui.SwipeResult{
		Success: true,
	}
	mockUI.EXPECT().Swipe(100, 200, 300, 400, 500).Return(expectedResult, nil)

	// Test Swipe method call
	result, err := mockUI.Swipe(100, 200, 300, 400, 500)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.True(t, result.Success)
}

// TestUI_Click_WithMockClient tests Click with mock client
func TestUI_Click_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock UI
	mockUI := mock.NewMockUIInterface(ctrl)

	// Set expected behavior
	expectedResult := &ui.UIResult{
		Success: true,
	}
	mockUI.EXPECT().Click(150, 250, "left").Return(expectedResult, nil)

	// Test Click method call
	result, err := mockUI.Click(150, 250, "left")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.True(t, result.Success)
}

// TestUI_InputText_WithMockClient tests InputText with mock client
func TestUI_InputText_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock UI
	mockUI := mock.NewMockUIInterface(ctrl)

	inputText := "Hello, world!"
	// Set expected behavior
	expectedResult := &ui.TextInputResult{
		Text: inputText,
	}
	mockUI.EXPECT().InputText(inputText).Return(expectedResult, nil)

	// Test InputText method call
	result, err := mockUI.InputText(inputText)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, inputText, result.Text)
}

// TestUI_GetAllUIElements_WithMockClient tests GetAllUIElements with mock client
func TestUI_GetAllUIElements_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock UI
	mockUI := mock.NewMockUIInterface(ctrl)

	// Set expected behavior
	expectedResult := &ui.UIElementsResult{
		Elements: []*ui.UIElement{
			{
				Bounds: &ui.UIBounds{
					Left:   48,
					Top:    90,
					Right:  1032,
					Bottom: 630,
				},
				ClassName: "LinearLayout",
				Text:      "Sample Text",
				Type:      "UIElement",
			},
			{
				Bounds: &ui.UIBounds{
					Left:   100,
					Top:    200,
					Right:  300,
					Bottom: 400,
				},
				ClassName: "Button",
				Text:      "Click Me",
				Type:      "button",
			},
		},
	}
	mockUI.EXPECT().GetAllUIElements(5000).Return(expectedResult, nil)

	// Test GetAllUIElements method call
	result, err := mockUI.GetAllUIElements(5000)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Len(t, result.Elements, 2)
	assert.Equal(t, "LinearLayout", result.Elements[0].ClassName)
	assert.Equal(t, "Sample Text", result.Elements[0].Text)
	assert.Equal(t, "UIElement", result.Elements[0].Type)
	assert.Equal(t, "Button", result.Elements[1].ClassName)
	assert.Equal(t, "Click Me", result.Elements[1].Text)
	assert.Equal(t, "button", result.Elements[1].Type)
}

// TestUI_Error_WithMockClient tests error cases
func TestUI_Error_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock UI
	mockUI := mock.NewMockUIInterface(ctrl)

	// Set expected behavior - return error
	mockUI.EXPECT().GetClickableUIElements(5000).Return(nil, assert.AnError)

	// Test method call
	result, err := mockUI.GetClickableUIElements(5000)

	// Verify error handling
	assert.Error(t, err)
	assert.Nil(t, result)
}
