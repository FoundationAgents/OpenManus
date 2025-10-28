package integration

import (
	"os"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/stretchr/testify/require"
)

// TestComputerFunctionalValidation tests Computer module functionality through state changes
// This test validates that operations actually work by checking their effects
func TestComputerFunctionalValidation(t *testing.T) {
	// Skip if no API key provided
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		t.Skip("Skipping functional validation test: AGENTBAY_API_KEY not set")
	}

	// Create AgentBay client and session
	agentBay, err := agentbay.NewAgentBay(apiKey)
	require.NoError(t, err, "Failed to create AgentBay client")

	sessionParams := &agentbay.CreateSessionParams{
		ImageId: "linux_latest",
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

	t.Logf("Created Computer functional validation session: %s", session.SessionID)

	// Wait for session to be ready
	time.Sleep(10 * time.Second)

	config := DefaultFunctionalTestConfig()

	t.Run("MouseMovementValidation", func(t *testing.T) {
		result := NewFunctionalTestResult("MouseMovementValidation")
		startTime := time.Now()
		defer func() {
			result.Duration = time.Since(startTime)
			t.Logf("Test Result: %+v", result)
		}()

		// Step 1: Get initial cursor position
		initialCursor := session.Computer.GetCursorPosition()
		if initialCursor.ErrorMessage != "" {
			result.SetFailure("Failed to get initial cursor position: " + initialCursor.ErrorMessage)
			return
		}
		result.AddDetail("initial_cursor", map[string]int{"x": initialCursor.X, "y": initialCursor.Y})

		// Step 2: Get screen size for safe movement
		screen := session.Computer.GetScreenSize()
		if screen.ErrorMessage != "" || !ValidateScreenSize(screen) {
			result.SetFailure("Invalid screen size")
			return
		}
		result.AddDetail("screen_size", map[string]interface{}{
			"width": screen.Width, "height": screen.Height, "dpi": screen.DpiScalingFactor,
		})

		// Step 3: Move mouse to a different position (center of screen)
		targetX := screen.Width / 2
		targetY := screen.Height / 2
		moveResult := session.Computer.MoveMouse(targetX, targetY)
		if !moveResult.Success {
			result.SetFailure("Mouse move operation failed: " + moveResult.ErrorMessage)
			return
		}

		// Wait for movement to complete
		time.Sleep(config.WaitTimeAfterAction)

		// Step 4: Verify cursor position changed
		newCursor := session.Computer.GetCursorPosition()
		if newCursor.ErrorMessage != "" {
			result.SetFailure("Failed to get new cursor position: " + newCursor.ErrorMessage)
			return
		}
		result.AddDetail("new_cursor", map[string]int{"x": newCursor.X, "y": newCursor.Y})
		result.AddDetail("target_position", map[string]int{"x": targetX, "y": targetY})

		// Validate cursor movement
		if ValidateCursorPosition(newCursor, screen, targetX, targetY, config.CursorPositionTolerance) {
			result.SetSuccess("Mouse movement validated successfully")
			t.Logf("✅ Mouse moved from (%d,%d) to (%d,%d), target was (%d,%d)",
				initialCursor.X, initialCursor.Y, newCursor.X, newCursor.Y, targetX, targetY)
		} else {
			result.SetFailure("Cursor position validation failed")
			t.Logf("❌ Mouse movement failed: expected (%d,%d), got (%d,%d)",
				targetX, targetY, newCursor.X, newCursor.Y)
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
		screenshot1, err := SafeScreenshot(session.Computer, "initial")
		if err != nil || screenshot1 == "" {
			result.SetFailure("Failed to take initial screenshot")
			return
		}
		result.AddDetail("screenshot1_url", screenshot1)

		// Step 2: Perform a visible action (move mouse to corner)
		screen := session.Computer.GetScreenSize()
		if screen.ErrorMessage != "" {
			result.SetFailure("Failed to get screen size")
			return
		}

		// Move to top-left corner
		moveResult := session.Computer.MoveMouse(50, 50)
		if !moveResult.Success {
			result.SetFailure("Failed to move mouse: " + moveResult.ErrorMessage)
			return
		}

		// Wait for action to complete
		time.Sleep(config.WaitTimeAfterAction)

		// Step 3: Take second screenshot
		screenshot2, err := SafeScreenshot(session.Computer, "after_move")
		if err != nil || screenshot2 == "" {
			result.SetFailure("Failed to take second screenshot")
			return
		}
		result.AddDetail("screenshot2_url", screenshot2)

		// Validate screenshot change
		if ValidateScreenshotChanged(screenshot1, screenshot2) {
			result.SetSuccess("Screenshot content validation successful")
			t.Logf("✅ Screenshots changed: %s → %s", screenshot1, screenshot2)
		} else {
			result.SetFailure("Screenshots did not change as expected")
			t.Logf("❌ Screenshots unchanged: %s = %s", screenshot1, screenshot2)
		}
	})

	t.Run("KeyboardInputValidation", func(t *testing.T) {
		result := NewFunctionalTestResult("KeyboardInputValidation")
		startTime := time.Now()
		defer func() {
			result.Duration = time.Since(startTime)
			t.Logf("Test Result: %+v", result)
		}()

		// Step 1: Take initial screenshot
		screenshot1, _ := SafeScreenshot(session.Computer, "before_input")

		// Step 2: Click somewhere safe (center of screen) to focus
		screen := session.Computer.GetScreenSize()
		if screen.ErrorMessage != "" {
			result.SetFailure("Failed to get screen size")
			return
		}

		centerX := screen.Width / 2
		centerY := screen.Height / 2
		clickResult := session.Computer.ClickMouse(centerX, centerY, "left")
		if !clickResult.Success {
			result.SetFailure("Failed to click for focus: " + clickResult.ErrorMessage)
			return
		}

		time.Sleep(1 * time.Second)

		// Step 3: Input test text
		testText := "AgentBay Functional Test"
		inputResult := session.Computer.InputText(testText)
		if !inputResult.Success {
			result.SetFailure("Failed to input text: " + inputResult.ErrorMessage)
			return
		}
		result.AddDetail("input_text", testText)

		time.Sleep(config.WaitTimeAfterAction)

		// Step 4: Take screenshot after input
		screenshot2, _ := SafeScreenshot(session.Computer, "after_input")

		// Step 5: Select all text and delete it
		selectResult := session.Computer.PressKeys([]string{"Ctrl", "a"}, false)
		if !selectResult.Success {
			result.SetFailure("Failed to select all: " + selectResult.ErrorMessage)
			return
		}

		time.Sleep(500 * time.Millisecond)

		deleteResult := session.Computer.PressKeys([]string{"Delete"}, false)
		if !deleteResult.Success {
			result.SetFailure("Failed to delete text: " + deleteResult.ErrorMessage)
			return
		}

		time.Sleep(config.WaitTimeAfterAction)

		// Step 6: Take final screenshot
		screenshot3, _ := SafeScreenshot(session.Computer, "after_delete")

		// Validate keyboard operations
		inputChanged := ValidateScreenshotChanged(screenshot1, screenshot2)
		deleteChanged := ValidateScreenshotChanged(screenshot2, screenshot3)

		result.AddDetail("screenshots", map[string]string{
			"initial": screenshot1, "after_input": screenshot2, "after_delete": screenshot3,
		})
		result.AddDetail("input_changed", inputChanged)
		result.AddDetail("delete_changed", deleteChanged)

		if inputChanged && deleteChanged {
			result.SetSuccess("Keyboard input validation successful")
			t.Logf("✅ Keyboard operations validated: input changed screen, delete changed screen")
		} else {
			result.SetFailure("Keyboard operations did not produce expected visual changes")
			t.Logf("❌ Keyboard validation failed: input_changed=%v, delete_changed=%v",
				inputChanged, deleteChanged)
		}
	})

	t.Run("ScreenConsistencyValidation", func(t *testing.T) {
		result := NewFunctionalTestResult("ScreenConsistencyValidation")
		startTime := time.Now()
		defer func() {
			result.Duration = time.Since(startTime)
			t.Logf("Test Result: %+v", result)
		}()

		// Step 1: Get screen size
		screen := session.Computer.GetScreenSize()
		if screen.ErrorMessage != "" || !ValidateScreenSize(screen) {
			result.SetFailure("Invalid screen size: " + screen.ErrorMessage)
			return
		}
		result.AddDetail("screen", map[string]interface{}{
			"width": screen.Width, "height": screen.Height, "dpi": screen.DpiScalingFactor,
		})

		// Step 2: Test cursor positions at screen boundaries
		testPositions := []struct {
			name string
			x, y int
		}{
			{"top_left", 0, 0},
			{"top_right", screen.Width - 1, 0},
			{"bottom_left", 0, screen.Height - 1},
			{"bottom_right", screen.Width - 1, screen.Height - 1},
			{"center", screen.Width / 2, screen.Height / 2},
		}

		allValid := true
		positionResults := make(map[string]bool)

		for _, pos := range testPositions {
			// Move to position
			moveResult := session.Computer.MoveMouse(pos.x, pos.y)
			if !moveResult.Success {
				t.Logf("Failed to move to %s (%d,%d): %s", pos.name, pos.x, pos.y, moveResult.ErrorMessage)
				allValid = false
				positionResults[pos.name] = false
				continue
			}

			time.Sleep(500 * time.Millisecond)

			// Get cursor position
			cursor := session.Computer.GetCursorPosition()
			if cursor.ErrorMessage != "" {
				t.Logf("Failed to get cursor at %s: %s", pos.name, cursor.ErrorMessage)
				allValid = false
				positionResults[pos.name] = false
				continue
			}

			// Validate position
			valid := ValidateCursorPosition(cursor, screen, pos.x, pos.y, config.CursorPositionTolerance)
			positionResults[pos.name] = valid
			if !valid {
				allValid = false
				t.Logf("❌ Position %s: expected (%d,%d), got (%d,%d)",
					pos.name, pos.x, pos.y, cursor.X, cursor.Y)
			} else {
				t.Logf("✅ Position %s: (%d,%d) validated", pos.name, cursor.X, cursor.Y)
			}
		}

		result.AddDetail("position_results", positionResults)
		result.AddDetail("all_positions_valid", allValid)

		if allValid {
			result.SetSuccess("Screen consistency validation successful")
		} else {
			result.SetFailure("Some cursor positions failed validation")
		}
	})

	t.Run("CompleteWorkflowValidation", func(t *testing.T) {
		result := NewFunctionalTestResult("CompleteWorkflowValidation")
		startTime := time.Now()
		defer func() {
			result.Duration = time.Since(startTime)
			t.Logf("Test Result: %+v", result)
		}()

		// This test combines multiple operations to validate a complete workflow
		workflowSteps := []string{}
		screenshots := make(map[string]string)

		// Step 1: Initial state
		screenshot, _ := SafeScreenshot(session.Computer, "workflow_start")
		screenshots["start"] = screenshot
		workflowSteps = append(workflowSteps, "Initial screenshot taken")

		// Step 2: Get screen info and move to center
		screen := session.Computer.GetScreenSize()
		if screen.ErrorMessage != "" {
			result.SetFailure("Failed to get screen size")
			return
		}

		centerX := screen.Width / 2
		centerY := screen.Height / 2
		moveResult := session.Computer.MoveMouse(centerX, centerY)
		if moveResult.Success {
			workflowSteps = append(workflowSteps, "Moved mouse to center")
		}

		time.Sleep(1 * time.Second)

		// Step 3: Click and input text
		clickResult := session.Computer.ClickMouse(centerX, centerY, "left")
		if clickResult.Success {
			workflowSteps = append(workflowSteps, "Clicked at center")
		}

		inputResult := session.Computer.InputText("Workflow Test")
		if inputResult.Success {
			workflowSteps = append(workflowSteps, "Input text")
		}

		time.Sleep(config.WaitTimeAfterAction)

		// Step 4: Screenshot after input
		screenshot, _ = SafeScreenshot(session.Computer, "workflow_input")
		screenshots["after_input"] = screenshot

		// Step 5: Select and copy text
		selectResult := session.Computer.PressKeys([]string{"Ctrl", "a"}, false)
		if selectResult.Success {
			workflowSteps = append(workflowSteps, "Selected all text")
		}

		copyResult := session.Computer.PressKeys([]string{"Ctrl", "c"}, false)
		if copyResult.Success {
			workflowSteps = append(workflowSteps, "Copied text")
		}

		// Step 6: Delete and paste
		deleteResult := session.Computer.PressKeys([]string{"Delete"}, false)
		if deleteResult.Success {
			workflowSteps = append(workflowSteps, "Deleted text")
		}

		time.Sleep(1 * time.Second)

		pasteResult := session.Computer.PressKeys([]string{"Ctrl", "v"}, false)
		if pasteResult.Success {
			workflowSteps = append(workflowSteps, "Pasted text")
		}

		time.Sleep(config.WaitTimeAfterAction)

		// Step 7: Final screenshot
		screenshot, _ = SafeScreenshot(session.Computer, "workflow_end")
		screenshots["end"] = screenshot

		// Validate workflow
		inputChanged := ValidateScreenshotChanged(screenshots["start"], screenshots["after_input"])
		workflowCompleted := ValidateScreenshotChanged(screenshots["after_input"], screenshots["end"])

		result.AddDetail("workflow_steps", workflowSteps)
		result.AddDetail("screenshots", screenshots)
		result.AddDetail("input_changed", inputChanged)
		result.AddDetail("workflow_completed", workflowCompleted)

		if len(workflowSteps) >= 6 && inputChanged {
			result.SetSuccess("Complete workflow validation successful")
			t.Logf("✅ Workflow completed: %d steps, visual changes confirmed", len(workflowSteps))
		} else {
			result.SetFailure("Workflow validation failed")
			t.Logf("❌ Workflow failed: %d steps, input_changed=%v", len(workflowSteps), inputChanged)
		}
	})
}
