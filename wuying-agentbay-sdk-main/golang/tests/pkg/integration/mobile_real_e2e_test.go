package integration

import (
	"os"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestMobileRealE2E tests Mobile module with real AgentBay session
// This test requires:
// 1. AGENTBAY_API_KEY environment variable
// 2. Real AgentBay session (mobile_latest image)
// 3. Manual execution (not suitable for CI/CD)
func TestMobileRealE2E(t *testing.T) {
	// Skip if no API key provided
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		t.Skip("Skipping real E2E test: AGENTBAY_API_KEY not set")
	}

	// Create AgentBay client
	agentBay, err := agentbay.NewAgentBay(apiKey)
	require.NoError(t, err, "Failed to create AgentBay client")

	// Create session with mobile image
	sessionParams := &agentbay.CreateSessionParams{
		ImageId: "mobile_latest", // Use mobile_latest for mobile automation
	}

	sessionResult, err := agentBay.Create(sessionParams)
	require.NoError(t, err, "Failed to create session")
	require.NotNil(t, sessionResult.Session, "Session should be created")

	session := sessionResult.Session
	defer func() {
		// Cleanup: Delete session after test
		deleteResult, _ := session.Delete()
		if deleteResult != nil && deleteResult.RequestID != "" {
			t.Logf("Session %s deleted successfully", session.SessionID)
		}
	}()

	t.Logf("Created mobile session: %s", session.SessionID)

	// Wait for session to be ready
	time.Sleep(15 * time.Second) // Mobile sessions may take longer to start

	t.Run("Mobile Screenshot", func(t *testing.T) {
		result := session.Mobile.Screenshot()

		assert.NotEmpty(t, result.RequestID, "Should have request ID")
		if result.Data != "" {
			t.Logf("Mobile screenshot URL: %s", result.Data)
			assert.Contains(t, result.Data, "http", "Screenshot should be a URL")
		} else {
			t.Logf("Mobile screenshot failed: %s", result.ErrorMessage)
		}
	})

	t.Run("Mobile GetInstalledApps", func(t *testing.T) {
		result := session.Mobile.GetInstalledApps(false, true, true)

		assert.NotEmpty(t, result.RequestID, "Should have request ID")
		if len(result.Apps) > 0 {
			t.Logf("Found %d installed apps", len(result.Apps))
			for i, app := range result.Apps {
				if i < 5 { // Log first 5 apps
					t.Logf("App %d: %s (%s)", i+1, app.Name, app.StartCmd)
				}
			}
		} else {
			t.Logf("GetInstalledApps failed or no apps found: %s", result.ErrorMessage)
		}
	})

	t.Run("Mobile GetClickableUIElements", func(t *testing.T) {
		result := session.Mobile.GetClickableUIElements(5000) // 5 second timeout

		assert.NotEmpty(t, result.RequestID, "Should have request ID")
		if len(result.Elements) > 0 {
			t.Logf("Found %d clickable UI elements", len(result.Elements))
			for i, element := range result.Elements {
				if i < 3 { // Log first 3 elements
					t.Logf("Element %d: %s (bounds: %+v)", i+1, element.Text, element.Bounds)
				}
			}
		} else {
			t.Logf("GetClickableUIElements failed or no elements found: %s", result.ErrorMessage)
		}
	})

	t.Run("Mobile GetAllUIElements", func(t *testing.T) {
		result := session.Mobile.GetAllUIElements(5000) // 5 second timeout

		assert.NotEmpty(t, result.RequestID, "Should have request ID")
		if len(result.Elements) > 0 {
			t.Logf("Found %d total UI elements", len(result.Elements))
			// Count different element types
			textViews := 0
			buttons := 0
			others := 0
			for _, element := range result.Elements {
				switch element.ClassName {
				case "TextView", "android.widget.TextView":
					textViews++
				case "Button", "android.widget.Button":
					buttons++
				default:
					others++
				}
			}
			t.Logf("Element breakdown: %d TextViews, %d Buttons, %d Others", textViews, buttons, others)
		} else {
			t.Logf("GetAllUIElements failed or no elements found: %s", result.ErrorMessage)
		}
	})

	t.Run("Mobile Tap", func(t *testing.T) {
		// Tap at center of screen (safe area)
		centerX := 540 // Common mobile screen center X
		centerY := 960 // Common mobile screen center Y

		result := session.Mobile.Tap(centerX, centerY)

		assert.NotEmpty(t, result.RequestID, "Should have request ID")
		if result.Success {
			t.Logf("Successfully tapped at (%d, %d)", centerX, centerY)
		} else {
			t.Logf("Tap failed: %s", result.ErrorMessage)
		}
	})

	t.Run("Mobile SendKey", func(t *testing.T) {
		// Test HOME key (Android key code 3)
		result := session.Mobile.SendKey(3)

		assert.NotEmpty(t, result.RequestID, "Should have request ID")
		if result.Success {
			t.Log("Successfully sent HOME key")

			// Wait a moment for the action to complete
			time.Sleep(2 * time.Second)
		} else {
			t.Logf("SendKey failed: %s", result.ErrorMessage)
		}
	})

	t.Run("Mobile InputText", func(t *testing.T) {
		testText := "AgentBay Mobile Test"
		result := session.Mobile.InputText(testText)

		assert.NotEmpty(t, result.RequestID, "Should have request ID")
		if result.Success {
			t.Logf("Successfully input text: %s", testText)
		} else {
			t.Logf("InputText failed: %s", result.ErrorMessage)
		}
	})

	t.Run("Mobile Swipe", func(t *testing.T) {
		// Swipe from bottom to top (scroll up gesture)
		startX := 540
		startY := 1500
		endX := 540
		endY := 500
		duration := 500 // 500ms

		result := session.Mobile.Swipe(startX, startY, endX, endY, duration)

		assert.NotEmpty(t, result.RequestID, "Should have request ID")
		if result.Success {
			t.Logf("Successfully swiped from (%d,%d) to (%d,%d)", startX, startY, endX, endY)
		} else {
			t.Logf("Swipe failed: %s", result.ErrorMessage)
		}
	})

	t.Run("Mobile App Management", func(t *testing.T) {
		// First, get list of installed apps
		appsResult := session.Mobile.GetInstalledApps(false, true, false)
		if len(appsResult.Apps) > 0 {
			// Try to start the first app
			firstApp := appsResult.Apps[0]
			t.Logf("Attempting to start app: %s", firstApp.Name)

			startResult := session.Mobile.StartApp(firstApp.StartCmd, "", "")
			if startResult.RequestID != "" {
				if len(startResult.Processes) > 0 {
					t.Logf("App started successfully, PID: %d", startResult.Processes[0].PID)

					// Wait a moment
					time.Sleep(3 * time.Second)

					// Try to stop the app
					stopResult := session.Mobile.StopAppByPName(startResult.Processes[0].PName)
					if stopResult.Success {
						t.Logf("App stopped successfully")
					} else {
						t.Logf("Failed to stop app: %s", stopResult.ErrorMessage)
					}
				} else {
					t.Logf("App start result unclear: %s", startResult.ErrorMessage)
				}
			}
		} else {
			t.Skip("No apps available for app management test")
		}
	})

	t.Run("Mobile Complete Workflow", func(t *testing.T) {
		// This tests a complete mobile automation workflow
		t.Log("Starting complete mobile automation workflow...")

		// Step 1: Take initial screenshot
		screenshot1 := session.Mobile.Screenshot()
		if screenshot1.Data != "" {
			t.Logf("Initial mobile screenshot: %s", screenshot1.Data)
		}

		// Step 2: Press HOME to go to home screen
		homeResult := session.Mobile.SendKey(3) // HOME key
		if homeResult.Success {
			t.Log("Pressed HOME key")
			time.Sleep(2 * time.Second)
		}

		// Step 3: Get UI elements on home screen
		elementsResult := session.Mobile.GetClickableUIElements(3000)
		if len(elementsResult.Elements) > 0 {
			t.Logf("Found %d clickable elements on home screen", len(elementsResult.Elements))

			// Step 4: Tap on the first clickable element (if safe)
			firstElement := elementsResult.Elements[0]
			if firstElement.Bounds.Left >= 0 && firstElement.Bounds.Top >= 0 {
				tapX := (firstElement.Bounds.Left + firstElement.Bounds.Right) / 2
				tapY := (firstElement.Bounds.Top + firstElement.Bounds.Bottom) / 2

				tapResult := session.Mobile.Tap(tapX, tapY)
				if tapResult.Success {
					t.Logf("Tapped on element: %s", firstElement.Text)
					time.Sleep(2 * time.Second)
				}
			}
		}

		// Step 5: Swipe gesture
		swipeResult := session.Mobile.Swipe(540, 1200, 540, 600, 400)
		if swipeResult.Success {
			t.Log("Performed swipe gesture")
			time.Sleep(1 * time.Second)
		}

		// Step 6: Press BACK to return
		backResult := session.Mobile.SendKey(4) // BACK key
		if backResult.Success {
			t.Log("Pressed BACK key")
			time.Sleep(1 * time.Second)
		}

		// Step 7: Take final screenshot
		screenshot2 := session.Mobile.Screenshot()
		if screenshot2.Data != "" {
			t.Logf("Final mobile screenshot: %s", screenshot2.Data)
		}

		t.Log("Complete mobile workflow finished successfully")
	})
}
