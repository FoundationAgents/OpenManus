package interfaces

import (
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/window"
)

//go:generate mockgen -destination=../../../tests/pkg/unit/mock/mock_window.go -package=mock github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/interface WindowInterface

// WindowInterface defines the interface for window operations
type WindowInterface interface {
	// ListRootWindows lists all root windows
	ListRootWindows() (*window.WindowListResult, error)

	// GetActiveWindow gets the currently active window
	GetActiveWindow() (*window.WindowDetailResult, error)

	// ActivateWindow activates a window by ID
	ActivateWindow(windowID int) (*window.WindowResult, error)

	// MaximizeWindow maximizes a window by ID
	MaximizeWindow(windowID int) (*window.WindowResult, error)

	// MinimizeWindow minimizes a window by ID
	MinimizeWindow(windowID int) (*window.WindowResult, error)

	// RestoreWindow restores a window by ID
	RestoreWindow(windowID int) (*window.WindowResult, error)

	// CloseWindow closes a window by ID
	CloseWindow(windowID int) (*window.WindowResult, error)

	// FullscreenWindow toggles fullscreen mode for a window by ID
	FullscreenWindow(windowID int) (*window.WindowResult, error)

	// ResizeWindow resizes a window by ID
	ResizeWindow(windowID int, width int, height int) (*window.WindowResult, error)

	// FocusMode enables or disables focus mode
	FocusMode(on bool) (*window.WindowResult, error)
}
