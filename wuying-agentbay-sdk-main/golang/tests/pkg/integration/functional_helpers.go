package integration

import (
	"math"
	"strings"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/computer"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/mobile"
)

// FunctionalTestConfig defines configuration for functional tests
type FunctionalTestConfig struct {
	WaitTimeAfterAction     time.Duration // Wait time after each action
	MaxRetries              int           // Maximum retry attempts
	ScreenshotComparison    bool          // Enable screenshot comparison
	UIElementTolerance      float64       // UI element change tolerance (0.0-1.0)
	CursorPositionTolerance int           // Cursor position tolerance in pixels
}

// DefaultFunctionalTestConfig returns default configuration
func DefaultFunctionalTestConfig() *FunctionalTestConfig {
	return &FunctionalTestConfig{
		WaitTimeAfterAction:     2 * time.Second,
		MaxRetries:              3,
		ScreenshotComparison:    true,
		UIElementTolerance:      0.3, // 30% change threshold
		CursorPositionTolerance: 5,   // 5 pixel tolerance
	}
}

// ValidateCursorPosition checks if cursor position is within screen bounds and expected range
func ValidateCursorPosition(cursor *computer.CursorPosition, screen *computer.ScreenSize, expectedX, expectedY int, tolerance int) bool {
	if cursor == nil || screen == nil {
		return false
	}

	// Check if cursor is within screen bounds
	if cursor.X < 0 || cursor.Y < 0 || cursor.X >= screen.Width || cursor.Y >= screen.Height {
		return false
	}

	// Check if cursor is within expected position tolerance
	deltaX := int(math.Abs(float64(cursor.X - expectedX)))
	deltaY := int(math.Abs(float64(cursor.Y - expectedY)))

	return deltaX <= tolerance && deltaY <= tolerance
}

// ValidateScreenshotChanged checks if screenshot URLs indicate content change
func ValidateScreenshotChanged(url1, url2 string) bool {
	if url1 == "" || url2 == "" {
		return false
	}

	// Different URLs typically indicate different content
	// AgentBay generates new URLs for new screenshots
	return url1 != url2
}

// ValidateScreenSize checks if screen size values are reasonable
func ValidateScreenSize(screen *computer.ScreenSize) bool {
	if screen == nil {
		return false
	}

	// Screen dimensions should be positive and reasonable
	return screen.Width > 0 && screen.Height > 0 &&
		screen.Width <= 10000 && screen.Height <= 10000 && // Max reasonable size
		screen.DpiScalingFactor > 0 && screen.DpiScalingFactor <= 10 // Reasonable DPI range
}

// UIElement represents a simplified UI element for comparison
type UIElement struct {
	Text      string
	ClassName string
	Bounds    struct {
		Left, Top, Right, Bottom int
	}
}

// ConvertMobileUIElements converts mobile UI elements to simplified format
func ConvertMobileUIElements(elements []*mobile.UIElement) []UIElement {
	result := make([]UIElement, len(elements))
	for i, elem := range elements {
		if elem != nil {
			result[i] = UIElement{
				Text:      elem.Text,
				ClassName: elem.ClassName,
				Bounds: struct {
					Left, Top, Right, Bottom int
				}{
					Left:   elem.Bounds.Left,
					Top:    elem.Bounds.Top,
					Right:  elem.Bounds.Right,
					Bottom: elem.Bounds.Bottom,
				},
			}
		}
	}
	return result
}

// ValidateUIElementsChanged checks if UI elements have changed significantly
func ValidateUIElementsChanged(before, after []UIElement, tolerance float64) bool {
	if len(before) == 0 && len(after) == 0 {
		return false // No elements in either case
	}

	// Calculate change ratio
	totalElements := len(before) + len(after)
	if totalElements == 0 {
		return false
	}

	// Count different elements
	differentCount := 0

	// Simple comparison: check if element counts differ significantly
	countDiff := math.Abs(float64(len(after) - len(before)))
	if countDiff/float64(math.Max(float64(len(before)), 1)) > tolerance {
		return true
	}

	// Check for text content changes
	beforeTexts := make(map[string]bool)
	for _, elem := range before {
		if elem.Text != "" {
			beforeTexts[elem.Text] = true
		}
	}

	afterTexts := make(map[string]bool)
	for _, elem := range after {
		if elem.Text != "" {
			afterTexts[elem.Text] = true
		}
	}

	// Count text differences
	for text := range afterTexts {
		if !beforeTexts[text] {
			differentCount++
		}
	}

	for text := range beforeTexts {
		if !afterTexts[text] {
			differentCount++
		}
	}

	changeRatio := float64(differentCount) / float64(totalElements)
	return changeRatio > tolerance
}

// ValidateAppLaunched checks if app launch was successful by analyzing UI changes
func ValidateAppLaunched(beforeUI, afterUI []UIElement) bool {
	// App launch should result in significant UI changes
	return ValidateUIElementsChanged(beforeUI, afterUI, 0.5) // 50% change threshold for app launch
}

// FindTextInputElement finds a text input element in UI elements list
func FindTextInputElement(elements []UIElement) *UIElement {
	for _, elem := range elements {
		// Look for common text input class names
		if strings.Contains(strings.ToLower(elem.ClassName), "edittext") ||
			strings.Contains(strings.ToLower(elem.ClassName), "textfield") ||
			strings.Contains(strings.ToLower(elem.ClassName), "input") {
			return &elem
		}
	}
	return nil
}

// CalculateElementCenter calculates the center point of a UI element
func CalculateElementCenter(elem *UIElement) (int, int) {
	if elem == nil {
		return 0, 0
	}
	centerX := (elem.Bounds.Left + elem.Bounds.Right) / 2
	centerY := (elem.Bounds.Top + elem.Bounds.Bottom) / 2
	return centerX, centerY
}

// ValidateElementBounds checks if element bounds are reasonable
func ValidateElementBounds(elem *UIElement, screenWidth, screenHeight int) bool {
	if elem == nil {
		return false
	}

	bounds := elem.Bounds
	return bounds.Left >= 0 && bounds.Top >= 0 &&
		bounds.Right <= screenWidth && bounds.Bottom <= screenHeight &&
		bounds.Left < bounds.Right && bounds.Top < bounds.Bottom
}

// FunctionalTestResult represents the result of a functional test
type FunctionalTestResult struct {
	TestName string
	Success  bool
	Message  string
	Details  map[string]interface{}
	Duration time.Duration
}

// NewFunctionalTestResult creates a new test result
func NewFunctionalTestResult(testName string) *FunctionalTestResult {
	return &FunctionalTestResult{
		TestName: testName,
		Success:  false,
		Details:  make(map[string]interface{}),
	}
}

// SetSuccess marks the test as successful
func (r *FunctionalTestResult) SetSuccess(message string) {
	r.Success = true
	r.Message = message
}

// SetFailure marks the test as failed
func (r *FunctionalTestResult) SetFailure(message string) {
	r.Success = false
	r.Message = message
}

// AddDetail adds a detail to the test result
func (r *FunctionalTestResult) AddDetail(key string, value interface{}) {
	r.Details[key] = value
}

// WaitWithTimeout waits for a condition with timeout
func WaitWithTimeout(condition func() bool, timeout time.Duration, checkInterval time.Duration) bool {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		if condition() {
			return true
		}
		time.Sleep(checkInterval)
	}
	return false
}

// SafeScreenshot takes a screenshot with error handling
func SafeScreenshot(computer *computer.Computer, testName string) (string, error) {
	if computer == nil {
		return "", nil
	}

	result := computer.Screenshot()
	if result == nil {
		return "", nil
	}

	if result.ErrorMessage != "" {
		return "", nil
	}

	return result.Data, nil
}

// SafeMobileScreenshot takes a mobile screenshot with error handling
func SafeMobileScreenshot(mobile *mobile.Mobile, testName string) (string, error) {
	if mobile == nil {
		return "", nil
	}

	result := mobile.Screenshot()
	if result == nil {
		return "", nil
	}

	if result.ErrorMessage != "" {
		return "", nil
	}

	return result.Data, nil
}
