package main

import (
	"fmt"
	"os"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/application"
)

func main() {
	// Get API key from environment variable or use a default value for testing
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		apiKey = "akm-xxx" // Replace with your actual API key for testing
		fmt.Println("Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for production use.")
	}

	// Initialize the AgentBay client
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Create a new session with default parameters
	fmt.Println("\nCreating a new session...")
	params := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	sessionResult, err := agentBay.Create(params)
	if err != nil {
		fmt.Printf("\nError creating session: %v\n", err)
		os.Exit(1)
	}
	session := sessionResult.Session
	fmt.Printf("\nSession created with ID: %s\n", session.SessionID)

	// Complete Application-Window Workflow
	fmt.Println("\n=== Complete Application-Window Workflow ===")

	if session.Application != nil && session.Window != nil {
		// Step 1: Get installed applications
		fmt.Println("\nStep 1: Getting installed applications...")
		appsListResult, err := session.Application.GetInstalledApps(true, false, true)
		if err != nil {
			fmt.Printf("Error getting installed apps: %v\n", err)
		} else {
			fmt.Printf("Found %d installed applications (RequestID: %s)\n", len(appsListResult.Applications), appsListResult.RequestID)

			// Print the first 3 apps or fewer if less than 3 are available
			count := min(len(appsListResult.Applications), 3)
			for i := 0; i < count; i++ {
				fmt.Printf("App %d: %s\n", i+1, appsListResult.Applications[i].Name)
			}

			if len(appsListResult.Applications) > 0 {
				// Find an app with name "Google Chrome" to launch
				var appToStart *application.Application
				for _, app := range appsListResult.Applications {
					if app.Name == "Google Chrome" {
						appToStart = &app
						break
					}
				}

				if appToStart != nil {
					// Step 2: Start the application
					fmt.Printf("\nStep 2: Starting application: %s with command: %s\n", appToStart.Name, appToStart.CmdLine)
					startResult, err := session.Application.StartApp(appToStart.CmdLine, "", "")
					if err != nil {
						fmt.Printf("Error starting app: %v\n", err)
					} else {
						fmt.Printf("Application start result (RequestID: %s): %d processes started\n", startResult.RequestID, len(startResult.Processes))

						// Step 3: Wait for 1 minute
						fmt.Println("\nStep 3: Waiting for 1 minute for application to fully load...")
						time.Sleep(60 * time.Second)

						// Step 4: List root windows
						fmt.Println("\nStep 4: Listing root windows...")
						rootWindowsResult, err := session.Window.ListRootWindows()
						if err != nil {
							fmt.Printf("Error listing root windows: %v\n", err)
						} else {
							fmt.Printf("Found %d root windows (RequestID: %s)\n", len(rootWindowsResult.Windows), rootWindowsResult.RequestID)

							// Print the first 3 windows or fewer if less than 3 are available
							windowCount := min(len(rootWindowsResult.Windows), 3)
							for i := 0; i < windowCount; i++ {
								fmt.Printf("Window %d: %s (ID: %d)\n", i+1, rootWindowsResult.Windows[i].Title, rootWindowsResult.Windows[i].WindowID)
							}

							if len(rootWindowsResult.Windows) > 0 {
								// Step 5: Activate a window
								windowToActivate := rootWindowsResult.Windows[0]
								fmt.Printf("\nStep 5: Activating window: %s (ID: %d)\n", windowToActivate.Title, windowToActivate.WindowID)
								activateResult, err := session.Window.ActivateWindow(windowToActivate.WindowID)
								if err != nil {
									fmt.Printf("Error activating window: %v\n", err)
								} else {
									fmt.Printf("Window activated successfully (RequestID: %s)\n", activateResult.RequestID)
								}

								// Step 6: Get active window
								fmt.Println("\nStep 6: Getting active window...")
								activeWindowResult, err := session.Window.GetActiveWindow()
								if err != nil {
									fmt.Printf("Error getting active window: %v\n", err)
								} else if activeWindowResult != nil && activeWindowResult.Window != nil {
									fmt.Printf("Active window (RequestID: %s): %s (ID: %d, Process: %s, PID: %d)\n",
										activeWindowResult.RequestID,
										activeWindowResult.Window.Title,
										activeWindowResult.Window.WindowID,
										activeWindowResult.Window.PName,
										activeWindowResult.Window.PID)
								} else {
									fmt.Println("No active window found")
								}

								// Additional window operations with the first window
								windowID := rootWindowsResult.Windows[0].WindowID

								// Maximize window
								fmt.Printf("\nMaximizing window with ID %d...\n", windowID)
								maximizeResult, err := session.Window.MaximizeWindow(windowID)
								if err != nil {
									fmt.Printf("Error maximizing window: %v\n", err)
								} else {
									fmt.Printf("Window maximized successfully (RequestID: %s)\n", maximizeResult.RequestID)
								}

								// Minimize window
								fmt.Printf("\nMinimizing window with ID %d...\n", windowID)
								minimizeResult, err := session.Window.MinimizeWindow(windowID)
								if err != nil {
									fmt.Printf("Error minimizing window: %v\n", err)
								} else {
									fmt.Printf("Window minimized successfully (RequestID: %s)\n", minimizeResult.RequestID)
								}

								// Restore window
								fmt.Printf("\nRestoring window with ID %d...\n", windowID)
								restoreResult, err := session.Window.RestoreWindow(windowID)
								if err != nil {
									fmt.Printf("Error restoring window: %v\n", err)
								} else {
									fmt.Printf("Window restored successfully (RequestID: %s)\n", restoreResult.RequestID)
								}

								// Resize window
								fmt.Printf("\nResizing window with ID %d to 800x600...\n", windowID)
								resizeResult, err := session.Window.ResizeWindow(windowID, 800, 600)
								if err != nil {
									fmt.Printf("Error resizing window: %v\n", err)
								} else {
									fmt.Printf("Window resized successfully (RequestID: %s)\n", resizeResult.RequestID)
								}
							} else {
								fmt.Println("No root windows found after starting application")
							}
						}
					}
				} else {
					fmt.Println("No application with name 'Google Chrome' found, trying with first available app...")
					// Use the first available application as fallback
					appToStart = &appsListResult.Applications[0]
					fmt.Printf("Using fallback app: %s\n", appToStart.Name)
				}
			} else {
				fmt.Println("No installed applications found, skipping workflow")
			}
		}

		// List visible applications
		fmt.Println("\nListing visible applications...")
		visibleAppsResult, err := session.Application.ListVisibleApps()
		if err != nil {
			fmt.Printf("Error listing visible apps: %v\n", err)
		} else {
			fmt.Printf("Found %d visible applications\n", len(visibleAppsResult.Processes))
			// Print the first 3 apps or fewer if less than 3 are available
			count := min(len(visibleAppsResult.Processes), 3)
			for i := 0; i < count; i++ {
				fmt.Printf("Process %d: %s (PID: %d)\n", i+1, visibleAppsResult.Processes[i].PName, visibleAppsResult.Processes[i].PID)
			}
		}
	}

	// Focus mode operations
	fmt.Println("\n=== Focus Mode Operations ===")
	// Enable focus mode
	fmt.Println("\nEnabling focus mode...")
	focusEnableResult, err := session.Window.FocusMode(true)
	if err != nil {
		fmt.Printf("Error enabling focus mode: %v\n", err)
	} else {
		fmt.Printf("Focus mode enabled successfully (RequestID: %s)\n", focusEnableResult.RequestID)
	}

	// Disable focus mode
	fmt.Println("\nDisabling focus mode...")
	focusDisableResult, err := session.Window.FocusMode(false)
	if err != nil {
		fmt.Printf("Error disabling focus mode: %v\n", err)
	} else {
		fmt.Printf("Focus mode disabled successfully (RequestID: %s)\n", focusDisableResult.RequestID)
	}

	// Delete the session
	fmt.Println("\nDeleting the session...")
	deleteResult, err := session.Delete()
	if err != nil {
		fmt.Printf("Error deleting session: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Session deleted successfully (RequestID: %s)\n", deleteResult.RequestID)
}

// min returns the smaller of x or y.
func min(x, y int) int {
	if x < y {
		return x
	}
	return y
}
