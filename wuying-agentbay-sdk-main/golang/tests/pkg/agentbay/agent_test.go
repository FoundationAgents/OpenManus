package agentbay_test

import (
	"os"
	"strconv"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

func TestAgent_ExecuteTask(t *testing.T) {
	// Create session parameters with Windows image for agent tasks
	params := agentbay.NewCreateSessionParams().WithImageId("waic-playground-demo-windows")

	// Setup session with cleanup
	session, cleanup := testutil.SetupAndCleanup(t, params)
	defer cleanup()

	// Test Agent task execution
	if session.Agent != nil {
		task := "create a folder named 'agentbay' in C:\\Windows\\Temp"

		// Get timeout from environment or use default
		maxTryTimesStr := os.Getenv("AGENT_TASK_TIMEOUT")
		maxTryTimes := 300 // default value
		if maxTryTimesStr != "" {
			if parsed, err := strconv.Atoi(maxTryTimesStr); err == nil {
				maxTryTimes = parsed
			}
		} else {
			t.Log("We will wait for 300 * 3 seconds to finish.")
		}

		t.Logf("Executing agent task: %s", task)
		result := session.Agent.ExecuteTask(task, maxTryTimes)

		t.Logf("Agent task result with RequestID %s: Success=%v, TaskID=%s, Status=%s",
			result.RequestID, result.Success, result.TaskID, result.TaskStatus)

		if !result.Success {
			t.Errorf("Agent task execution failed: %s", result.ErrorMessage)
		} else {
			t.Logf("Agent task executed successfully")

			if result.RequestID == "" {
				t.Errorf("Agent.ExecuteTask did not return RequestID")
			}

			if result.TaskID == "" {
				t.Errorf("Agent.ExecuteTask did not return TaskID")
			}
		}
	} else {
		t.Log("Note: Agent interface is nil, skipping agent test")
	}
}
