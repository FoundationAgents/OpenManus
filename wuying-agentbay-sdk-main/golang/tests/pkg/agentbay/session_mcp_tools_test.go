package agentbay_test

import (
	"fmt"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

func TestSession_ListMcpTools(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Test with different ImageId values
	testCases := []struct {
		name    string
		imageId string
	}{
		{"Default ImageId", ""}, // Should use "linux_latest" as default
		{"Linux Latest", "linux_latest"},
		{"Code Latest", "code_latest"},
		{"Browser Latest", "browser_latest"},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			// Create session parameters
			params := &agentbay.CreateSessionParams{}
			if tc.imageId != "" {
				params.ImageId = tc.imageId
			}

			// Create a new session
			fmt.Printf("Creating session with ImageId: %s\n", tc.imageId)
			sessionResult, err := agentBay.Create(params)
			if err != nil {
				t.Fatalf("Error creating session: %v", err)
			}

			session := sessionResult.Session
			t.Logf("Session created with ID: %s", session.SessionID)

			// Verify that ImageId is properly set in session
			expectedImageId := tc.imageId
			if expectedImageId == "" {
				expectedImageId = "linux_latest"
			}
			if session.ImageId != expectedImageId {
				t.Errorf("Expected session.ImageId to be '%s', but got '%s'", expectedImageId, session.ImageId)
			}

			defer func() {
				// Clean up the session after test
				fmt.Println("Cleaning up: Deleting the session...")
				deleteResult, err := agentBay.Delete(session)
				if err != nil {
					t.Logf("Warning: Error deleting session: %v", err)
				} else {
					t.Logf("Session deleted (RequestID: %s)", deleteResult.RequestID)
				}
			}()

			// Call ListMcpTools API
			fmt.Printf("Calling ListMcpTools with ImageId: %s\n", session.ImageId)
			mcpToolsResult, err := session.ListMcpTools()
			if err != nil {
				t.Fatalf("Error calling ListMcpTools: %v", err)
			}

			// Verify the response
			t.Logf("ListMcpTools response - RequestID: %s", mcpToolsResult.RequestID)
			t.Logf("Number of tools returned: %d", len(mcpToolsResult.Tools))

			if len(mcpToolsResult.Tools) == 0 {
				t.Log("Warning: No MCP tools returned")
			}

			// Verify each tool has required fields
			for i, tool := range mcpToolsResult.Tools {
				t.Logf("Tool %d: Name='%s', Description='%s', Server='%s', Tool='%s'", i+1, tool.Name, tool.Description, tool.Server, tool.Tool)

				if tool.Name == "" {
					t.Errorf("Tool %d has empty Name", i+1)
				}
				if tool.Server == "" {
					t.Errorf("Tool %d has empty Server", i+1)
				}
				if tool.Tool == "" {
					t.Errorf("Tool %d has empty Tool identifier", i+1)
				}
				// Description and InputSchema can be empty, so we don't check them
			}

			// Verify that the session's McpTools field is updated
			if len(session.McpTools) != len(mcpToolsResult.Tools) {
				t.Errorf("Expected session.McpTools to have %d tools, but got %d", len(mcpToolsResult.Tools), len(session.McpTools))
			}

			// Verify that the tools are properly stored in session
			for i, tool := range session.McpTools {
				if tool.Name != mcpToolsResult.Tools[i].Name {
					t.Errorf("Expected session.McpTools[%d].Name to be '%s', but got '%s'", i, mcpToolsResult.Tools[i].Name, tool.Name)
				}
			}
		})
	}
}

func TestSession_ListMcpTools_EmptyImageId(t *testing.T) {
	// Initialize AgentBay client
	apiKey := testutil.GetTestAPIKey(t)
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		t.Fatalf("Error initializing AgentBay client: %v", err)
	}

	// Create a session without specifying ImageId
	fmt.Println("Creating a new session without ImageId...")
	sessionResult, err := agentBay.Create(nil)
	if err != nil {
		t.Fatalf("Error creating session: %v", err)
	}

	session := sessionResult.Session
	t.Logf("Session created with ID: %s", session.SessionID)

	defer func() {
		// Clean up the session after test
		fmt.Println("Cleaning up: Deleting the session...")
		deleteResult, err := agentBay.Delete(session)
		if err != nil {
			t.Logf("Warning: Error deleting session: %v", err)
		} else {
			t.Logf("Session deleted (RequestID: %s)", deleteResult.RequestID)
		}
	}()

	// Test ListMcpTools method with default ImageId
	fmt.Println("Testing ListMcpTools method with default ImageId...")
	mcpToolsResult, err := session.ListMcpTools()
	if err != nil {
		t.Errorf("Error calling ListMcpTools: %v", err)
		return
	}

	// Verify the response
	if mcpToolsResult.RequestID == "" {
		t.Errorf("ListMcpTools method did not return RequestID")
	}

	if mcpToolsResult.Tools == nil {
		t.Errorf("Expected Tools to be non-nil")
		return
	}

	t.Logf("Found %d MCP tools with default ImageId", len(mcpToolsResult.Tools))
}
