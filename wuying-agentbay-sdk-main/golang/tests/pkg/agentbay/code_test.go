package agentbay_test

import (
	"fmt"
	"strings"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

func TestCode_RunCode(t *testing.T) {
	// Create session parameters with ImageId set to code_latest
	params := agentbay.NewCreateSessionParams().WithImageId("code_latest")

	// Setup session with cleanup
	session, cleanup := testutil.SetupAndCleanup(t, params)
	defer cleanup()

	// Test RunCode execution
	if session.Code != nil {
		// Test with Python code
		fmt.Println("Executing Python code...")
		pythonCode := `
print("Hello, world!")
x = 1 + 1
print(x)
`
		// Test with default timeout
		cmdResult, err := session.Code.RunCode(pythonCode, "python")
		if err != nil {
			t.Logf("Note: Python code execution failed: %v", err)
		} else {
			result := cmdResult.Output
			t.Logf("Python code execution result with RequestID %s: %s", cmdResult.RequestID, result)

			// Check if response contains "tool not found"
			if testutil.ContainsToolNotFound(result) {
				t.Errorf("Code.RunCode returned 'tool not found'")
			}

			// Verify the response contains expected output
			if !strings.Contains(result, "Hello, world!") || !strings.Contains(result, "2") {
				t.Errorf("Python code verification failed: expected 'Hello, world!' and '2' in response, got '%s'", result)
			} else {
				t.Logf("Python code execution verified successfully")
			}

			if cmdResult.RequestID == "" {
				t.Errorf("Code.RunCode did not return RequestID")
			} else {
				t.Logf("RequestID received: %s", cmdResult.RequestID)
			}
		}

		// Test with JavaScript and custom timeout
		fmt.Println("Executing JavaScript code...")
		jsCode := `
console.log("Hello, world!");
const x = 1 + 1;
console.log(x);
`
		customTimeout := 60

		cmdResultJs, err := session.Code.RunCode(jsCode, "javascript", customTimeout)
		if err != nil {
			t.Logf("Note: JavaScript code execution failed: %v", err)
		} else {
			result := cmdResultJs.Output
			t.Logf("JavaScript code execution result with RequestID %s: %s", cmdResultJs.RequestID, result)

			// Check if response contains "tool not found"
			if testutil.ContainsToolNotFound(result) {
				t.Errorf("Code.RunCode with custom timeout returned 'tool not found'")
			}

			// Verify the response contains expected output
			if !strings.Contains(result, "Hello, world!") || !strings.Contains(result, "2") {
				t.Errorf("JavaScript code verification failed: expected 'Hello, world!' and '2' in response, got '%s'", result)
			} else {
				t.Logf("JavaScript code execution verified successfully")
			}

			if cmdResultJs.RequestID == "" {
				t.Errorf("Code.RunCode with custom timeout did not return RequestID")
			} else {
				t.Logf("RequestID received: %s", cmdResultJs.RequestID)
			}
		}

		// Test unsupported language
		_, err = session.Code.RunCode("print('test')", "invalid_language")
		if err == nil {
			t.Error("Code.RunCode should return error for unsupported language")
		} else {
			t.Logf("Expected error for unsupported language: %v", err)
		}
	} else {
		t.Logf("Note: Code interface is nil, skipping run_code test")
	}
}
