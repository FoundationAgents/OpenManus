package agentbay_test

import (
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

func TestApplication_GetInstalledApps(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a session with ImageId set to linux_latest
	fmt.Println("Creating a new session for application testing...")
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	result, err := agentBay.Create(sessionParams)
	if err != nil {
		t.Fatalf("Error creating session: %v", err)
	}

	session := result.Session
	t.Logf("Session created with ID: %s", session.SessionID)

	// IMPORTANT: Ensure cleanup of the session after test
	defer func() {
		fmt.Println("Cleaning up: Deleting the session...")
		_, err := agentBay.Delete(session)
		if err != nil {
			t.Logf("Warning: Error deleting session: %v", err)
		} else {
			t.Log("Session successfully deleted")
		}
	}()

	// Test GetInstalledApps
	if session.Application != nil {
		fmt.Println("Getting installed applications...")
		appsResult, err := session.Application.GetInstalledApps(true, false, true)
		if err != nil {
			t.Logf("Note: GetInstalledApps failed: %v", err)
		} else {
			t.Logf("Got response content with RequestID: %s", appsResult.RequestID)

			apps := appsResult.Applications
			t.Logf("Found %d installed applications", len(apps))

			// Verify we got some apps
			if len(apps) == 0 {
				t.Logf("Warning: No installed applications found")
			} else {
				// Print the first 3 apps or fewer if less than 3 are available
				count := min(len(apps), 3)
				for i := 0; i < count; i++ {
					t.Logf("App %d: %s", i+1, apps[i].Name)
				}

				// Verify app properties
				for _, app := range apps {
					if app.Name == "" {
						t.Errorf("Found app with empty name")
					}
				}
			}

			// Check if response contains "tool not found"
			if len(apps) > 0 && testutil.ContainsToolNotFound(apps[0].Name) {
				t.Errorf("Application.GetInstalledApps returned 'tool not found'")
			}

			if appsResult.RequestID == "" {
				t.Errorf("GetInstalledApps method did not return RequestID")
			}
		}
	} else {
		t.Logf("Note: Application interface is nil, skipping application test")
	}
}

func TestApplication_ListVisibleApps(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a session with ImageId set to linux_latest
	fmt.Println("Creating a new session for visible apps testing...")
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	result, err := agentBay.Create(sessionParams)
	if err != nil {
		t.Fatalf("Error creating session: %v", err)
	}

	session := result.Session
	t.Logf("Session created with ID: %s", session.SessionID)

	// IMPORTANT: Ensure cleanup of the session after test
	defer func() {
		fmt.Println("Cleaning up: Deleting the session...")
		_, err := agentBay.Delete(session)
		if err != nil {
			t.Logf("Warning: Error deleting session: %v", err)
		} else {
			t.Log("Session successfully deleted")
		}
	}()

	// Test ListVisibleApps
	if session.Application != nil {
		fmt.Println("Listing visible applications...")
		visibleResult, err := session.Application.ListVisibleApps()
		if err != nil {
			t.Logf("Note: ListVisibleApps failed: %v", err)
		} else {
			t.Logf("Got response content with RequestID: %s", visibleResult.RequestID)

			visibleApps := visibleResult.Processes
			t.Logf("Found %d visible applications", len(visibleApps))

			// Verify we got some apps
			if len(visibleApps) == 0 {
				t.Logf("Warning: No visible applications found")
			} else {
				// Print the first 3 apps or fewer if less than 3 are available
				count := min(len(visibleApps), 3)
				for i := 0; i < count; i++ {
					t.Logf("Process %d: %s (PID: %d)", i+1, visibleApps[i].PName, visibleApps[i].PID)
				}

				// Verify app properties
				for _, app := range visibleApps {
					if app.PName == "" {
						t.Errorf("Found app with empty process name")
					}
					if app.PID <= 0 {
						t.Errorf("Found app with invalid PID: %d", app.PID)
					}
				}
			}

			// Check if response contains "tool not found"
			if len(visibleApps) > 0 && testutil.ContainsToolNotFound(visibleApps[0].PName) {
				t.Errorf("Application.ListVisibleApps returned 'tool not found'")
			}

			if visibleResult.RequestID == "" {
				t.Errorf("ListVisibleApps method did not return RequestID")
			}
		}
	} else {
		t.Logf("Note: Application interface is nil, skipping application test")
	}
}

// min returns the smaller of x or y.
func min(x, y int) int {
	if x < y {
		return x
	}
	return y
}

func TestApplication_StartApp(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a session with ImageId set to linux_latest
	fmt.Println("Creating a new session for StartApp testing...")
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	result, err := agentBay.Create(sessionParams)
	if err != nil {
		t.Fatalf("Error creating session: %v", err)
	}

	session := result.Session
	t.Logf("Session created with ID: %s", session.SessionID)

	// IMPORTANT: Ensure cleanup of the session after test
	defer func() {
		fmt.Println("Cleaning up: Deleting the session...")
		_, err := agentBay.Delete(session)
		if err != nil {
			t.Logf("Warning: Error deleting session: %v", err)
		} else {
			t.Log("Session successfully deleted")
		}
	}()

	// Test StartApp with Google Chrome configuration
	if session.Application != nil {
		fmt.Println("Starting Google Chrome application...")

		// Define the start command from the provided JSON configuration
		startCmd := "/usr/bin/google-chrome-stable"

		// Call StartApp function
		processResult, err := session.Application.StartApp(startCmd, "", "")

		if err != nil {
			t.Logf("Note: StartApp failed: %v", err)

			// Check if the error is due to the tool not being found
			if err.Error() != "" && testutil.ContainsToolNotFound(err.Error()) {
				t.Logf("StartApp tool not found, skipping test")
				return
			}

			// Check if the error is due to Chrome not being installed
			if strings.Contains(err.Error(), "no such file") ||
				strings.Contains(err.Error(), "not found") {
				t.Logf("Google Chrome may not be installed on the test system, skipping test")
				return
			}
		} else {
			t.Logf("Got response content with RequestID: %s", processResult.RequestID)

			processes := processResult.Processes
			t.Logf("Application started successfully, returned %d processes", len(processes))

			// Verify we got some processes back
			if len(processes) == 0 {
				t.Logf("Warning: No processes returned after starting the application")
			} else {
				// Print the processes
				for i, process := range processes {
					t.Logf("Process %d: %s (PID: %d)", i+1, process.PName, process.PID)

					// Verify process properties
					if process.PName == "" {
						t.Errorf("Found process with empty process name")
					}
					if process.PID <= 0 {
						t.Errorf("Found process with invalid PID: %d", process.PID)
					}

					// Try to stop the process to clean up
					if process.PID > 0 {
						fmt.Printf("Attempting to stop process %s (PID: %d)...\n", process.PName, process.PID)
						stopResult, stopErr := session.Application.StopAppByPID(process.PID)
						if stopErr != nil {
							t.Logf("Warning: Failed to stop process: %v", stopErr)
						} else {
							t.Logf("Successfully stopped process %s (PID: %d) with RequestID: %s",
								process.PName, process.PID, stopResult.RequestID)
						}
					}
				}
			}

			// Check if response contains "tool not found"
			if len(processes) > 0 && testutil.ContainsToolNotFound(processes[0].PName) {
				t.Errorf("Application.StartApp returned 'tool not found'")
			}

			if processResult.RequestID == "" {
				t.Errorf("StartApp method did not return RequestID")
			}
		}
	} else {
		t.Logf("Note: Application interface is nil, skipping application test")
	}
}

func TestApplication_StopAppByPName(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a session with ImageId set to linux_latest
	fmt.Println("Creating a new session for StopAppByPName testing...")
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	result, err := agentBay.Create(sessionParams)
	if err != nil {
		t.Fatalf("Error creating session: %v", err)
	}

	session := result.Session
	t.Logf("Session created with ID: %s", session.SessionID)

	// IMPORTANT: Ensure cleanup of the session after test
	defer func() {
		fmt.Println("Cleaning up: Deleting the session...")
		_, err := agentBay.Delete(session)
		if err != nil {
			t.Logf("Warning: Error deleting session: %v", err)
		} else {
			t.Log("Session successfully deleted")
		}
	}()

	// Test StopAppByPName
	if session.Application != nil {
		// First, start an application to get a process to stop
		fmt.Println("Starting Google Chrome application...")
		startCmd := "/usr/bin/google-chrome-stable"
		startResult, err := session.Application.StartApp(startCmd, "", "")

		if err != nil {
			t.Logf("Note: StartApp failed: %v", err)

			// Check if the error is due to the tool not being found
			if err.Error() != "" && testutil.ContainsToolNotFound(err.Error()) {
				t.Logf("StartApp tool not found, skipping test")
				return
			}

			// Check if the error is due to Chrome not being installed
			if strings.Contains(err.Error(), "no such file") ||
				strings.Contains(err.Error(), "not found") {
				t.Logf("Google Chrome may not be installed on the test system, skipping test")
				return
			}
		} else {
			processes := startResult.Processes
			t.Logf("Application started successfully, returned %d processes", len(processes))

			// Verify we got some processes back
			if len(processes) == 0 {
				t.Logf("Warning: No processes returned after starting the application")
				return
			}

			// Get the process name to stop
			processToStop := processes[0].PName
			t.Logf("Attempting to stop process by name: %s", processToStop)

			// Call StopAppByPName function
			stopResult, err := session.Application.StopAppByPName(processToStop)
			if err != nil {
				t.Errorf("StopAppByPName failed: %v", err)

				// Check if the error is due to the tool not being found
				if err.Error() != "" && testutil.ContainsToolNotFound(err.Error()) {
					t.Logf("StopAppByPName tool not found, skipping test")
					return
				}
			} else {
				t.Logf("Got response content with RequestID: %s", stopResult.RequestID)
				t.Logf("Successfully stopped process by name: %s", processToStop)

				// Verify the process was stopped by listing visible apps
				time.Sleep(1 * time.Second) // Give some time for the process to be terminated
				visibleResult, err := session.Application.ListVisibleApps()
				if err != nil {
					t.Logf("Warning: Failed to list visible apps after stopping: %v", err)
				} else {
					visibleApps := visibleResult.Processes

					// Check if the process is still in the list
					processStillRunning := false
					for _, app := range visibleApps {
						if app.PName == processToStop {
							processStillRunning = true
							break
						}
					}

					if processStillRunning {
						t.Logf("Warning: Process %s is still running after StopAppByPName", processToStop)
					} else {
						t.Logf("Confirmed process %s is no longer running", processToStop)
					}
				}

				if stopResult.RequestID == "" {
					t.Errorf("StopAppByPName method did not return RequestID")
				}
			}
		}
	} else {
		t.Logf("Note: Application interface is nil, skipping application test")
	}
}
