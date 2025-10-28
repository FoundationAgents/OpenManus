package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/application"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/command"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/filesystem"
	interfaces "github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/interface"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/oss"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/ui"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/window"
)

// TestInterfaceCompliance ensures that actual implementation classes implement their respective interfaces
func TestInterfaceCompliance(t *testing.T) {

	// Test that AgentBay implements AgentBayInterface
	t.Run("AgentBay implements AgentBayInterface", func(t *testing.T) {
		var _ interfaces.AgentBayInterface = (*agentbay.AgentBay)(nil)
	})

	// Test that Session implements SessionInterface
	t.Run("Session implements SessionInterface", func(t *testing.T) {
		var _ interfaces.SessionInterface = (*agentbay.Session)(nil)
	})

	// Test that FileSystem implements FileSystemInterface
	t.Run("FileSystem implements FileSystemInterface", func(t *testing.T) {
		var _ interfaces.FileSystemInterface = (*filesystem.FileSystem)(nil)
	})

	// Test that Command implements CommandInterface
	t.Run("Command implements CommandInterface", func(t *testing.T) {
		var _ interfaces.CommandInterface = (*command.Command)(nil)
	})

	// Test that ApplicationManager implements ApplicationInterface
	t.Run("ApplicationManager implements ApplicationInterface", func(t *testing.T) {
		var _ interfaces.ApplicationInterface = (*application.ApplicationManager)(nil)
	})

	// Test that OSSManager implements OSSInterface
	t.Run("OSSManager implements OSSInterface", func(t *testing.T) {
		var _ interfaces.OSSInterface = (*oss.OSSManager)(nil)
	})

	// Test that UIManager implements UIInterface
	t.Run("UIManager implements UIInterface", func(t *testing.T) {
		var _ interfaces.UIInterface = (*ui.UIManager)(nil)
	})

	// Test that WindowManager implements WindowInterface
	t.Run("WindowManager implements WindowInterface", func(t *testing.T) {
		var _ interfaces.WindowInterface = (*window.WindowManager)(nil)
	})

	// Test that ContextService implements ContextInterface
	t.Run("ContextService implements ContextInterface", func(t *testing.T) {
		var _ interfaces.ContextInterface = (*agentbay.ContextService)(nil)
	})
}

// TestConcreteInterfaceUsage tests that concrete implementations can be used through their interfaces
func TestConcreteInterfaceUsage(t *testing.T) {
	// This test verifies that concrete implementations can be used through their interfaces
	// It doesn't test actual functionality (which would require a real client)
	// but ensures that the interface contract is correctly implemented

	// Note: We skip the actual method calls to avoid nil pointer dereference
	// The interface compliance is already tested in TestInterfaceCompliance

	t.Run("FileSystem can be used through interface", func(t *testing.T) {
		// Create a mock session with nil client to test interface usage
		mockSession := &MockSessionForCompliance{
			apiKey:    "test-api-key",
			sessionID: "test-session-id",
			client:    nil, // This will cause nil pointer dereference if called
		}

		// Create concrete FileSystem
		fs := filesystem.NewFileSystem(mockSession)

		// Use it through interface - this verifies the interface is implemented
		var fsInterface interfaces.FileSystemInterface = fs

		// We don't call methods because that would cause nil pointer dereference
		// The fact that we can assign it to the interface type proves compliance
		_ = fsInterface
	})

	t.Run("Command can be used through interface", func(t *testing.T) {
		mockSession := &MockSessionForCompliance{
			apiKey:    "test-api-key",
			sessionID: "test-session-id",
			client:    nil,
		}

		cmd := command.NewCommand(mockSession)
		var cmdInterface interfaces.CommandInterface = cmd
		_ = cmdInterface
	})

	t.Run("ApplicationManager can be used through interface", func(t *testing.T) {
		mockSession := &MockSessionForCompliance{
			apiKey:    "test-api-key",
			sessionID: "test-session-id",
			client:    nil,
		}

		app := application.NewApplicationManager(mockSession)
		var appInterface interfaces.ApplicationInterface = app
		_ = appInterface
	})

	t.Run("OSSManager can be used through interface", func(t *testing.T) {
		mockSession := &MockSessionForCompliance{
			apiKey:    "test-api-key",
			sessionID: "test-session-id",
			client:    nil,
		}

		ossManager := oss.NewOss(mockSession)
		var ossInterface interfaces.OSSInterface = ossManager
		_ = ossInterface
	})

	t.Run("UIManager can be used through interface", func(t *testing.T) {
		mockSession := &MockSessionForCompliance{
			apiKey:    "test-api-key",
			sessionID: "test-session-id",
			client:    nil,
		}

		uiManager := ui.NewUI(mockSession)
		var uiInterface interfaces.UIInterface = uiManager
		_ = uiInterface
	})

	t.Run("WindowManager can be used through interface", func(t *testing.T) {
		mockSession := &MockSessionForCompliance{
			apiKey:    "test-api-key",
			sessionID: "test-session-id",
			client:    nil,
		}

		winManager := window.NewWindowManager(mockSession)
		var winInterface interfaces.WindowInterface = winManager
		_ = winInterface
	})
}

// MockSessionForCompliance for testing interface compliance (avoid name conflict)
type MockSessionForCompliance struct {
	apiKey    string
	sessionID string
	client    *client.Client
}

func (m *MockSessionForCompliance) GetAPIKey() string                        { return m.apiKey }
func (m *MockSessionForCompliance) GetSessionId() string                     { return m.sessionID }
func (m *MockSessionForCompliance) GetClient() *client.Client                { return m.client }
func (m *MockSessionForCompliance) IsVpc() bool                              { return false }
func (m *MockSessionForCompliance) NetworkInterfaceIp() string               { return "" }
func (m *MockSessionForCompliance) HttpPort() string                         { return "" }
func (m *MockSessionForCompliance) FindServerForTool(toolName string) string { return "" }
func (m *MockSessionForCompliance) Delete(syncContext ...bool) (*agentbay.DeleteResult, error) {
	return nil, nil
}
func (m *MockSessionForCompliance) SetLabels(labels map[string]string) *agentbay.LabelResult {
	return &agentbay.LabelResult{
		ApiResponse: models.ApiResponse{RequestID: ""},
	}
}
func (m *MockSessionForCompliance) GetLabels() (*agentbay.LabelResult, error) { return nil, nil }
func (m *MockSessionForCompliance) GetLink(protocolType *string, port *int32) (*agentbay.LinkResult, error) {
	return nil, nil
}
func (m *MockSessionForCompliance) Info() (*agentbay.InfoResult, error) { return nil, nil }
func (m *MockSessionForCompliance) CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error) {
	return &models.McpToolResult{
		Success:      true,
		Data:         "",
		ErrorMessage: "",
		RequestID:    "",
	}, nil
}
