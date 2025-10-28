package integration_test

import (
	"fmt"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

func TestWindow_WindowOperations(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a session
	fmt.Println("Creating a new session for window operations testing...")
	params := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	sessionResult, err := agentBay.Create(params)
	if err != nil {
		t.Fatalf("Error creating session: %v", err)
	}
	session := sessionResult.Session
	t.Logf("Session created with ID: %s (RequestID: %s)",
		session.SessionID, sessionResult.RequestID)

	// IMPORTANT: Ensure cleanup of the session after test
	defer func() {
		fmt.Println("Cleaning up: Deleting the session...")
		deleteResult, err := agentBay.Delete(session)
		if err != nil {
			t.Logf("Warning: Error deleting session: %v", err)
		} else {
			t.Logf("Session successfully deleted (RequestID: %s)",
				deleteResult.RequestID)
		}
	}()

	// Test window operations
	if session.Window != nil && session.Application != nil {
		// First, start Google Chrome
		fmt.Println("Starting Google Chrome application...")
		startCmd := "/usr/bin/google-chrome-stable"
		chromeResult, err := session.Application.StartApp(startCmd, "", "")
		if err != nil {
			t.Logf("Note: Failed to start Google Chrome: %v", err)
			t.Logf("Continuing with existing windows...")
		} else {
			chromeProcesses := chromeResult.Processes
			t.Logf("Google Chrome started successfully, returned %d processes (RequestID: %s)",
				len(chromeProcesses), chromeResult.RequestID)

			// Give Chrome some time to initialize
			time.Sleep(10 * time.Second)

			// Clean up Chrome processes at the end
			defer func() {
				for _, proc := range chromeProcesses {
					if proc.PID > 0 {
						fmt.Printf("Attempting to stop Chrome process (PID: %d)...\n", proc.PID)
						stopResult, err := session.Application.StopAppByPID(proc.PID)
						if err != nil {
							t.Logf("Warning: Failed to stop Chrome process: %v", err)
						} else {
							t.Logf("Successfully stopped Chrome process (PID: %d) (RequestID: %s)",
								proc.PID, stopResult.RequestID)
						}
					}
				}
			}()
		}

		// Get a list of root windows
		windowsResult, err := session.Window.ListRootWindows()
		if err != nil {
			t.Logf("Note: ListRootWindows failed: %v", err)
			return
		}

		windows := windowsResult.Windows
		// Debug the response structure
		t.Logf("ListRootWindows response type: %T (RequestID: %s)",
			windows, windowsResult.RequestID)

		if len(windows) == 0 {
			t.Logf("No windows available for testing window operations")
			return
		}

		// Try to find a Chrome window for testing
		var windowID int
		var windowFound bool
		for _, window := range windows {
			// Debug the window structure
			t.Logf("Window: %s (ID: %d, Process: %s, PID: %d)",
				window.Title, window.WindowID, window.PName, window.PID)

			if window.PName == "chrome" {
				windowID = window.WindowID
				windowFound = true
				t.Logf("Found Chrome window with ID %d for testing window operations", windowID)
				break
			}
		}

		// If no Chrome window found, use the first window
		if !windowFound && len(windows) > 0 {
			firstWindow := windows[0]
			windowID = firstWindow.WindowID
			t.Logf("No Chrome window found, using window with ID %d for testing window operations", windowID)
			windowFound = true
		}

		if !windowFound {
			t.Logf("No suitable windows found for testing")
			return
		}

		// Test RestoreWindow
		fmt.Printf("Restoring window with ID %d...\n", windowID)
		restoreResult, err := session.Window.RestoreWindow(windowID)
		if err != nil {
			t.Logf("Note: RestoreWindow failed: %v", err)
		} else {
			t.Logf("Window restored successfully (RequestID: %s)", restoreResult.RequestID)
		}
		// Wait for 3 seconds to allow user to see the result
		time.Sleep(3 * time.Second)

		// Test ResizeWindow
		fmt.Printf("Resizing window with ID %d to 800x600...\n", windowID)
		resizeResult, err := session.Window.ResizeWindow(windowID, 800, 600)
		if err != nil {
			t.Logf("Note: ResizeWindow failed: %v", err)
		} else {
			t.Logf("Window resized successfully (RequestID: %s)", resizeResult.RequestID)
		}
		// Wait for 3 seconds to allow user to see the result
		time.Sleep(3 * time.Second)

		// Test MinimizeWindow
		fmt.Printf("Minimizing window with ID %d...\n", windowID)
		minimizeResult, err := session.Window.MinimizeWindow(windowID)
		if err != nil {
			t.Logf("Note: MinimizeWindow failed: %v", err)
		} else {
			t.Logf("Window minimized successfully (RequestID: %s)", minimizeResult.RequestID)
		}
		// Wait for 3 seconds to allow user to see the result
		time.Sleep(3 * time.Second)

		// Test MaximizeWindow
		fmt.Printf("Maximizing window with ID %d...\n", windowID)
		maximizeResult, err := session.Window.MaximizeWindow(windowID)
		if err != nil {
			t.Logf("Note: MaximizeWindow failed: %v", err)
		} else {
			t.Logf("Window maximized successfully (RequestID: %s)", maximizeResult.RequestID)
		}
		// Wait for 3 seconds to allow user to see the result
		time.Sleep(3 * time.Second)

		// Start a terminal
		fmt.Println("Starting gnome-terminal...")
		terminalResult, err := session.Application.StartApp("/usr/bin/gnome-terminal", "", "")
		if err != nil {
			t.Logf("Note: Failed to start gnome-terminal: %v", err)
		} else {
			terminalProcesses := terminalResult.Processes
			t.Logf("Terminal started successfully, returned %d processes (RequestID: %s)",
				len(terminalProcesses), terminalResult.RequestID)

			// Give terminal some time to initialize
			time.Sleep(3 * time.Second)

			// Clean up terminal processes at the end
			defer func() {
				for _, proc := range terminalProcesses {
					if proc.PID > 0 {
						fmt.Printf("Attempting to stop terminal process (PID: %d)...\n", proc.PID)
						stopResult, err := session.Application.StopAppByPID(proc.PID)
						if err != nil {
							t.Logf("Warning: Failed to stop terminal process: %v", err)
						} else {
							t.Logf("Successfully stopped terminal process (PID: %d) (RequestID: %s)",
								proc.PID, stopResult.RequestID)
						}
					}
				}
			}()
		}

		// Activate the Chrome window again
		fmt.Printf("Activating Chrome window with ID %d again...\n", windowID)
		activateResult, err := session.Window.ActivateWindow(windowID)
		if err != nil {
			t.Logf("Note: ActivateWindow failed: %v", err)
		} else {
			t.Logf("Window activated successfully (RequestID: %s)", activateResult.RequestID)
		}
		// Wait for 3 seconds to allow user to see the result
		time.Sleep(3 * time.Second)

		// Test FullscreenWindow
		fmt.Printf("Fullscreening window with ID %d...\n", windowID)
		fullscreenResult, err := session.Window.FullscreenWindow(windowID)
		if err != nil {
			t.Logf("Note: FullscreenWindow failed: %v", err)
		} else {
			t.Logf("Window fullscreened successfully (RequestID: %s)", fullscreenResult.RequestID)
		}
	} else {
		t.Logf("Window or Application interface is nil, skipping window operations test")
	}
}
