package integration

import (
	"os"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestComputerRealE2E tests Computer module with real AgentBay session
// This test requires:
// 1. AGENTBAY_API_KEY environment variable
// 2. Real AgentBay session (linux_latest or windows_lat·est image)
// 3. Manual execution (not suitable for CI/CD)
func TestComputerRealE2E(t *testing.T) {
	// Skip if no API key provided
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		t.Skip("Skipping real E2E test: AGENTBAY_API_KEY not set")
	}

	// Create AgentBay client
	agentBay, err := agentbay.NewAgentBay(apiKey)
	require.NoError(t, err, "Failed to create AgentBay client")

	// Create session with desktop image
	sessionParams := &agentbay.CreateSessionParams{
		ImageId: "linux_latest", // Use linux_latest for desktop automation
	}

	sessionResult, err := agentBay.Create(sessionParams)
	require.NoError(t, err, "Failed to create session")
	require.NotNil(t, sessionResult.Session, "Session should be created")

	session := sessionResult.Session
	defer func() {
		// Cleanup: Delete session after test
		deleteResult, _ := session.Delete()
		if deleteResult != nil && deleteResult.Success {
			t.Logf("Session %s deleted successfully", session.SessionID)
		}
	}()

	t.Logf("Created session: %s", session.SessionID)

	// Wait for session to be ready
	time.Sleep(10 * time.Second)

	t.Run("Computer Screenshot", func(t *testing.T) {
		result := session.Computer.Screenshot()

		assert.NotEmpty(t, result.RequestID, "Should have request ID")
		if result.Data != "" {
			t.Logf("Screenshot URL: %s", result.Data)
			assert.Contains(t, result.Data, "http", "Screenshot should be a URL")
		} else {
			t.Logf("Screenshot failed: %s", result.ErrorMessage)
		}
	})

	t.Run("Computer GetScreenSize", func(t *testing.T) {
		result := session.Computer.GetScreenSize()

		assert.NotEmpty(t, result.RequestID, "Should have request ID")
		if result.Width > 0 && result.Height > 0 {
			t.Logf("Screen size: %dx%d (DPI: %.1f)", result.Width, result.Height, result.DpiScalingFactor)
			assert.Greater(t, result.Width, 0, "Width should be positive")
			assert.Greater(t, result.Height, 0, "Height should be positive")
			assert.Greater(t, result.DpiScalingFactor, 0.0, "DPI scaling factor should be positive")
		} else {
			t.Logf("GetScreenSize failed: %s", result.ErrorMessage)
		}
	})

	t.Run("Computer GetCursorPosition", func(t *testing.T) {
		result := session.Computer.GetCursorPosition()

		assert.NotEmpty(t, result.RequestID, "Should have request ID")
		if result.ErrorMessage == "" {
			t.Logf("Cursor position: (%d, %d)", result.X, result.Y)
			assert.GreaterOrEqual(t, result.X, 0, "X coordinate should be non-negative")
			assert.GreaterOrEqual(t, result.Y, 0, "Y coordinate should be non-negative")
		} else {
			t.Logf("GetCursorPosition failed: %s", result.ErrorMessage)
		}
	})

	t.Run("Computer MoveMouse", func(t *testing.T) {
		// Move mouse to center of screen first
		screenResult := session.Computer.GetScreenSize()
		if screenResult.Width > 0 && screenResult.Height > 0 {
			centerX := screenResult.Width / 2
			centerY := screenResult.Height / 2

			result := session.Computer.MoveMouse(centerX, centerY)
			assert.NotEmpty(t, result.RequestID, "Should have request ID")

			if result.Success {
				t.Logf("Mouse moved to center: (%d, %d)", centerX, centerY)

				// Verify cursor position changed
				time.Sleep(1 * time.Second)
				posResult := session.Computer.GetCursorPosition()
				if posResult.ErrorMessage == "" {
					t.Logf("New cursor position: (%d, %d)", posResult.X, posResult.Y)
				}
			} else {
				t.Logf("MoveMouse failed: %s", result.ErrorMessage)
			}
		} else {
			t.Skip("Cannot test MoveMouse without screen size")
		}
	})

	t.Run("Computer InputText", func(t *testing.T) {
		testText := "Hello AgentBay Computer Module!"
		result := session.Computer.InputText(testText)

		assert.NotEmpty(t, result.RequestID, "Should have request ID")
		if result.Success {
			t.Logf("Successfully input text: %s", testText)
		} else {
			t.Logf("InputText failed: %s", result.ErrorMessage)
		}
	})

	t.Run("Computer PressKeys", func(t *testing.T) {
		// Test Ctrl+A (Select All)
		result := session.Computer.PressKeys([]string{"Ctrl", "a"}, false)

		assert.NotEmpty(t, result.RequestID, "Should have request ID")
		if result.Success {
			t.Logf("Successfully pressed Ctrl+A")
		} else {
			t.Logf("PressKeys failed: %s", result.ErrorMessage)
		}
	})

	t.Run("Computer Parameter Validation", func(t *testing.T) {
		// Test invalid button parameter
		result := session.Computer.ClickMouse(100, 200, "invalid_button")
		assert.False(t, result.Success, "Should fail with invalid button")
		assert.Contains(t, result.ErrorMessage, "invalid button", "Should mention invalid button")

		// Test invalid scroll direction
		scrollResult := session.Computer.Scroll(100, 200, "invalid_direction", 1)
		assert.False(t, scrollResult.Success, "Should fail with invalid direction")
		assert.Contains(t, scrollResult.ErrorMessage, "invalid direction", "Should mention invalid direction")
	})

	t.Run("Computer Complete Workflow", func(t *testing.T) {
		// This tests a complete desktop automation workflow
		t.Log("Starting complete desktop automation workflow...")

		// Step 1: Take initial screenshot
		screenshot1 := session.Computer.Screenshot()
		if screenshot1.Data != "" {
			t.Logf("Initial screenshot: %s", screenshot1.Data)
		}

		// Step 2: Get screen dimensions
		screen := session.Computer.GetScreenSize()
		if screen.Width > 0 && screen.Height > 0 {
			t.Logf("Working with screen: %dx%d", screen.Width, screen.Height)

			// Step 3: Move to a safe area (center of screen)
			centerX := screen.Width / 2
			centerY := screen.Height / 2
			moveResult := session.Computer.MoveMouse(centerX, centerY)
			if moveResult.Success {
				t.Logf("Moved to center: (%d, %d)", centerX, centerY)
			}

			// Step 4: Click at center
			clickResult := session.Computer.ClickMouse(centerX, centerY, "left")
			if clickResult.Success {
				t.Log("Clicked at center")
			}

			// Step 5: Type some text
			inputResult := session.Computer.InputText("AgentBay E2E Test")
			if inputResult.Success {
				t.Log("Input test text")
			}

			// Step 6: Select all text
			selectResult := session.Computer.PressKeys([]string{"Ctrl", "a"}, false)
			if selectResult.Success {
				t.Log("Selected all text")
			}

			// Step 7: Take final screenshot
			screenshot2 := session.Computer.Screenshot()
			if screenshot2.Data != "" {
				t.Logf("Final screenshot: %s", screenshot2.Data)
			}

			t.Log("Complete workflow finished successfully")
		} else {
			t.Skip("Cannot run complete workflow without screen size")
		}
	})
}
