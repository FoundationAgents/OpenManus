package integration

import (
	"os"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/stretchr/testify/require"
)

// TestMobileFunctionalValidation tests Mobile module functionality through state changes
// This test validates that operations actually work by checking their effects
func TestMobileFunctionalValidation(t *testing.T) {
	// Skip if no API key provided
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		t.Skip("Skipping functional validation test: AGENTBAY_API_KEY not set")
	}

	// Create AgentBay client and session
	agentBay, err := agentbay.NewAgentBay(apiKey)
	require.NoError(t, err, "Failed to create AgentBay client")

	sessionParams := &agentbay.CreateSessionParams{
		ImageId: "mobile_latest",
	}

	sessionResult, err := agentBay.Create(sessionParams)
	require.NoError(t, err, "Failed to create session")
	require.NotNil(t, sessionResult.Session, "Session should be created")

	session := sessionResult.Session
	defer func() {
		deleteResult, _ := session.Delete()
		if deleteResult != nil && deleteResult.RequestID != "" {
			t.Logf("Session %s deleted successfully", session.SessionID)
		}
	}()

	t.Logf("Created Mobile functional validation session: %s", session.SessionID)

	// Wait for mobile session to be ready (longer than desktop)
	time.Sleep(15 * time.Second)

	config := DefaultFunctionalTestConfig()

	t.Run("TouchFunctionalityValidation", func(t *testing.T) {
		result := NewFunctionalTestResult("TouchFunctionalityValidation")
		startTime := time.Now()
		defer func() {
			result.Duration = time.Since(startTime)
			t.Logf("Test Result: %+v", result)
		}()

		// Step 1: Get initial UI elements
		initialElements := session.Mobile.GetClickableUIElements(5000)
		if initialElements.ErrorMessage != "" {
			result.SetFailure("Failed to get initial UI elements: " + initialElements.ErrorMessage)
			return
		}
		result.AddDetail("initial_elements_count", len(initialElements.Elements))

		// Step 2: Press HOME key to change UI state
		homeResult := session.Mobile.SendKey(3) // HOME key
		if !homeResult.Success {
			result.SetFailure("Failed to send HOME key: " + homeResult.ErrorMessage)
			return
		}

		// Wait for UI to change
		time.Sleep(config.WaitTimeAfterAction)

		// Step 3: Get UI elements after HOME press
		afterHomeElements := session.Mobile.GetClickableUIElements(5000)
		if afterHomeElements.ErrorMessage != "" {
			result.SetFailure("Failed to get UI elements after HOME: " + afterHomeElements.ErrorMessage)
			return
		}
		result.AddDetail("after_home_elements_count", len(afterHomeElements.Elements))

		// Convert to comparable format
		initialUIElements := ConvertMobileUIElements(initialElements.Elements)
		afterHomeUIElements := ConvertMobileUIElements(afterHomeElements.Elements)

		// Validate UI change
		uiChanged := ValidateUIElementsChanged(initialUIElements, afterHomeUIElements, config.UIElementTolerance)
		result.AddDetail("ui_changed", uiChanged)

		if uiChanged {
			result.SetSuccess("Touch functionality validation successful")
			t.Logf("✅ HOME key changed UI: %d → %d elements",
				len(initialElements.Elements), len(afterHomeElements.Elements))
		} else {
			result.SetFailure("UI did not change as expected after HOME key")
			t.Logf("❌ HOME key failed: %d = %d elements",
				len(initialElements.Elements), len(afterHomeElements.Elements))
		}
	})

	t.Run("SwipeFunctionalityValidation", func(t *testing.T) {
		result := NewFunctionalTestResult("SwipeFunctionalityValidation")
		startTime := time.Now()
		defer func() {
			result.Duration = time.Since(startTime)
			t.Logf("Test Result: %+v", result)
		}()

		// Step 1: Get initial UI state
		initialElements := session.Mobile.GetAllUIElements(5000)
		if initialElements.ErrorMessage != "" {
			result.SetFailure("Failed to get initial UI elements: " + initialElements.ErrorMessage)
			return
		}
		result.AddDetail("initial_all_elements_count", len(initialElements.Elements))

		// Step 2: Perform swipe gesture (bottom to top - scroll up)
		swipeResult := session.Mobile.Swipe(540, 1500, 540, 500, 500) // Common mobile screen coordinates
		if !swipeResult.Success {
			result.SetFailure("Failed to perform swipe: " + swipeResult.ErrorMessage)
			return
		}

		// Wait for swipe animation to complete
		time.Sleep(config.WaitTimeAfterAction)

		// Step 3: Get UI elements after swipe
		afterSwipeElements := session.Mobile.GetAllUIElements(5000)
		if afterSwipeElements.ErrorMessage != "" {
			result.SetFailure("Failed to get UI elements after swipe: " + afterSwipeElements.ErrorMessage)
			return
		}
		result.AddDetail("after_swipe_elements_count", len(afterSwipeElements.Elements))

		// Convert to comparable format
		initialUIElements := ConvertMobileUIElements(initialElements.Elements)
		afterSwipeUIElements := ConvertMobileUIElements(afterSwipeElements.Elements)

		// Validate swipe effect
		uiChanged := ValidateUIElementsChanged(initialUIElements, afterSwipeUIElements, config.UIElementTolerance)
		result.AddDetail("swipe_changed_ui", uiChanged)

		if uiChanged {
			result.SetSuccess("Swipe functionality validation successful")
			t.Logf("✅ Swipe changed UI: %d → %d elements",
				len(initialElements.Elements), len(afterSwipeElements.Elements))
		} else {
			result.SetFailure("Swipe did not produce expected UI changes")
			t.Logf("❌ Swipe failed: %d = %d elements",
				len(initialElements.Elements), len(afterSwipeElements.Elements))
		}
	})

	t.Run("AppManagementValidation", func(t *testing.T) {
		result := NewFunctionalTestResult("AppManagementValidation")
		startTime := time.Now()
		defer func() {
			result.Duration = time.Since(startTime)
			t.Logf("Test Result: %+v", result)
		}()

		// Step 1: Get installed apps
		appsResult := session.Mobile.GetInstalledApps(false, true, false)
		if appsResult.ErrorMessage != "" || len(appsResult.Apps) == 0 {
			result.SetFailure("Failed to get installed apps or no apps found")
			return
		}
		result.AddDetail("installed_apps_count", len(appsResult.Apps))

		// Find a safe app to test (avoid system apps)
		var testApp *struct {
			Name     string
			StartCmd string
		}

		for _, app := range appsResult.Apps {
			// Look for common safe apps (avoid system/critical apps)
			if app.Name != "" && app.StartCmd != "" &&
				!contains([]string{"system", "android", "launcher", "settings"}, app.Name) {
				testApp = &struct {
					Name     string
					StartCmd string
				}{Name: app.Name, StartCmd: app.StartCmd}
				break
			}
		}

		if testApp == nil {
			result.SetFailure("No suitable test app found")
			return
		}
		result.AddDetail("test_app", testApp.Name)

		// Step 2: Get UI before app launch
		beforeLaunchUI := session.Mobile.GetClickableUIElements(3000)
		beforeUIElements := ConvertMobileUIElements(beforeLaunchUI.Elements)

		// Step 3: Launch app
		startResult := session.Mobile.StartApp(testApp.StartCmd, "", "")
		if startResult.ErrorMessage != "" {
			result.SetFailure("Failed to start app: " + startResult.ErrorMessage)
			return
		}

		// Wait for app to launch
		time.Sleep(3 * time.Second)

		// Step 4: Get UI after app launch
		afterLaunchUI := session.Mobile.GetClickableUIElements(3000)
		afterUIElements := ConvertMobileUIElements(afterLaunchUI.Elements)

		// Validate app launch
		appLaunched := ValidateAppLaunched(beforeUIElements, afterUIElements)
		result.AddDetail("app_launched", appLaunched)

		if !appLaunched {
			result.SetFailure("App launch did not change UI as expected")
			return
		}

		// Step 5: Stop app (if we have process info)
		if len(startResult.Processes) > 0 {
			stopResult := session.Mobile.StopAppByPName(startResult.Processes[0].PName)
			if stopResult.Success {
				result.AddDetail("app_stopped", true)
				t.Logf("App %s stopped successfully", testApp.Name)
			}
		}

		result.SetSuccess("App management validation successful")
		t.Logf("✅ App %s launched and UI changed significantly", testApp.Name)
	})

	t.Run("TextInputValidation", func(t *testing.T) {
		result := NewFunctionalTestResult("TextInputValidation")
		startTime := time.Now()
		defer func() {
			result.Duration = time.Since(startTime)
			t.Logf("Test Result: %+v", result)
		}()

		// Step 1: Take initial screenshot
		screenshot1, _ := SafeMobileScreenshot(session.Mobile, "before_input")
		result.AddDetail("screenshot1", screenshot1)

		// Step 2: Find a text input element
		elements := session.Mobile.GetClickableUIElements(5000)
		if elements.ErrorMessage != "" {
			result.SetFailure("Failed to get UI elements: " + elements.ErrorMessage)
			return
		}

		uiElements := ConvertMobileUIElements(elements.Elements)
		textInput := FindTextInputElement(uiElements)

		if textInput == nil {
			// If no text input found, try tapping center and input anyway
			tapResult := session.Mobile.Tap(540, 960) // Common center coordinates
			if !tapResult.Success {
				result.SetFailure("No text input found and failed to tap center")
				return
			}
			result.AddDetail("input_method", "center_tap")
		} else {
			// Tap on the text input element
			centerX, centerY := CalculateElementCenter(textInput)
			tapResult := session.Mobile.Tap(centerX, centerY)
			if !tapResult.Success {
				result.SetFailure("Failed to tap text input element")
				return
			}
			result.AddDetail("input_method", "text_element_tap")
			result.AddDetail("text_element", map[string]interface{}{
				"text": textInput.Text, "class": textInput.ClassName,
			})
		}

		time.Sleep(1 * time.Second)

		// Step 3: Input test text
		testText := "Mobile Test Input"
		inputResult := session.Mobile.InputText(testText)
		if !inputResult.Success {
			result.SetFailure("Failed to input text: " + inputResult.ErrorMessage)
			return
		}
		result.AddDetail("input_text", testText)

		time.Sleep(config.WaitTimeAfterAction)

		// Step 4: Take screenshot after input
		screenshot2, _ := SafeMobileScreenshot(session.Mobile, "after_input")
		result.AddDetail("screenshot2", screenshot2)

		// Step 5: Clear text (select all and delete)
		// Send Ctrl+A equivalent or select all
		_ = session.Mobile.SendKey(1) // May vary by Android version
		time.Sleep(500 * time.Millisecond)

		// Delete text
		deleteResult := session.Mobile.SendKey(67) // KEYCODE_DEL
		if deleteResult.Success {
			time.Sleep(config.WaitTimeAfterAction)
		}

		// Step 6: Take final screenshot
		screenshot3, _ := SafeMobileScreenshot(session.Mobile, "after_delete")
		result.AddDetail("screenshot3", screenshot3)

		// Validate text input
		inputChanged := ValidateScreenshotChanged(screenshot1, screenshot2)
		deleteChanged := ValidateScreenshotChanged(screenshot2, screenshot3)

		result.AddDetail("input_changed_screen", inputChanged)
		result.AddDetail("delete_changed_screen", deleteChanged)

		if inputChanged {
			result.SetSuccess("Text input validation successful")
			t.Logf("✅ Text input changed screen content")
		} else {
			result.SetFailure("Text input did not produce visible changes")
			t.Logf("❌ Text input validation failed")
		}
	})

	t.Run("ScreenshotContentValidation", func(t *testing.T) {
		result := NewFunctionalTestResult("ScreenshotContentValidation")
		startTime := time.Now()
		defer func() {
			result.Duration = time.Since(startTime)
			t.Logf("Test Result: %+v", result)
		}()

		// Step 1: Take initial screenshot
		screenshot1, err := SafeMobileScreenshot(session.Mobile, "initial")
		if err != nil || screenshot1 == "" {
			result.SetFailure("Failed to take initial screenshot")
			return
		}
		result.AddDetail("screenshot1_url", screenshot1)

		// Step 2: Perform visible action (tap somewhere)
		tapResult := session.Mobile.Tap(400, 800) // Safe coordinates
		if !tapResult.Success {
			result.SetFailure("Failed to tap screen: " + tapResult.ErrorMessage)
			return
		}

		time.Sleep(config.WaitTimeAfterAction)

		// Step 3: Take second screenshot
		screenshot2, err := SafeMobileScreenshot(session.Mobile, "after_tap")
		if err != nil || screenshot2 == "" {
			result.SetFailure("Failed to take second screenshot")
			return
		}
		result.AddDetail("screenshot2_url", screenshot2)

		// Validate screenshot change
		if ValidateScreenshotChanged(screenshot1, screenshot2) {
			result.SetSuccess("Mobile screenshot content validation successful")
			t.Logf("✅ Mobile screenshots changed: %s → %s", screenshot1, screenshot2)
		} else {
			result.SetFailure("Mobile screenshots did not change as expected")
			t.Logf("❌ Mobile screenshots unchanged: %s = %s", screenshot1, screenshot2)
		}
	})

	t.Run("CompleteMobileWorkflowValidation", func(t *testing.T) {
		result := NewFunctionalTestResult("CompleteMobileWorkflowValidation")
		startTime := time.Now()
		defer func() {
			result.Duration = time.Since(startTime)
			t.Logf("Test Result: %+v", result)
		}()

		workflowSteps := []string{}
		screenshots := make(map[string]string)

		// Step 1: Initial state
		screenshot, _ := SafeMobileScreenshot(session.Mobile, "mobile_workflow_start")
		screenshots["start"] = screenshot
		workflowSteps = append(workflowSteps, "Initial mobile screenshot")

		// Step 2: Go to home screen
		homeResult := session.Mobile.SendKey(3) // HOME
		if homeResult.Success {
			workflowSteps = append(workflowSteps, "Pressed HOME key")
			time.Sleep(2 * time.Second)
		}

		// Step 3: Get home screen elements
		homeElements := session.Mobile.GetClickableUIElements(3000)
		if homeElements.ErrorMessage == "" && len(homeElements.Elements) > 0 {
			workflowSteps = append(workflowSteps, "Retrieved home screen elements")
			result.AddDetail("home_elements_count", len(homeElements.Elements))

			// Step 4: Tap on first safe element
			uiElements := ConvertMobileUIElements(homeElements.Elements)
			if len(uiElements) > 0 {
				firstElement := uiElements[0]
				if ValidateElementBounds(&firstElement, 1080, 1920) { // Common mobile resolution
					centerX, centerY := CalculateElementCenter(&firstElement)
					tapResult := session.Mobile.Tap(centerX, centerY)
					if tapResult.Success {
						workflowSteps = append(workflowSteps, "Tapped first element")
						time.Sleep(2 * time.Second)
					}
				}
			}
		}

		// Step 5: Perform swipe gesture
		swipeResult := session.Mobile.Swipe(540, 1200, 540, 600, 400)
		if swipeResult.Success {
			workflowSteps = append(workflowSteps, "Performed swipe gesture")
			time.Sleep(1 * time.Second)
		}

		// Step 6: Input some text
		inputResult := session.Mobile.InputText("Mobile Workflow Test")
		if inputResult.Success {
			workflowSteps = append(workflowSteps, "Input test text")
			time.Sleep(config.WaitTimeAfterAction)
		}

		// Step 7: Press BACK key
		backResult := session.Mobile.SendKey(4) // BACK
		if backResult.Success {
			workflowSteps = append(workflowSteps, "Pressed BACK key")
			time.Sleep(1 * time.Second)
		}

		// Step 8: Final screenshot
		screenshot, _ = SafeMobileScreenshot(session.Mobile, "mobile_workflow_end")
		screenshots["end"] = screenshot

		// Validate workflow
		workflowChanged := ValidateScreenshotChanged(screenshots["start"], screenshots["end"])

		result.AddDetail("workflow_steps", workflowSteps)
		result.AddDetail("screenshots", screenshots)
		result.AddDetail("workflow_changed", workflowChanged)

		if len(workflowSteps) >= 5 && workflowChanged {
			result.SetSuccess("Complete mobile workflow validation successful")
			t.Logf("✅ Mobile workflow completed: %d steps, visual changes confirmed", len(workflowSteps))
		} else {
			result.SetFailure("Mobile workflow validation failed")
			t.Logf("❌ Mobile workflow failed: %d steps, changed=%v", len(workflowSteps), workflowChanged)
		}
	})
}

// Helper function to check if a string slice contains a substring
func contains(slice []string, item string) bool {
	for _, s := range slice {
		if len(s) > 0 && len(item) > 0 &&
			(s == item ||
				(len(item) > len(s) && item[:len(s)] == s) ||
				(len(s) > len(item) && s[:len(item)] == item)) {
			return true
		}
	}
	return false
}
