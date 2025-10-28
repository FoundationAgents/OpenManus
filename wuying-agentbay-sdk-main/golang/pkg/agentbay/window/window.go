package window

import (
	"encoding/json"
	"fmt"

	mcp "github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

// Window represents a window in the system
type Window struct {
	WindowID           int      `json:"window_id"`
	Title              string   `json:"title"`
	AbsoluteUpperLeftX int      `json:"absolute_upper_left_x,omitempty"`
	AbsoluteUpperLeftY int      `json:"absolute_upper_left_y,omitempty"`
	Width              int      `json:"width,omitempty"`
	Height             int      `json:"height,omitempty"`
	PID                int      `json:"pid,omitempty"`
	PName              string   `json:"pname,omitempty"`
	ChildWindows       []Window `json:"child_windows,omitempty"`
}

// WindowInfo represents window information
type WindowInfo struct {
	WindowID int    `json:"window_id"`
	Title    string `json:"title"`
	PID      int    `json:"pid"`
	PName    string `json:"pname"`
}

// WindowListResult represents the result of listing windows
type WindowListResult struct {
	models.ApiResponse
	Windows []*WindowInfo
}

// WindowDetailResult represents the result of getting window details
type WindowDetailResult struct {
	models.ApiResponse
	Window *Window
}

// WindowResult represents the result of a window action
type WindowResult struct {
	models.ApiResponse
	Success bool
}

// WindowInfoResult represents the result of getting window information
type WindowInfoResult struct {
	models.ApiResponse
	Window *WindowInfo
}

// WindowActionResult represents the result of a window action
type WindowActionResult struct {
	models.ApiResponse
	Success bool
}

// WindowManager handles window management operations in the AgentBay cloud environment
type WindowManager struct {
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

// NewWindowManager creates a new window manager instance
func NewWindowManager(session interface {
	GetAPIKey() string
	GetClient() *mcp.Client
	GetSessionId() string
	IsVpc() bool
	NetworkInterfaceIp() string
	HttpPort() string
	FindServerForTool(toolName string) string
	CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error)
}) *WindowManager {
	return &WindowManager{
		Session: session,
	}
}

// ListRootWindows lists all root windows with their associated information
func (wm *WindowManager) ListRootWindows() (*WindowListResult, error) {
	args := map[string]interface{}{}

	result, err := wm.Session.CallMcpTool("list_root_windows", args)
	if err != nil {
		return nil, fmt.Errorf("error listing root windows: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("error listing root windows: %s", result.ErrorMessage)
	}

	// Parse the JSON string into a slice of WindowInfo structs
	var windows []*WindowInfo
	if err := json.Unmarshal([]byte(result.Data), &windows); err != nil {
		return nil, fmt.Errorf("failed to parse window information: %w", err)
	}

	return &WindowListResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Windows: windows,
	}, nil
}

// GetActiveWindow retrieves information about the currently active window (original interface)
func (wm *WindowManager) GetActiveWindow() (*WindowDetailResult, error) {
	args := map[string]interface{}{}

	result, err := wm.Session.CallMcpTool("get_active_window", args)
	if err != nil {
		return nil, fmt.Errorf("error getting active window: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("error getting active window: %s", result.ErrorMessage)
	}

	// Parse the JSON string into a Window struct
	var window Window
	if err := json.Unmarshal([]byte(result.Data), &window); err != nil {
		return nil, fmt.Errorf("failed to parse window information: %w", err)
	}

	return &WindowDetailResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Window: &window,
	}, nil
}

// ActivateWindow activates a window by ID (original interface)
func (wm *WindowManager) ActivateWindow(windowID int) (*WindowResult, error) {
	args := map[string]interface{}{
		"window_id": windowID,
	}

	result, err := wm.Session.CallMcpTool("activate_window", args)
	if err != nil {
		return nil, fmt.Errorf("error activating window: %w", err)
	}

	return &WindowResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: result.Success,
	}, nil
}

// MaximizeWindow maximizes a window by ID (original interface)
func (wm *WindowManager) MaximizeWindow(windowID int) (*WindowResult, error) {
	args := map[string]interface{}{
		"window_id": windowID,
	}

	result, err := wm.Session.CallMcpTool("maximize_window", args)
	if err != nil {
		return nil, fmt.Errorf("error maximizing window: %w", err)
	}

	return &WindowResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: result.Success,
	}, nil
}

// MinimizeWindow minimizes a window by ID (original interface)
func (wm *WindowManager) MinimizeWindow(windowID int) (*WindowResult, error) {
	args := map[string]interface{}{
		"window_id": windowID,
	}

	result, err := wm.Session.CallMcpTool("minimize_window", args)
	if err != nil {
		return nil, fmt.Errorf("error minimizing window: %w", err)
	}

	return &WindowResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: result.Success,
	}, nil
}

// RestoreWindow restores a window by ID (original interface)
func (wm *WindowManager) RestoreWindow(windowID int) (*WindowResult, error) {
	args := map[string]interface{}{
		"window_id": windowID,
	}

	result, err := wm.Session.CallMcpTool("restore_window", args)
	if err != nil {
		return nil, fmt.Errorf("error restoring window: %w", err)
	}

	return &WindowResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: result.Success,
	}, nil
}

// CloseWindow closes a window by ID (original interface)
func (wm *WindowManager) CloseWindow(windowID int) (*WindowResult, error) {
	args := map[string]interface{}{
		"window_id": windowID,
	}

	result, err := wm.Session.CallMcpTool("close_window", args)
	if err != nil {
		return nil, fmt.Errorf("error closing window: %w", err)
	}

	return &WindowResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: result.Success,
	}, nil
}

// FullscreenWindow toggles fullscreen mode for a window by ID (original interface)
func (wm *WindowManager) FullscreenWindow(windowID int) (*WindowResult, error) {
	args := map[string]interface{}{
		"window_id": windowID,
	}

	result, err := wm.Session.CallMcpTool("fullscreen_window", args)
	if err != nil {
		return nil, fmt.Errorf("error toggling fullscreen: %w", err)
	}

	return &WindowResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: result.Success,
	}, nil
}

// ResizeWindow resizes a window by ID (original interface)
func (wm *WindowManager) ResizeWindow(windowID int, width, height int) (*WindowResult, error) {
	args := map[string]interface{}{
		"window_id": windowID,
		"width":     width,
		"height":    height,
	}

	result, err := wm.Session.CallMcpTool("resize_window", args)
	if err != nil {
		return nil, fmt.Errorf("error resizing window: %w", err)
	}

	return &WindowResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: result.Success,
	}, nil
}

// FocusMode enables or disables focus mode (original interface)
func (wm *WindowManager) FocusMode(on bool) (*WindowResult, error) {
	args := map[string]interface{}{
		"on": on,
	}

	result, err := wm.Session.CallMcpTool("focus_mode", args)
	if err != nil {
		return nil, fmt.Errorf("error setting focus mode: %w", err)
	}

	return &WindowResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: result.Success,
	}, nil
}
