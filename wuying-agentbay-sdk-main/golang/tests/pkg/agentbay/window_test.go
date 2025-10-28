package agentbay_test

import (
	"fmt"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

// Window represents a window in the system (copy of the same struct from window package)
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

func TestWindow_ListRootWindows(t *testing.T) {
	// Setup session with cleanup and ImageId set to linux_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test Window list root windows functionality
	if session.Window != nil {
		fmt.Println("Listing root windows...")
		listResult, err := session.Window.ListRootWindows()
		if err != nil {
			t.Logf("Note: ListRootWindows failed: %v", err)
		} else {
			t.Logf("Found %d root windows (RequestID: %s)", len(listResult.Windows), listResult.RequestID)

			// Print the first window if available
			if len(listResult.Windows) > 0 {
				t.Logf("First window: ID=%d, Title=%s, PID=%d, PName=%s",
					listResult.Windows[0].WindowID,
					listResult.Windows[0].Title,
					listResult.Windows[0].PID,
					listResult.Windows[0].PName)
			}
		}
	} else {
		t.Logf("Note: Window interface is nil, skipping window test")
	}
}

func TestWindow_GetActiveWindow(t *testing.T) {
	// Setup session with cleanup and ImageId set to linux_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test Window get active window functionality
	if session.Window != nil {
		fmt.Println("Getting active window...")
		activeWindowResult, err := session.Window.GetActiveWindow()
		if err != nil {
			t.Logf("Note: GetActiveWindow failed: %v", err)
		} else {
			t.Logf("Active window (RequestID: %s):", activeWindowResult.RequestID)
			if activeWindowResult.Window != nil {
				t.Logf("Active window: %s (ID: %d, Process: %s, PID: %d)",
					activeWindowResult.Window.Title,
					activeWindowResult.Window.WindowID,
					activeWindowResult.Window.PName,
					activeWindowResult.Window.PID)

				// Verify window properties
				if activeWindowResult.Window.WindowID <= 0 {
					t.Errorf("Active window has invalid ID: %d", activeWindowResult.Window.WindowID)
				}
				if activeWindowResult.Window.PID <= 0 {
					t.Logf("Active window has PID: %d", activeWindowResult.Window.PID)
				}
			} else {
				t.Logf("No active window found")
			}
		}
	} else {
		t.Logf("Note: Window interface is nil, skipping window test")
	}
}

func TestWindow_ActivateWindow(t *testing.T) {
	// Setup session with cleanup and ImageId set to linux_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test Window activate window functionality
	if session.Window != nil && session.Application != nil {
		// Step 1: List available applications
		t.Logf("Step 1: Listing available applications...")
		appsResult, err := session.Application.GetInstalledApps(true, false, true)
		if err != nil {
			t.Logf("Note: ListApps failed: %v", err)
			return
		}
		t.Logf("Found %d applications (RequestID: %s)", len(appsResult.Applications), appsResult.RequestID)

		if len(appsResult.Applications) == 0 {
			t.Logf("No applications found, skipping window activation test")
			return
		}

		// Step 2: Start the application
		appToStart := appsResult.Applications[0]
		t.Logf("Step 2: Starting application: %s with command: %s", appToStart.Name, appToStart.CmdLine)
		startResult, err := session.Application.StartApp(appToStart.CmdLine, "", "")
		if err != nil {
			t.Logf("Note: StartApp failed: %v", err)
			return
		}
		t.Logf("Application start result (RequestID: %s): %d processes started", startResult.RequestID, len(startResult.Processes))

		// Step 3: Wait for 1 minute
		t.Logf("Step 3: Waiting for 1 minute for application to fully load...")
		testutil.SleepWithMessage(60, "Application is starting...")

		// Step 4: List root windows
		t.Logf("Step 4: Listing root windows...")
		listResult, err := session.Window.ListRootWindows()
		if err != nil {
			t.Logf("Note: ListRootWindows failed: %v", err)
			return
		}
		t.Logf("Found %d root windows (RequestID: %s)", len(listResult.Windows), listResult.RequestID)

		if len(listResult.Windows) == 0 {
			t.Logf("No root windows found after starting application")
			return
		}

		// Step 5: Activate a window
		windowToActivate := listResult.Windows[0]
		t.Logf("Step 5: Activating window: %s (ID: %d)", windowToActivate.Title, windowToActivate.WindowID)
		activateResult, err := session.Window.ActivateWindow(windowToActivate.WindowID)
		if err != nil {
			t.Logf("Note: ActivateWindow failed: %v", err)
		} else {
			t.Logf("Window activated successfully (RequestID: %s)", activateResult.RequestID)
		}

		// Step 6: Get active window
		t.Logf("Step 6: Getting active window...")
		activeWindowResult, err := session.Window.GetActiveWindow()
		if err != nil {
			t.Logf("Note: GetActiveWindow failed: %v", err)
		} else {
			t.Logf("Active window (RequestID: %s):", activeWindowResult.RequestID)
			if activeWindowResult.Window != nil {
				t.Logf("Active window: %s (ID: %d, Process: %s, PID: %d)",
					activeWindowResult.Window.Title,
					activeWindowResult.Window.WindowID,
					activeWindowResult.Window.PName,
					activeWindowResult.Window.PID)

				// Verify window properties
				if activeWindowResult.Window.WindowID <= 0 {
					t.Errorf("Active window has invalid ID: %d", activeWindowResult.Window.WindowID)
				}
				if activeWindowResult.Window.PID <= 0 {
					t.Logf("Active window has PID: %d", activeWindowResult.Window.PID)
				}
			}
		}
	} else {
		t.Logf("Note: Window or Application interface is nil, skipping window test")
	}
}

func TestWindow_FocusMode(t *testing.T) {
	// Setup session with cleanup and ImageId set to linux_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test FocusMode
	if session.Window != nil {
		// Enable focus mode
		fmt.Println("Enabling focus mode...")
		enableResult, err := session.Window.FocusMode(true)
		if err != nil {
			t.Logf("Note: FocusMode(true) failed: %v", err)
		} else {
			t.Logf("Focus mode enabled successfully (RequestID: %s)", enableResult.RequestID)
		}

		// Wait a short time
		fmt.Println("Waiting briefly...")
		testutil.SleepWithMessage(2, "Focus mode is active...")

		// Disable focus mode
		fmt.Println("Disabling focus mode...")
		disableResult, err := session.Window.FocusMode(false)
		if err != nil {
			t.Logf("Note: FocusMode(false) failed: %v", err)
		} else {
			t.Logf("Focus mode disabled successfully (RequestID: %s)", disableResult.RequestID)
		}
	} else {
		t.Logf("Note: Window interface is nil, skipping focus mode test")
	}
}
