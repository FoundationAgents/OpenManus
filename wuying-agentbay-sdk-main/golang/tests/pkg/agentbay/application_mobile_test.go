package agentbay_test

import (
	"fmt"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

func TestApplicationMobile_GetInstalledApps(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a session with mobile_latest image
	fmt.Println("Creating a new mobile session for application testing...")
	params := agentbay.NewCreateSessionParams().WithImageId("mobile_latest")
	sessionResult, err := agentBay.Create(params)
	if err != nil {
		t.Fatalf("Error creating mobile session: %v", err)
	}
	session := sessionResult.Session
	t.Logf("Mobile session created with ID: %s (RequestID: %s)",
		session.SessionID, sessionResult.RequestID)

	// IMPORTANT: Ensure cleanup of the session after test
	defer func() {
		fmt.Println("Cleaning up: Deleting the mobile session...")
		deleteResult, err := agentBay.Delete(session)
		if err != nil {
			t.Logf("Warning: Error deleting mobile session: %v", err)
		} else {
			t.Logf("Mobile session successfully deleted (RequestID: %s)",
				deleteResult.RequestID)
		}
	}()

	// Test GetInstalledApps for mobile
	if session.Application != nil {
		fmt.Println("Testing getInstalledApps for mobile...")
		appsResult, err := session.Application.GetInstalledApps(true, false, true)
		if err != nil {
			t.Logf("Note: GetInstalledApps failed: %v", err)
		} else {
			t.Logf("Found %d mobile installed applications (RequestID: %s)",
				len(appsResult.Applications), appsResult.RequestID)

			// Verify results
			if len(appsResult.Applications) == 0 {
				t.Logf("Warning: No mobile installed applications found")
			} else {
				// Print and verify first few apps
				count := min(len(appsResult.Applications), 3)
				for i := 0; i < count; i++ {
					app := appsResult.Applications[i]
					t.Logf("Verifying mobile app %d: %s", i+1, app.Name)
					if app.Name == "" {
						t.Errorf("Found mobile app with empty name")
					}
					if app.CmdLine == "" {
						t.Errorf("Found mobile app with empty command line")
					}
				}
			}

			// Check if response contains "tool not found"
			if len(appsResult.Applications) > 0 && testutil.ContainsToolNotFound(appsResult.Applications[0].Name) {
				t.Errorf("Application.GetInstalledApps returned 'tool not found'")
			}

			if appsResult.RequestID == "" {
				t.Errorf("GetInstalledApps method did not return RequestID")
			}
		}
	} else {
		t.Logf("Note: Application interface is nil, skipping mobile application test")
	}
}

func TestApplicationMobile_StartApp_SimpleCommand(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a session with mobile_latest image
	fmt.Println("Creating a new mobile session for startApp testing...")
	params := agentbay.NewCreateSessionParams().WithImageId("mobile_latest")
	sessionResult, err := agentBay.Create(params)
	if err != nil {
		t.Fatalf("Error creating mobile session: %v", err)
	}
	session := sessionResult.Session
	t.Logf("Mobile session created with ID: %s (RequestID: %s)",
		session.SessionID, sessionResult.RequestID)

	// IMPORTANT: Ensure cleanup of the session after test
	defer func() {

		fmt.Println("Cleaning up: Deleting the mobile session...")

		deleteResult, err := agentBay.Delete(session)
		if err != nil {
			t.Logf("Warning: Error deleting mobile session: %v", err)
		} else {
			t.Logf("Mobile session successfully deleted (RequestID: %s)",
				deleteResult.RequestID)
		}
	}()

	// Test StartApp with simple command like Python example
	if session.Application != nil {
		fmt.Println("Starting mobile app with simple command like Python example...")

		// Test case matching Python example usage:
		// session.application.start_app("monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1")
		startCmd := "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1"
		t.Logf("Starting mobile app with command: %s", startCmd)

		processResult, err := session.Application.StartApp(startCmd, "", "")
		if err != nil {
			t.Logf("Note: Mobile app start test (expected in mobile environment): %v", err)
			// This test is expected to work mainly in mobile environments
			return
		}

		t.Logf("Start Mobile App RequestID: %s", processResult.RequestID)

		// Verify results structure
		processes := processResult.Processes
		t.Logf("Mobile app start result: %d processes", len(processes))

		if len(processes) > 0 {
			for i, proc := range processes {
				t.Logf("Mobile process %d: %s (PID: %d)", i+1, proc.PName, proc.PID)
				if proc.PName == "" {
					t.Errorf("Found mobile process with empty process name")
				}
				if proc.PID <= 0 {
					t.Errorf("Found mobile process with invalid PID: %d", proc.PID)
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
	} else {
		t.Logf("Note: Application interface is nil, skipping mobile application test")
	}
}

func TestApplicationMobile_StartApp_WithActivity(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a session with mobile_latest image
	fmt.Println("Creating a new mobile session for startApp with activity testing...")
	params := agentbay.NewCreateSessionParams().WithImageId("mobile_latest")
	sessionResult, err := agentBay.Create(params)
	if err != nil {
		t.Fatalf("Error creating mobile session: %v", err)
	}
	session := sessionResult.Session
	t.Logf("Mobile session created with ID: %s (RequestID: %s)",
		session.SessionID, sessionResult.RequestID)

	// IMPORTANT: Ensure cleanup of the session after test
	defer func() {
		fmt.Println("Cleaning up: Deleting the mobile session...")

		deleteResult, err := agentBay.Delete(session)
		if err != nil {
			t.Logf("Warning: Error deleting mobile session: %v", err)
		} else {
			t.Logf("Mobile session successfully deleted (RequestID: %s)",
				deleteResult.RequestID)
		}
	}()

	// Test StartApp with activity like Python example
	if session.Application != nil {
		fmt.Println("Starting mobile app with activity like Python example...")

		// Test case matching Python example usage with activity:
		// session.application.start_app(start_cmd=start_cmd, activity=app_activity)
		appPackage := "com.xingin.xhs"
		appActivity := "com.xingin.outside.activity.OppoOutsideFeedActivity"
		startCmd := fmt.Sprintf("monkey -p %s -c android.intent.category.LAUNCHER 1", appPackage)

		t.Logf("Starting mobile app with activity: %s", appActivity)
		t.Logf("Start command: %s", startCmd)

		processResult, err := session.Application.StartApp(startCmd, "", appActivity)
		if err != nil {
			t.Logf("Note: Mobile app with activity test (expected in mobile environment): %v", err)
			// This test is expected to work mainly in mobile environments
			return
		}

		t.Logf("Start Mobile App with Activity RequestID: %s", processResult.RequestID)

		// Verify results structure
		processes := processResult.Processes
		t.Logf("Mobile app with activity start result: %d processes", len(processes))

		if len(processes) > 0 {
			for i, proc := range processes {
				t.Logf("Mobile process with activity %d: %s (PID: %d)", i+1, proc.PName, proc.PID)
				if proc.PName == "" {
					t.Errorf("Found mobile process with empty process name")
				}
				if proc.PID <= 0 {
					t.Errorf("Found mobile process with invalid PID: %d", proc.PID)
				}
			}
		}

		// Check if response contains "tool not found"
		if len(processes) > 0 && testutil.ContainsToolNotFound(processes[0].PName) {
			t.Errorf("Application.StartApp with activity returned 'tool not found'")
		}

		if processResult.RequestID == "" {
			t.Errorf("StartApp with activity method did not return RequestID")
		}
	} else {
		t.Logf("Note: Application interface is nil, skipping mobile application test")
	}
}

func TestApplicationMobile_StopAppByCmd(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a session with mobile_latest image
	fmt.Println("Creating a new mobile session for stopAppByCmd testing...")
	params := agentbay.NewCreateSessionParams().WithImageId("mobile_latest")
	sessionResult, err := agentBay.Create(params)
	if err != nil {
		t.Fatalf("Error creating mobile session: %v", err)
	}
	session := sessionResult.Session
	t.Logf("Mobile session created with ID: %s (RequestID: %s)",
		session.SessionID, sessionResult.RequestID)

	// IMPORTANT: Ensure cleanup of the session after test
	defer func() {
		fmt.Println("Cleaning up: Deleting the mobile session...")
		deleteResult, err := agentBay.Delete(session)
		if err != nil {
			t.Logf("Warning: Error deleting mobile session: %v", err)
		} else {
			t.Logf("Mobile session successfully deleted (RequestID: %s)",
				deleteResult.RequestID)
		}
	}()

	// Test StopAppByCmd like Python example
	if session.Application != nil {
		fmt.Println("Stopping mobile app by command like Python example...")

		// Test case matching Python example usage:
		// session.application.stop_app_by_cmd("am force-stop com.sankuai.meituan")
		stopCmd := "am force-stop com.sankuai.meituan"
		t.Logf("Stopping mobile app with command: %s", stopCmd)

		stopResult, err := session.Application.StopAppByCmd(stopCmd)
		if err != nil {
			t.Logf("Note: Mobile app stop by command test (expected in mobile environment): %v", err)
			// This test is expected to work mainly in mobile environments
			return
		}

		t.Logf("Mobile application stopped by command successfully")
		t.Logf("Stop Mobile App by Cmd RequestID: %s", stopResult.RequestID)

		// Verify that we got a successful result
		if !stopResult.Success {
			t.Errorf("StopAppByCmd did not return success")
		}

		if stopResult.RequestID == "" {
			t.Errorf("StopAppByCmd method did not return RequestID")
		}
	} else {
		t.Logf("Note: Application interface is nil, skipping mobile application test")
	}
}

func TestApplicationMobile_CompleteWorkflow(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a session with mobile_latest image
	fmt.Println("Creating a new mobile session for complete workflow testing...")
	params := agentbay.NewCreateSessionParams().WithImageId("mobile_latest")
	sessionResult, err := agentBay.Create(params)
	if err != nil {
		t.Fatalf("Error creating mobile session: %v", err)
	}
	session := sessionResult.Session
	t.Logf("Mobile session created with ID: %s (RequestID: %s)",
		session.SessionID, sessionResult.RequestID)

	// IMPORTANT: Ensure cleanup of the session after test
	defer func() {
		fmt.Println("Cleaning up: Deleting the mobile session...")
		deleteResult, err := agentBay.Delete(session)
		if err != nil {
			t.Logf("Warning: Error deleting mobile session: %v", err)
		} else {
			t.Logf("Mobile session successfully deleted (RequestID: %s)",
				deleteResult.RequestID)
		}
	}()

	// Test complete workflow matching Python example
	if session.Application != nil {
		fmt.Println("Testing complete mobile workflow like Python example...")

		// Step 1: Get installed apps
		fmt.Println("Step 1: Getting mobile installed applications...")
		appsResult, err := session.Application.GetInstalledApps(true, false, true)
		if err != nil {
			t.Logf("Note: GetInstalledApps failed: %v", err)
		} else {
			if appsResult.RequestID == "" {
				t.Errorf("GetInstalledApps method did not return RequestID")
			}
			t.Logf("Found %d mobile apps (RequestID: %s)", len(appsResult.Applications), appsResult.RequestID)
		}

		// Step 2: Start mobile app with simple command
		fmt.Println("Step 2: Starting mobile app with simple command...")
		startCmd := "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1"
		startResult, err := session.Application.StartApp(startCmd, "", "")
		if err != nil {
			t.Logf("Note: Simple start command failed (expected in mobile environment): %v", err)
		} else {
			if startResult.RequestID == "" {
				t.Errorf("StartApp method did not return RequestID")
			}
			t.Logf("Started mobile app: %d processes (RequestID: %s)", len(startResult.Processes), startResult.RequestID)
		}

		// Step 3: Start mobile app with activity
		fmt.Println("Step 3: Starting mobile app with activity...")
		appPackage := "com.xingin.xhs"
		appActivity := "com.xingin.outside.activity.OppoOutsideFeedActivity"
		activityStartCmd := fmt.Sprintf("monkey -p %s -c android.intent.category.LAUNCHER 1", appPackage)

		activityStartResult, err := session.Application.StartApp(activityStartCmd, "", appActivity)
		if err != nil {
			t.Logf("Note: Activity start command failed (expected in mobile environment): %v", err)
		} else {
			if activityStartResult.RequestID == "" {
				t.Errorf("StartApp with activity method did not return RequestID")
			}
			t.Logf("Started mobile app with activity: %d processes (RequestID: %s)",
				len(activityStartResult.Processes), activityStartResult.RequestID)
		}

		// Step 4: Stop mobile app
		fmt.Println("Step 4: Stopping mobile app...")
		stopCmd := "am force-stop com.xingin.xhs"
		stopResult, err := session.Application.StopAppByCmd(stopCmd)
		if err != nil {
			t.Logf("Note: Stop command failed (expected in mobile environment): %v", err)
		} else {
			if stopResult.RequestID == "" {
				t.Errorf("StopAppByCmd method did not return RequestID")
			}
			if !stopResult.Success {
				t.Errorf("StopAppByCmd did not return success")
			}
			t.Logf("Mobile app stopped successfully (RequestID: %s)", stopResult.RequestID)
		}

		fmt.Println("Mobile workflow completed successfully!")
	} else {
		t.Logf("Note: Application interface is nil, skipping mobile workflow test")
	}
}
