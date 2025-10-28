package integration

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/stretchr/testify/assert"
)

func TestSession_ComputerMobileIntegration(t *testing.T) {
	// Create a mock AgentBay instance
	mockAgentBay := &agentbay.AgentBay{
		APIKey: "test-api-key",
	}

	// Create a new session
	session := agentbay.NewSession(mockAgentBay, "test-session-123")

	// Test that Computer and Mobile modules are properly initialized
	t.Run("Computer module initialization", func(t *testing.T) {
		assert.NotNil(t, session.Computer, "Computer module should be initialized")
		assert.Equal(t, session, session.Computer.Session, "Computer should reference the session")
	})

	t.Run("Mobile module initialization", func(t *testing.T) {
		assert.NotNil(t, session.Mobile, "Mobile module should be initialized")
		assert.Equal(t, session, session.Mobile.Session, "Mobile should reference the session")
	})

	// Test that session methods are accessible through Computer and Mobile
	t.Run("Session interface compatibility", func(t *testing.T) {
		// Test that Computer can access session methods
		assert.Equal(t, "test-api-key", session.Computer.Session.GetAPIKey())
		assert.Equal(t, "test-session-123", session.Computer.Session.GetSessionId())

		// Test that Mobile can access session methods
		assert.Equal(t, "test-api-key", session.Mobile.Session.GetAPIKey())
		assert.Equal(t, "test-session-123", session.Mobile.Session.GetSessionId())
	})

	// Test that existing modules are still available
	t.Run("Existing modules compatibility", func(t *testing.T) {
		assert.NotNil(t, session.UI, "UI module should still be available")
		assert.NotNil(t, session.Application, "Application module should still be available")
		assert.NotNil(t, session.Window, "Window module should still be available")
		assert.NotNil(t, session.FileSystem, "FileSystem module should still be available")
		assert.NotNil(t, session.Command, "Command module should still be available")
		assert.NotNil(t, session.Code, "Code module should still be available")
		assert.NotNil(t, session.Agent, "Agent module should still be available")
	})
}

func TestSession_ComputerModuleUsage(t *testing.T) {
	// This test demonstrates how the Computer module would be used
	// Note: This is a structural test, not a functional test since we don't have a real session

	mockAgentBay := &agentbay.AgentBay{
		APIKey: "test-api-key",
	}

	session := agentbay.NewSession(mockAgentBay, "test-session-456")

	t.Run("Computer module API availability", func(t *testing.T) {
		// Verify that Computer module methods are available
		// These would normally make MCP tool calls, but we're just testing structure

		assert.NotNil(t, session.Computer.ClickMouse, "ClickMouse method should be available")
		assert.NotNil(t, session.Computer.MoveMouse, "MoveMouse method should be available")
		assert.NotNil(t, session.Computer.DragMouse, "DragMouse method should be available")
		assert.NotNil(t, session.Computer.Scroll, "Scroll method should be available")
		assert.NotNil(t, session.Computer.InputText, "InputText method should be available")
		assert.NotNil(t, session.Computer.PressKeys, "PressKeys method should be available")
		assert.NotNil(t, session.Computer.ReleaseKeys, "ReleaseKeys method should be available")
		assert.NotNil(t, session.Computer.GetCursorPosition, "GetCursorPosition method should be available")
		assert.NotNil(t, session.Computer.GetScreenSize, "GetScreenSize method should be available")
		assert.NotNil(t, session.Computer.Screenshot, "Screenshot method should be available")
	})
}

func TestSession_MobileModuleUsage(t *testing.T) {
	// This test demonstrates how the Mobile module would be used

	mockAgentBay := &agentbay.AgentBay{
		APIKey: "test-api-key",
	}

	session := agentbay.NewSession(mockAgentBay, "test-session-789")

	t.Run("Mobile module API availability", func(t *testing.T) {
		// Verify that Mobile module methods are available

		assert.NotNil(t, session.Mobile.Tap, "Tap method should be available")
		assert.NotNil(t, session.Mobile.Swipe, "Swipe method should be available")
		assert.NotNil(t, session.Mobile.InputText, "InputText method should be available")
		assert.NotNil(t, session.Mobile.SendKey, "SendKey method should be available")
		assert.NotNil(t, session.Mobile.GetClickableUIElements, "GetClickableUIElements method should be available")
		assert.NotNil(t, session.Mobile.GetAllUIElements, "GetAllUIElements method should be available")
		assert.NotNil(t, session.Mobile.GetInstalledApps, "GetInstalledApps method should be available")
		assert.NotNil(t, session.Mobile.StartApp, "StartApp method should be available")
		assert.NotNil(t, session.Mobile.StopAppByPName, "StopAppByPName method should be available")
		assert.NotNil(t, session.Mobile.Screenshot, "Screenshot method should be available")
	})
}
