package computer

import (
	"encoding/json"
	"fmt"

	mcp "github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/window"
)

// MouseButton represents mouse button types
type MouseButton string

const (
	MouseButtonLeft       MouseButton = "left"
	MouseButtonRight      MouseButton = "right"
	MouseButtonMiddle     MouseButton = "middle"
	MouseButtonDoubleLeft MouseButton = "double_left"
)

// ScrollDirection represents scroll directions
type ScrollDirection string

const (
	ScrollDirectionUp    ScrollDirection = "up"
	ScrollDirectionDown  ScrollDirection = "down"
	ScrollDirectionLeft  ScrollDirection = "left"
	ScrollDirectionRight ScrollDirection = "right"
)

// CursorPosition represents the cursor position on screen
type CursorPosition struct {
	models.ApiResponse
	X            int    `json:"x"`
	Y            int    `json:"y"`
	ErrorMessage string `json:"error_message"`
}

// ScreenSize represents the screen dimensions
type ScreenSize struct {
	models.ApiResponse
	Width            int     `json:"width"`
	Height           int     `json:"height"`
	DpiScalingFactor float64 `json:"dpiScalingFactor"`
	ErrorMessage     string  `json:"error_message"`
}

// ScreenshotResult represents the result of a screenshot operation
type ScreenshotResult struct {
	models.ApiResponse
	Data         string `json:"data"`
	ErrorMessage string `json:"error_message"`
}

// BoolResult represents a boolean operation result
type BoolResult struct {
	models.ApiResponse
	Success      bool   `json:"success"`
	ErrorMessage string `json:"error_message"`
}

// Computer handles computer UI automation operations in the AgentBay cloud environment.
// Provides comprehensive desktop automation capabilities including mouse, keyboard,
// window management, application management, and screen operations.
type Computer struct {
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

// NewComputer creates a new Computer instance
func NewComputer(session interface {
	GetAPIKey() string
	GetClient() *mcp.Client
	GetSessionId() string
	IsVpc() bool
	NetworkInterfaceIp() string
	HttpPort() string
	FindServerForTool(toolName string) string
	CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error)
}) *Computer {
	return &Computer{Session: session}
}

// ClickMouse clicks the mouse at the specified coordinates
func (c *Computer) ClickMouse(x, y int, button MouseButton) *BoolResult {
	// Validate button parameter
	validButtons := []MouseButton{MouseButtonLeft, MouseButtonRight, MouseButtonMiddle, MouseButtonDoubleLeft}
	isValid := false
	for _, validButton := range validButtons {
		if button == validButton {
			isValid = true
			break
		}
	}
	if !isValid {
		return &BoolResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			Success:      false,
			ErrorMessage: fmt.Sprintf("invalid button: %s. Valid options: %v", button, validButtons),
		}
	}

	args := map[string]interface{}{
		"x":      x,
		"y":      y,
		"button": string(button),
	}

	result, err := c.Session.CallMcpTool("click_mouse", args)
	if err != nil {
		return &BoolResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			Success:      false,
			ErrorMessage: fmt.Sprintf("failed to call click_mouse: %v", err),
		}
	}

	return &BoolResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success:      result.Success,
		ErrorMessage: result.ErrorMessage,
	}
}

// MoveMouse moves the mouse cursor to specific coordinates
func (c *Computer) MoveMouse(x, y int) *BoolResult {
	args := map[string]interface{}{
		"x": x,
		"y": y,
	}

	result, err := c.Session.CallMcpTool("move_mouse", args)
	if err != nil {
		return &BoolResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			Success:      false,
			ErrorMessage: fmt.Sprintf("failed to call move_mouse: %v", err),
		}
	}

	return &BoolResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success:      result.Success,
		ErrorMessage: result.ErrorMessage,
	}
}

// DragMouse drags the mouse from one point to another
func (c *Computer) DragMouse(fromX, fromY, toX, toY int, button MouseButton) *BoolResult {
	// Validate button parameter
	validButtons := []MouseButton{MouseButtonLeft, MouseButtonRight, MouseButtonMiddle}
	isValid := false
	for _, validButton := range validButtons {
		if button == validButton {
			isValid = true
			break
		}
	}
	if !isValid {
		return &BoolResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			Success:      false,
			ErrorMessage: fmt.Sprintf("invalid button: %s. Valid options: %v", button, validButtons),
		}
	}

	args := map[string]interface{}{
		"from_x": fromX,
		"from_y": fromY,
		"to_x":   toX,
		"to_y":   toY,
		"button": string(button),
	}

	result, err := c.Session.CallMcpTool("drag_mouse", args)
	if err != nil {
		return &BoolResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			Success:      false,
			ErrorMessage: fmt.Sprintf("failed to call drag_mouse: %v", err),
		}
	}

	return &BoolResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success:      result.Success,
		ErrorMessage: result.ErrorMessage,
	}
}

// Scroll scrolls the mouse wheel at specific coordinates
func (c *Computer) Scroll(x, y int, direction ScrollDirection, amount int) *BoolResult {
	// Validate direction parameter
	validDirections := []ScrollDirection{ScrollDirectionUp, ScrollDirectionDown, ScrollDirectionLeft, ScrollDirectionRight}
	isValid := false
	for _, validDirection := range validDirections {
		if direction == validDirection {
			isValid = true
			break
		}
	}
	if !isValid {
		return &BoolResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			Success:      false,
			ErrorMessage: fmt.Sprintf("invalid direction: %s. Valid options: %v", direction, validDirections),
		}
	}

	args := map[string]interface{}{
		"x":         x,
		"y":         y,
		"direction": string(direction),
		"amount":    amount,
	}

	result, err := c.Session.CallMcpTool("scroll", args)
	if err != nil {
		return &BoolResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			Success:      false,
			ErrorMessage: fmt.Sprintf("failed to call scroll: %v", err),
		}
	}

	return &BoolResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success:      result.Success,
		ErrorMessage: result.ErrorMessage,
	}
}

// GetCursorPosition gets the current cursor position
func (c *Computer) GetCursorPosition() *CursorPosition {
	args := map[string]interface{}{}

	result, err := c.Session.CallMcpTool("get_cursor_position", args)
	if err != nil {
		return &CursorPosition{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			ErrorMessage: fmt.Sprintf("failed to call get_cursor_position: %v", err),
		}
	}

	if !result.Success {
		return &CursorPosition{
			ApiResponse: models.ApiResponse{
				RequestID: result.RequestID,
			},
			ErrorMessage: result.ErrorMessage,
		}
	}

	// Parse cursor position from JSON
	var position struct {
		X int `json:"x"`
		Y int `json:"y"`
	}
	if err := json.Unmarshal([]byte(result.Data), &position); err != nil {
		return &CursorPosition{
			ApiResponse: models.ApiResponse{
				RequestID: result.RequestID,
			},
			ErrorMessage: fmt.Sprintf("failed to parse cursor position: %v", err),
		}
	}

	return &CursorPosition{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		X:            position.X,
		Y:            position.Y,
		ErrorMessage: result.ErrorMessage,
	}
}

// InputText inputs text into the active field
func (c *Computer) InputText(text string) *BoolResult {
	args := map[string]interface{}{
		"text": text,
	}

	result, err := c.Session.CallMcpTool("input_text", args)
	if err != nil {
		return &BoolResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			Success:      false,
			ErrorMessage: fmt.Sprintf("failed to call input_text: %v", err),
		}
	}

	return &BoolResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success:      result.Success,
		ErrorMessage: result.ErrorMessage,
	}
}

// PressKeys presses multiple keyboard keys simultaneously
func (c *Computer) PressKeys(keys []string, hold bool) *BoolResult {
	args := map[string]interface{}{
		"keys": keys,
		"hold": hold,
	}

	result, err := c.Session.CallMcpTool("press_keys", args)
	if err != nil {
		return &BoolResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			Success:      false,
			ErrorMessage: fmt.Sprintf("failed to call press_keys: %v", err),
		}
	}

	return &BoolResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success:      result.Success,
		ErrorMessage: result.ErrorMessage,
	}
}

// ReleaseKeys releases multiple keyboard keys
func (c *Computer) ReleaseKeys(keys []string) *BoolResult {
	args := map[string]interface{}{
		"keys": keys,
	}

	result, err := c.Session.CallMcpTool("release_keys", args)
	if err != nil {
		return &BoolResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			Success:      false,
			ErrorMessage: fmt.Sprintf("failed to call release_keys: %v", err),
		}
	}

	return &BoolResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success:      result.Success,
		ErrorMessage: result.ErrorMessage,
	}
}

// GetScreenSize gets the size of the primary screen
func (c *Computer) GetScreenSize() *ScreenSize {
	args := map[string]interface{}{}

	result, err := c.Session.CallMcpTool("get_screen_size", args)
	if err != nil {
		return &ScreenSize{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			ErrorMessage: fmt.Sprintf("failed to call get_screen_size: %v", err),
		}
	}

	if !result.Success {
		return &ScreenSize{
			ApiResponse: models.ApiResponse{
				RequestID: result.RequestID,
			},
			ErrorMessage: result.ErrorMessage,
		}
	}

	// Parse screen size from JSON
	var size struct {
		Width            int     `json:"width"`
		Height           int     `json:"height"`
		DpiScalingFactor float64 `json:"dpiScalingFactor"`
	}
	if err := json.Unmarshal([]byte(result.Data), &size); err != nil {
		return &ScreenSize{
			ApiResponse: models.ApiResponse{
				RequestID: result.RequestID,
			},
			ErrorMessage: fmt.Sprintf("failed to parse screen size: %v", err),
		}
	}

	return &ScreenSize{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Width:            size.Width,
		Height:           size.Height,
		DpiScalingFactor: size.DpiScalingFactor,
		ErrorMessage:     result.ErrorMessage,
	}
}

// Screenshot takes a screenshot of the current screen
func (c *Computer) Screenshot() *ScreenshotResult {
	args := map[string]interface{}{}

	result, err := c.Session.CallMcpTool("system_screenshot", args)
	if err != nil {
		return &ScreenshotResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			ErrorMessage: fmt.Sprintf("failed to call system_screenshot: %v", err),
		}
	}

	return &ScreenshotResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Data:         result.Data,
		ErrorMessage: result.ErrorMessage,
	}
}

// ListRootWindows lists all root windows
func (c *Computer) ListRootWindows(timeoutMs ...int) (*window.WindowListResult, error) {
	windowManager := window.NewWindowManager(c.Session)
	return windowManager.ListRootWindows()
}

// GetActiveWindow gets the currently active window
func (c *Computer) GetActiveWindow(timeoutMs ...int) (*window.WindowDetailResult, error) {
	windowManager := window.NewWindowManager(c.Session)
	return windowManager.GetActiveWindow()
}

// ActivateWindow activates the specified window
func (c *Computer) ActivateWindow(windowID int) (*window.WindowResult, error) {
	windowManager := window.NewWindowManager(c.Session)
	return windowManager.ActivateWindow(windowID)
}

// CloseWindow closes the specified window
func (c *Computer) CloseWindow(windowID int) (*window.WindowResult, error) {
	windowManager := window.NewWindowManager(c.Session)
	return windowManager.CloseWindow(windowID)
}

// MaximizeWindow maximizes the specified window
func (c *Computer) MaximizeWindow(windowID int) (*window.WindowResult, error) {
	windowManager := window.NewWindowManager(c.Session)
	return windowManager.MaximizeWindow(windowID)
}

// MinimizeWindow minimizes the specified window
func (c *Computer) MinimizeWindow(windowID int) (*window.WindowResult, error) {
	windowManager := window.NewWindowManager(c.Session)
	return windowManager.MinimizeWindow(windowID)
}

// RestoreWindow restores the specified window
func (c *Computer) RestoreWindow(windowID int) (*window.WindowResult, error) {
	windowManager := window.NewWindowManager(c.Session)
	return windowManager.RestoreWindow(windowID)
}

// ResizeWindow resizes the specified window
func (c *Computer) ResizeWindow(windowID int, width int, height int) (*window.WindowResult, error) {
	windowManager := window.NewWindowManager(c.Session)
	return windowManager.ResizeWindow(windowID, width, height)
}

// FullscreenWindow makes the specified window fullscreen
func (c *Computer) FullscreenWindow(windowID int) (*window.WindowResult, error) {
	windowManager := window.NewWindowManager(c.Session)
	return windowManager.FullscreenWindow(windowID)
}

// FocusMode toggles focus mode on or off
func (c *Computer) FocusMode(on bool) (*window.WindowResult, error) {
	windowManager := window.NewWindowManager(c.Session)
	return windowManager.FocusMode(on)
}
