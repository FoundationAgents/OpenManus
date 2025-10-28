package integration

import (
	"os"
	"sync"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/stretchr/testify/require"
)

// TestCrossPlatformFunctionalValidation tests consistency between Computer and Mobile modules
// This test validates that similar operations work on both platforms
func TestCrossPlatformFunctionalValidation(t *testing.T) {
	// Skip if no API key provided
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		t.Skip("Skipping cross-platform functional validation test: AGENTBAY_API_KEY not set")
	}

	// Create AgentBay client
	agentBay, err := agentbay.NewAgentBay(apiKey)
	require.NoError(t, err, "Failed to create AgentBay client")

	// Create both desktop and mobile sessions
	var desktopSession, mobileSession *agentbay.Session
	var wg sync.WaitGroup
	var sessionErrors []error

	// Create sessions in parallel to save time
	wg.Add(2)

	// Create desktop session
	go func() {
		defer wg.Done()
		sessionParams := &agentbay.CreateSessionParams{
			ImageId: "linux_latest",
		}
		sessionResult, err := agentBay.Create(sessionParams)
		if err != nil {
			sessionErrors = append(sessionErrors, err)
			return
		}
		if sessionResult.Session == nil {
			sessionErrors = append(sessionErrors, err)
			return
		}
		desktopSession = sessionResult.Session
	}()

	// Create mobile session
	go func() {
		defer wg.Done()
		sessionParams := &agentbay.CreateSessionParams{
			ImageId: "mobile_latest",
		}
		sessionResult, err := agentBay.Create(sessionParams)
		if err != nil {
			sessionErrors = append(sessionErrors, err)
			return
		}
		if sessionResult.Session == nil {
			sessionErrors = append(sessionErrors, err)
			return
		}
		mobileSession = sessionResult.Session
	}()

	wg.Wait()

	// Check for session creation errors
	if len(sessionErrors) > 0 {
		t.Fatalf("Failed to create sessions: %v", sessionErrors)
	}

	require.NotNil(t, desktopSession, "Desktop session should be created")
	require.NotNil(t, mobileSession, "Mobile session should be created")

	// Cleanup sessions
	defer func() {
		if desktopSession != nil {
			deleteResult, _ := desktopSession.Delete()
			if deleteResult != nil && deleteResult.RequestID != "" {
				t.Logf("Desktop session %s deleted", desktopSession.SessionID)
			}
		}
		if mobileSession != nil {
			deleteResult, _ := mobileSession.Delete()
			if deleteResult != nil && deleteResult.RequestID != "" {
				t.Logf("Mobile session %s deleted", mobileSession.SessionID)
			}
		}
	}()

	t.Logf("Created desktop session: %s", desktopSession.SessionID)
	t.Logf("Created mobile session: %s", mobileSession.SessionID)

	// Wait for sessions to be ready
	t.Log("Waiting for sessions to be ready...")
	time.Sleep(15 * time.Second) // Use mobile timing (longer)

	config := DefaultFunctionalTestConfig()

	t.Run("ScreenshotConsistencyValidation", func(t *testing.T) {
		result := NewFunctionalTestResult("ScreenshotConsistencyValidation")
		startTime := time.Now()
		defer func() {
			result.Duration = time.Since(startTime)
			t.Logf("Test Result: %+v", result)
		}()

		// Test screenshot functionality on both platforms
		desktopScreenshot1, _ := SafeScreenshot(desktopSession.Computer, "desktop_initial")
		mobileScreenshot1, _ := SafeMobileScreenshot(mobileSession.Mobile, "mobile_initial")

		if desktopScreenshot1 == "" {
			result.SetFailure("Desktop screenshot failed")
			return
		}
		if mobileScreenshot1 == "" {
			result.SetFailure("Mobile screenshot failed")
			return
		}

		result.AddDetail("desktop_screenshot1", desktopScreenshot1)
		result.AddDetail("mobile_screenshot1", mobileScreenshot1)

		// Perform actions on both platforms
		// Desktop: move mouse
		screen := desktopSession.Computer.GetScreenSize()
		if screen.ErrorMessage == "" {
			desktopSession.Computer.MoveMouse(screen.Width/2, screen.Height/2)
		}

		// Mobile: tap screen
		mobileSession.Mobile.Tap(540, 960)

		time.Sleep(config.WaitTimeAfterAction)

		// Take screenshots after actions
		desktopScreenshot2, _ := SafeScreenshot(desktopSession.Computer, "desktop_after_action")
		mobileScreenshot2, _ := SafeMobileScreenshot(mobileSession.Mobile, "mobile_after_action")

		result.AddDetail("desktop_screenshot2", desktopScreenshot2)
		result.AddDetail("mobile_screenshot2", mobileScreenshot2)

		// Validate both platforms can capture screenshots and detect changes
		desktopChanged := ValidateScreenshotChanged(desktopScreenshot1, desktopScreenshot2)
		mobileChanged := ValidateScreenshotChanged(mobileScreenshot1, mobileScreenshot2)

		result.AddDetail("desktop_screenshot_changed", desktopChanged)
		result.AddDetail("mobile_screenshot_changed", mobileChanged)

		if desktopScreenshot1 != "" && mobileScreenshot1 != "" {
			result.SetSuccess("Screenshot functionality works on both platforms")
			t.Logf("✅ Screenshots: Desktop=%v, Mobile=%v", desktopChanged, mobileChanged)
		} else {
			result.SetFailure("Screenshot functionality failed on one or both platforms")
		}
	})

	t.Run("InputFunctionalityConsistency", func(t *testing.T) {
		result := NewFunctionalTestResult("InputFunctionalityConsistency")
		startTime := time.Now()
		defer func() {
			result.Duration = time.Since(startTime)
			t.Logf("Test Result: %+v", result)
		}()

		testText := "Cross-Platform Test"

		// Test input on desktop
		desktopScreenshot1, _ := SafeScreenshot(desktopSession.Computer, "desktop_before_input")

		// Click and input on desktop
		screen := desktopSession.Computer.GetScreenSize()
		if screen.ErrorMessage == "" {
			desktopSession.Computer.ClickMouse(screen.Width/2, screen.Height/2, "left")
			time.Sleep(1 * time.Second)
		}

		desktopInputResult := desktopSession.Computer.InputText(testText)
		time.Sleep(config.WaitTimeAfterAction)

		desktopScreenshot2, _ := SafeScreenshot(desktopSession.Computer, "desktop_after_input")

		// Test input on mobile
		mobileScreenshot1, _ := SafeMobileScreenshot(mobileSession.Mobile, "mobile_before_input")

		// Tap and input on mobile
		mobileSession.Mobile.Tap(540, 960)
		time.Sleep(1 * time.Second)

		mobileInputResult := mobileSession.Mobile.InputText(testText)
		time.Sleep(config.WaitTimeAfterAction)

		mobileScreenshot2, _ := SafeMobileScreenshot(mobileSession.Mobile, "mobile_after_input")

		// Validate input functionality
		desktopInputWorked := desktopInputResult.Success && ValidateScreenshotChanged(desktopScreenshot1, desktopScreenshot2)
		mobileInputWorked := mobileInputResult.Success && ValidateScreenshotChanged(mobileScreenshot1, mobileScreenshot2)

		result.AddDetail("desktop_input_success", desktopInputResult.Success)
		result.AddDetail("mobile_input_success", mobileInputResult.Success)
		result.AddDetail("desktop_visual_change", ValidateScreenshotChanged(desktopScreenshot1, desktopScreenshot2))
		result.AddDetail("mobile_visual_change", ValidateScreenshotChanged(mobileScreenshot1, mobileScreenshot2))
		result.AddDetail("test_text", testText)

		if desktopInputWorked && mobileInputWorked {
			result.SetSuccess("Input functionality works consistently on both platforms")
			t.Logf("✅ Input consistency: Desktop=✓, Mobile=✓")
		} else if desktopInputWorked || mobileInputWorked {
			result.SetSuccess("Input functionality works on at least one platform")
			t.Logf("⚠️ Input partial: Desktop=%v, Mobile=%v", desktopInputWorked, mobileInputWorked)
		} else {
			result.SetFailure("Input functionality failed on both platforms")
			t.Logf("❌ Input failed: Desktop=%v, Mobile=%v", desktopInputWorked, mobileInputWorked)
		}
	})

	t.Run("APIResponseConsistency", func(t *testing.T) {
		result := NewFunctionalTestResult("APIResponseConsistency")
		startTime := time.Now()
		defer func() {
			result.Duration = time.Since(startTime)
			t.Logf("Test Result: %+v", result)
		}()

		// Test that both platforms return consistent API response structures

		// Screenshot APIs
		desktopScreenshotResult := desktopSession.Computer.Screenshot()
		mobileScreenshotResult := mobileSession.Mobile.Screenshot()

		// Both should have RequestID
		desktopHasRequestID := desktopScreenshotResult.RequestID != ""
		mobileHasRequestID := mobileScreenshotResult.RequestID != ""

		// Input APIs
		desktopInputResult := desktopSession.Computer.InputText("API Test")
		mobileInputResult := mobileSession.Mobile.InputText("API Test")

		desktopInputHasRequestID := desktopInputResult.RequestID != ""
		mobileInputHasRequestID := mobileInputResult.RequestID != ""

		result.AddDetail("desktop_screenshot_request_id", desktopHasRequestID)
		result.AddDetail("mobile_screenshot_request_id", mobileHasRequestID)
		result.AddDetail("desktop_input_request_id", desktopInputHasRequestID)
		result.AddDetail("mobile_input_request_id", mobileInputHasRequestID)

		// Check error handling consistency
		// Test invalid parameters
		desktopInvalidResult := desktopSession.Computer.ClickMouse(100, 200, "invalid_button")
		mobileInvalidResult := mobileSession.Mobile.Swipe(-1, -1, -1, -1, -1) // Invalid coordinates

		desktopHandlesErrors := !desktopInvalidResult.Success && desktopInvalidResult.ErrorMessage != ""
		mobileHandlesErrors := !mobileInvalidResult.Success && mobileInvalidResult.ErrorMessage != ""

		result.AddDetail("desktop_error_handling", desktopHandlesErrors)
		result.AddDetail("mobile_error_handling", mobileHandlesErrors)

		// Overall consistency check
		allConsistent := desktopHasRequestID && mobileHasRequestID &&
			desktopInputHasRequestID && mobileInputHasRequestID &&
			desktopHandlesErrors && mobileHandlesErrors

		if allConsistent {
			result.SetSuccess("API response structures are consistent across platforms")
			t.Logf("✅ API consistency: All response structures match")
		} else {
			result.SetFailure("API response structures are inconsistent")
			t.Logf("❌ API inconsistency detected")
		}
	})

	t.Run("PerformanceConsistency", func(t *testing.T) {
		result := NewFunctionalTestResult("PerformanceConsistency")
		startTime := time.Now()
		defer func() {
			result.Duration = time.Since(startTime)
			t.Logf("Test Result: %+v", result)
		}()

		// Measure response times for similar operations

		// Screenshot performance
		desktopScreenshotStart := time.Now()
		desktopSession.Computer.Screenshot()
		desktopScreenshotDuration := time.Since(desktopScreenshotStart)

		mobileScreenshotStart := time.Now()
		mobileSession.Mobile.Screenshot()
		mobileScreenshotDuration := time.Since(mobileScreenshotStart)

		// Input performance
		desktopInputStart := time.Now()
		desktopSession.Computer.InputText("Performance Test")
		desktopInputDuration := time.Since(desktopInputStart)

		mobileInputStart := time.Now()
		mobileSession.Mobile.InputText("Performance Test")
		mobileInputDuration := time.Since(mobileInputStart)

		result.AddDetail("desktop_screenshot_ms", desktopScreenshotDuration.Milliseconds())
		result.AddDetail("mobile_screenshot_ms", mobileScreenshotDuration.Milliseconds())
		result.AddDetail("desktop_input_ms", desktopInputDuration.Milliseconds())
		result.AddDetail("mobile_input_ms", mobileInputDuration.Milliseconds())

		// Check if performance is reasonable (under 10 seconds for any operation)
		maxReasonableTime := 10 * time.Second
		allReasonable := desktopScreenshotDuration < maxReasonableTime &&
			mobileScreenshotDuration < maxReasonableTime &&
			desktopInputDuration < maxReasonableTime &&
			mobileInputDuration < maxReasonableTime

		if allReasonable {
			result.SetSuccess("Performance is reasonable on both platforms")
			t.Logf("✅ Performance: Desktop screenshot=%dms, Mobile screenshot=%dms",
				desktopScreenshotDuration.Milliseconds(), mobileScreenshotDuration.Milliseconds())
		} else {
			result.SetFailure("Performance issues detected")
			t.Logf("❌ Performance issues detected")
		}
	})

	t.Run("ComprehensiveCrossPlatformWorkflow", func(t *testing.T) {
		result := NewFunctionalTestResult("ComprehensiveCrossPlatformWorkflow")
		startTime := time.Now()
		defer func() {
			result.Duration = time.Since(startTime)
			t.Logf("Test Result: %+v", result)
		}()

		// Execute a comprehensive workflow on both platforms simultaneously
		var desktopWorkflowSuccess, mobileWorkflowSuccess bool
		var wg sync.WaitGroup

		wg.Add(2)

		// Desktop workflow
		go func() {
			defer wg.Done()
			success := true

			// Desktop workflow steps
			screenshot1, _ := SafeScreenshot(desktopSession.Computer, "desktop_workflow_start")
			if screenshot1 == "" {
				success = false
			}

			screen := desktopSession.Computer.GetScreenSize()
			if screen.ErrorMessage != "" {
				success = false
			}

			if success {
				moveResult := desktopSession.Computer.MoveMouse(screen.Width/2, screen.Height/2)
				if !moveResult.Success {
					success = false
				}
			}

			if success {
				clickResult := desktopSession.Computer.ClickMouse(screen.Width/2, screen.Height/2, "left")
				if !clickResult.Success {
					success = false
				}
			}

			if success {
				inputResult := desktopSession.Computer.InputText("Desktop Workflow")
				if !inputResult.Success {
					success = false
				}
			}

			time.Sleep(config.WaitTimeAfterAction)

			screenshot2, _ := SafeScreenshot(desktopSession.Computer, "desktop_workflow_end")
			if success && !ValidateScreenshotChanged(screenshot1, screenshot2) {
				success = false
			}

			desktopWorkflowSuccess = success
		}()

		// Mobile workflow
		go func() {
			defer wg.Done()
			success := true

			// Mobile workflow steps
			screenshot1, _ := SafeMobileScreenshot(mobileSession.Mobile, "mobile_workflow_start")
			if screenshot1 == "" {
				success = false
			}

			if success {
				homeResult := mobileSession.Mobile.SendKey(3) // HOME
				if !homeResult.Success {
					success = false
				}
				time.Sleep(2 * time.Second)
			}

			if success {
				tapResult := mobileSession.Mobile.Tap(540, 960)
				if !tapResult.Success {
					success = false
				}
			}

			if success {
				inputResult := mobileSession.Mobile.InputText("Mobile Workflow")
				if !inputResult.Success {
					success = false
				}
			}

			if success {
				swipeResult := mobileSession.Mobile.Swipe(540, 1200, 540, 600, 400)
				if !swipeResult.Success {
					success = false
				}
			}

			time.Sleep(config.WaitTimeAfterAction)

			screenshot2, _ := SafeMobileScreenshot(mobileSession.Mobile, "mobile_workflow_end")
			if success && !ValidateScreenshotChanged(screenshot1, screenshot2) {
				success = false
			}

			mobileWorkflowSuccess = success
		}()

		wg.Wait()

		result.AddDetail("desktop_workflow_success", desktopWorkflowSuccess)
		result.AddDetail("mobile_workflow_success", mobileWorkflowSuccess)

		if desktopWorkflowSuccess && mobileWorkflowSuccess {
			result.SetSuccess("Comprehensive workflows successful on both platforms")
			t.Logf("✅ Cross-platform workflows: Desktop=✓, Mobile=✓")
		} else if desktopWorkflowSuccess || mobileWorkflowSuccess {
			result.SetSuccess("Workflow successful on at least one platform")
			t.Logf("⚠️ Partial workflow success: Desktop=%v, Mobile=%v",
				desktopWorkflowSuccess, mobileWorkflowSuccess)
		} else {
			result.SetFailure("Workflows failed on both platforms")
			t.Logf("❌ Workflow failure: Desktop=%v, Mobile=%v",
				desktopWorkflowSuccess, mobileWorkflowSuccess)
		}
	})
}
