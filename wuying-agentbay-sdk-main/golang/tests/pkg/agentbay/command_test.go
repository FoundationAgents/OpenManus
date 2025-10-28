package agentbay_test

import (
	"fmt"
	"strings"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

func TestCommand_ExecuteCommand(t *testing.T) {
	// Create session parameters with ImageId set to code_latest
	params := agentbay.NewCreateSessionParams().WithImageId("code_latest")

	// Setup session with cleanup
	session, cleanup := testutil.SetupAndCleanup(t, params)
	defer cleanup()

	// Test Command execution
	if session.Command != nil {
		// Test with echo command (works on all platforms)
		fmt.Println("Executing echo command...")
		testString := "AgentBay SDK Test"
		echoCmd := fmt.Sprintf("echo '%s'", testString)

		// Test with default timeout
		cmdResult, err := session.Command.ExecuteCommand(echoCmd)
		if err != nil {
			t.Logf("Note: Echo command failed: %v", err)
		} else {
			result := cmdResult.Output
			t.Logf("Echo command result with RequestID %s: %s", cmdResult.RequestID, result)

			// Check if response contains "tool not found"
			if testutil.ContainsToolNotFound(result) {
				t.Errorf("Command.ExecuteCommand returned 'tool not found'")
			}

			// Verify the response contains the test string
			if !strings.Contains(result, testString) {
				t.Errorf("Echo command verification failed: expected '%s' in response, got '%s'", testString, result)
			} else {
				t.Logf("Echo command verified successfully")
			}

			if cmdResult.RequestID == "" {
				t.Errorf("Command.ExecuteCommand did not return RequestID")
			}
		}

		// Test with custom timeout
		fmt.Println("Executing echo command with custom timeout...")
		customTimeout := 2000 // 2 seconds
		cmdResultWithTimeout, err := session.Command.ExecuteCommand(echoCmd, customTimeout)
		if err != nil {
			t.Logf("Note: Echo command with custom timeout failed: %v", err)
		} else {
			resultWithTimeout := cmdResultWithTimeout.Output
			t.Logf("Echo command with custom timeout result with RequestID %s: %s", cmdResultWithTimeout.RequestID, resultWithTimeout)

			// Check if response contains "tool not found"
			if testutil.ContainsToolNotFound(resultWithTimeout) {
				t.Errorf("Command.ExecuteCommand with custom timeout returned 'tool not found'")
			}

			// Verify the response contains the test string
			if !strings.Contains(resultWithTimeout, testString) {
				t.Errorf("Echo command with custom timeout verification failed: expected '%s' in response, got '%s'", testString, resultWithTimeout)
			} else {
				t.Logf("Echo command with custom timeout verified successfully")
			}

			if cmdResultWithTimeout.RequestID == "" {
				t.Errorf("Command.ExecuteCommand with custom timeout did not return RequestID")
			}
		}
	} else {
		t.Logf("Note: Command interface is nil, skipping command test")
	}
}
