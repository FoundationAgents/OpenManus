package ui

import (
	"encoding/json"
	"fmt"

	mcp "github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/deprecation"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

// UIElement represents a UI element structure
type UIElement struct {
	Bounds      *UIBounds `json:"bounds,omitempty"`
	ClassName   string    `json:"className,omitempty"`
	ContentDesc string    `json:"contentDesc,omitempty"`
	ElementID   string    `json:"elementId,omitempty"`
	Package     string    `json:"package,omitempty"`
	ResourceID  string    `json:"resourceId,omitempty"`
	Text        string    `json:"text,omitempty"`
	Type        string    `json:"type,omitempty"`
}

// UIBounds represents the bounds of a UI element
type UIBounds struct {
	Bottom int `json:"bottom"`
	Left   int `json:"left"`
	Right  int `json:"right"`
	Top    int `json:"top"`
}

// UIElementsResult represents the result containing UI elements
type UIElementsResult struct {
	models.ApiResponse
	Elements []*UIElement
}

// KeyActionResult represents the result of a key action
type KeyActionResult struct {
	models.ApiResponse
	Success bool
}

// TextInputResult represents the result of a text input action
type TextInputResult struct {
	models.ApiResponse
	Text string
}

// SwipeResult represents the result of a swipe action
type SwipeResult struct {
	models.ApiResponse
	Success bool
}

// UIResult represents the result of a UI action
type UIResult struct {
	models.ApiResponse
	ComponentID string
	Success     bool
}

// ScreenshotResult represents the result of a screenshot operation
type ScreenshotResult struct {
	models.ApiResponse
	ScreenshotURL string
}

// UIActionResult represents the result of a UI action
type UIActionResult struct {
	models.ApiResponse
	Success bool
}

// SwipeDirection represents swipe directions
type SwipeDirection string

const (
	SwipeUp    SwipeDirection = "up"
	SwipeDown  SwipeDirection = "down"
	SwipeLeft  SwipeDirection = "left"
	SwipeRight SwipeDirection = "right"
)

// KeyCode represents Android UI key codes
type KeyCode int

// Common Android key codes
const (
	KEYCODE_UNKNOWN            KeyCode = 0
	KEYCODE_SOFT_LEFT          KeyCode = 1
	KEYCODE_SOFT_RIGHT         KeyCode = 2
	KEYCODE_HOME               KeyCode = 3
	KEYCODE_BACK               KeyCode = 4
	KEYCODE_CALL               KeyCode = 5
	KEYCODE_ENDCALL            KeyCode = 6
	KEYCODE_0                  KeyCode = 7
	KEYCODE_1                  KeyCode = 8
	KEYCODE_2                  KeyCode = 9
	KEYCODE_3                  KeyCode = 10
	KEYCODE_4                  KeyCode = 11
	KEYCODE_5                  KeyCode = 12
	KEYCODE_6                  KeyCode = 13
	KEYCODE_7                  KeyCode = 14
	KEYCODE_8                  KeyCode = 15
	KEYCODE_9                  KeyCode = 16
	KEYCODE_STAR               KeyCode = 17
	KEYCODE_POUND              KeyCode = 18
	KEYCODE_DPAD_UP            KeyCode = 19
	KEYCODE_DPAD_DOWN          KeyCode = 20
	KEYCODE_DPAD_LEFT          KeyCode = 21
	KEYCODE_DPAD_RIGHT         KeyCode = 22
	KEYCODE_DPAD_CENTER        KeyCode = 23
	KEYCODE_VOLUME_UP          KeyCode = 24
	KEYCODE_VOLUME_DOWN        KeyCode = 25
	KEYCODE_POWER              KeyCode = 26
	KEYCODE_CAMERA             KeyCode = 27
	KEYCODE_CLEAR              KeyCode = 28
	KEYCODE_A                  KeyCode = 29
	KEYCODE_B                  KeyCode = 30
	KEYCODE_C                  KeyCode = 31
	KEYCODE_D                  KeyCode = 32
	KEYCODE_E                  KeyCode = 33
	KEYCODE_F                  KeyCode = 34
	KEYCODE_G                  KeyCode = 35
	KEYCODE_H                  KeyCode = 36
	KEYCODE_I                  KeyCode = 37
	KEYCODE_J                  KeyCode = 38
	KEYCODE_K                  KeyCode = 39
	KEYCODE_L                  KeyCode = 40
	KEYCODE_M                  KeyCode = 41
	KEYCODE_N                  KeyCode = 42
	KEYCODE_O                  KeyCode = 43
	KEYCODE_P                  KeyCode = 44
	KEYCODE_Q                  KeyCode = 45
	KEYCODE_R                  KeyCode = 46
	KEYCODE_S                  KeyCode = 47
	KEYCODE_T                  KeyCode = 48
	KEYCODE_U                  KeyCode = 49
	KEYCODE_V                  KeyCode = 50
	KEYCODE_W                  KeyCode = 51
	KEYCODE_X                  KeyCode = 52
	KEYCODE_Y                  KeyCode = 53
	KEYCODE_Z                  KeyCode = 54
	KEYCODE_COMMA              KeyCode = 55
	KEYCODE_PERIOD             KeyCode = 56
	KEYCODE_ALT_LEFT           KeyCode = 57
	KEYCODE_ALT_RIGHT          KeyCode = 58
	KEYCODE_SHIFT_LEFT         KeyCode = 59
	KEYCODE_SHIFT_RIGHT        KeyCode = 60
	KEYCODE_TAB                KeyCode = 61
	KEYCODE_SPACE              KeyCode = 62
	KEYCODE_SYM                KeyCode = 63
	KEYCODE_EXPLORER           KeyCode = 64
	KEYCODE_ENVELOPE           KeyCode = 65
	KEYCODE_ENTER              KeyCode = 66
	KEYCODE_DEL                KeyCode = 67
	KEYCODE_GRAVE              KeyCode = 68
	KEYCODE_MINUS              KeyCode = 69
	KEYCODE_EQUALS             KeyCode = 70
	KEYCODE_LEFT_BRACKET       KeyCode = 71
	KEYCODE_RIGHT_BRACKET      KeyCode = 72
	KEYCODE_BACKSLASH          KeyCode = 73
	KEYCODE_SEMICOLON          KeyCode = 74
	KEYCODE_APOSTROPHE         KeyCode = 75
	KEYCODE_SLASH              KeyCode = 76
	KEYCODE_AT                 KeyCode = 77
	KEYCODE_NUM                KeyCode = 78
	KEYCODE_HEADSETHOOK        KeyCode = 79
	KEYCODE_FOCUS              KeyCode = 80
	KEYCODE_PLUS               KeyCode = 81
	KEYCODE_MENU               KeyCode = 82
	KEYCODE_NOTIFICATION       KeyCode = 83
	KEYCODE_SEARCH             KeyCode = 84
	KEYCODE_MEDIA_PLAY_PAUSE   KeyCode = 85
	KEYCODE_MEDIA_STOP         KeyCode = 86
	KEYCODE_MEDIA_NEXT         KeyCode = 87
	KEYCODE_MEDIA_PREVIOUS     KeyCode = 88
	KEYCODE_MEDIA_REWIND       KeyCode = 89
	KEYCODE_MEDIA_FAST_FORWARD KeyCode = 90
	KEYCODE_MUTE               KeyCode = 91
	KEYCODE_PAGE_UP            KeyCode = 92
	KEYCODE_PAGE_DOWN          KeyCode = 93
	KEYCODE_PICTSYMBOLS        KeyCode = 94
	KEYCODE_SWITCH_CHARSET     KeyCode = 95
	KEYCODE_BUTTON_A           KeyCode = 96
	KEYCODE_BUTTON_B           KeyCode = 97
	KEYCODE_BUTTON_C           KeyCode = 98
	KEYCODE_BUTTON_X           KeyCode = 99
	KEYCODE_BUTTON_Y           KeyCode = 100
	KEYCODE_BUTTON_Z           KeyCode = 101
	KEYCODE_BUTTON_L1          KeyCode = 102
	KEYCODE_BUTTON_R1          KeyCode = 103
	KEYCODE_BUTTON_L2          KeyCode = 104
	KEYCODE_BUTTON_R2          KeyCode = 105
	KEYCODE_BUTTON_THUMBL      KeyCode = 106
	KEYCODE_BUTTON_THUMBR      KeyCode = 107
	KEYCODE_BUTTON_START       KeyCode = 108
	KEYCODE_BUTTON_SELECT      KeyCode = 109
	KEYCODE_BUTTON_MODE        KeyCode = 110
)

// UIManager manages UI interactions with the session environment
type UIManager struct {
	Session interface {
		GetAPIKey() string
		GetClient() *mcp.Client
		GetSessionId() string
		IsVpc() bool
		NetworkInterfaceIp() string
		HttpPort() string
		FindServerForTool(toolName string) string
		CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error)
	}
}

// NewUI creates a new UI object
func NewUI(session interface {
	GetAPIKey() string
	GetClient() *mcp.Client
	GetSessionId() string
	IsVpc() bool
	NetworkInterfaceIp() string
	HttpPort() string
	FindServerForTool(toolName string) string
	CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error)
}) *UIManager {
	return &UIManager{
		Session: session,
	}
}

// GetClickableUIElements retrieves all clickable UI elements
// Deprecated: UI operations have been moved to platform-specific modules. Use session.Mobile.GetClickableUIElements() instead.
func (u *UIManager) GetClickableUIElements(timeoutMs int) (*UIElementsResult, error) {
	defer deprecation.DeprecatedMethod("UIManager.GetClickableUIElements", "UI operations have been moved to platform-specific modules", "session.Mobile.GetClickableUIElements()", "2.0.0")()
	if timeoutMs <= 0 {
		timeoutMs = 2000 // Default timeout
	}

	args := map[string]interface{}{
		"timeout_ms": timeoutMs,
	}

	result, err := u.Session.CallMcpTool("get_clickable_ui_elements", args)
	if err != nil {
		return nil, fmt.Errorf("failed to get clickable UI elements: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("failed to get clickable UI elements: %s", result.ErrorMessage)
	}

	// Parse the JSON string into a slice of UIElement structs
	var elements []*UIElement
	if err := json.Unmarshal([]byte(result.Data), &elements); err != nil {
		return nil, fmt.Errorf("failed to parse UI elements: %w", err)
	}

	return &UIElementsResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Elements: elements,
	}, nil
}

// GetAllUIElements retrieves all UI elements regardless of their clickable status
// Deprecated: UI operations have been moved to platform-specific modules. Use session.Mobile.GetAllUIElements() instead.
func (u *UIManager) GetAllUIElements(timeoutMs int) (*UIElementsResult, error) {
	defer deprecation.DeprecatedMethod("UIManager.GetAllUIElements", "UI operations have been moved to platform-specific modules", "session.Mobile.GetAllUIElements()", "2.0.0")()
	if timeoutMs <= 0 {
		timeoutMs = 5000 // Default timeout
	}

	args := map[string]interface{}{
		"timeout_ms": timeoutMs,
	}

	result, err := u.Session.CallMcpTool("get_all_ui_elements", args)
	if err != nil {
		return nil, fmt.Errorf("failed to get all UI elements: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("failed to get all UI elements: %s", result.ErrorMessage)
	}

	// Parse the JSON string into a slice of UIElement structs
	var elements []*UIElement
	if err := json.Unmarshal([]byte(result.Data), &elements); err != nil {
		return nil, fmt.Errorf("failed to parse UI elements: %w", err)
	}

	return &UIElementsResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Elements: elements,
	}, nil
}

// SendKey sends a key event to the UI (original interface)
// Deprecated: UI operations have been moved to platform-specific modules. Use session.Mobile.SendKey() instead.
func (u *UIManager) SendKey(key int) (*KeyActionResult, error) {
	defer deprecation.DeprecatedMethod("UIManager.SendKey", "UI operations have been moved to platform-specific modules", "session.Mobile.SendKey()", "2.0.0")()
	args := map[string]interface{}{
		"key": key,
	}

	result, err := u.Session.CallMcpTool("send_key", args)
	if err != nil {
		return nil, fmt.Errorf("failed to send key: %w", err)
	}

	return &KeyActionResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: result.Success,
	}, nil
}

// InputText inputs text into the currently focused UI element (original interface)
// Deprecated: UI operations have been moved to platform-specific modules. Use session.Computer.InputText() or session.Mobile.InputText() instead.
func (u *UIManager) InputText(text string) (*TextInputResult, error) {
	defer deprecation.DeprecatedMethod("UIManager.InputText", "UI operations have been moved to platform-specific modules", "session.Computer.InputText() or session.Mobile.InputText()", "2.0.0")()
	args := map[string]interface{}{
		"text": text,
	}

	result, err := u.Session.CallMcpTool("input_text", args)
	if err != nil {
		return nil, fmt.Errorf("failed to input text: %w", err)
	}

	return &TextInputResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Text: result.Data,
	}, nil
}

// Swipe performs a swipe gesture on the screen (original interface)
// Deprecated: UI operations have been moved to platform-specific modules. Use session.Mobile.Swipe() instead.
func (u *UIManager) Swipe(startX, startY, endX, endY, durationMs int) (*SwipeResult, error) {
	defer deprecation.DeprecatedMethod("UIManager.Swipe", "UI operations have been moved to platform-specific modules", "session.Mobile.Swipe()", "2.0.0")()
	if durationMs <= 0 {
		durationMs = 300 // Default duration in milliseconds
	}

	args := map[string]interface{}{
		"start_x":     startX,
		"start_y":     startY,
		"end_x":       endX,
		"end_y":       endY,
		"duration_ms": durationMs,
	}

	result, err := u.Session.CallMcpTool("swipe", args)
	if err != nil {
		return nil, fmt.Errorf("failed to swipe: %w", err)
	}

	return &SwipeResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: result.Success,
	}, nil
}

// Click performs a click action on the screen (original interface)
// Deprecated: UI operations have been moved to platform-specific modules. Use session.Computer.ClickMouse() or session.Mobile.Tap() instead.
func (u *UIManager) Click(x, y int, button string) (*UIResult, error) {
	defer deprecation.DeprecatedMethod("UIManager.Click", "UI operations have been moved to platform-specific modules", "session.Computer.ClickMouse() or session.Mobile.Tap()", "2.0.0")()
	if button == "" {
		button = "left" // Default button
	}

	args := map[string]interface{}{
		"x":      x,
		"y":      y,
		"button": button,
	}

	result, err := u.Session.CallMcpTool("click", args)
	if err != nil {
		return nil, fmt.Errorf("failed to click: %w", err)
	}

	return &UIResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		ComponentID: result.Data,
		Success:     result.Success,
	}, nil
}

// Screenshot captures a screenshot of the current screen (original interface)
// Deprecated: UI operations have been moved to platform-specific modules. Use session.Computer.Screenshot() or session.Mobile.Screenshot() instead.
func (u *UIManager) Screenshot() (*UIResult, error) {
	defer deprecation.DeprecatedMethod("UIManager.Screenshot", "UI operations have been moved to platform-specific modules", "session.Computer.Screenshot() or session.Mobile.Screenshot()", "2.0.0")()
	result, err := u.Session.CallMcpTool("system_screenshot", nil)
	if err != nil {
		return nil, fmt.Errorf("failed to take screenshot: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("failed to take screenshot: %s", result.ErrorMessage)
	}

	return &UIResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		ComponentID: result.Data,
		Success:     true,
	}, nil
}
