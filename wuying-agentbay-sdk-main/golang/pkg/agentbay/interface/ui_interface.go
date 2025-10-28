package interfaces

import (
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/ui"
)

//go:generate mockgen -destination=../../../tests/pkg/unit/mock/mock_ui.go -package=mock github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/interface UIInterface

// UIInterface defines the interface for UI operations
type UIInterface interface {
	GetClickableUIElements(timeoutMs int) (*ui.UIElementsResult, error)
	GetAllUIElements(timeoutMs int) (*ui.UIElementsResult, error)
	SendKey(key int) (*ui.KeyActionResult, error)
	InputText(text string) (*ui.TextInputResult, error)
	Swipe(startX, startY, endX, endY, durationMs int) (*ui.SwipeResult, error)
	Click(x, y int, button string) (*ui.UIResult, error)
	Screenshot() (*ui.UIResult, error)
}
