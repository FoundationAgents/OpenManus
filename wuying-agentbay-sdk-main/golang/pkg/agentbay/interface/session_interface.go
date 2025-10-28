package interfaces

import (
	"github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

//go:generate mockgen -destination=../../../tests/pkg/unit/mock/mock_session.go -package=mock github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/interface SessionInterface

// SessionInterface defines the interface for session operations
type SessionInterface interface {
	// GetAPIKey returns the API key
	GetAPIKey() string

	// GetClient returns the client instance
	GetClient() *client.Client

	// GetSessionId returns the session ID
	GetSessionId() string

	// Delete deletes this session
	Delete(syncContext ...bool) (*agentbay.DeleteResult, error)

	// SetLabels sets the labels for this session
	SetLabels(labels map[string]string) (*agentbay.LabelResult, error)

	// GetLabels gets the labels for this session
	GetLabels() (*agentbay.LabelResult, error)

	// GetLink gets the link for this session
	GetLink(protocolType *string, port *int32) (*agentbay.LinkResult, error)

	// Info gets information about this session
	Info() (*agentbay.InfoResult, error)

	// ListMcpTools lists MCP tools available for this session
	ListMcpTools() (*agentbay.McpToolsResult, error)

	// IsVpc returns whether this session uses VPC resources
	IsVpc() bool

	// NetworkInterfaceIp returns the network interface IP for VPC sessions
	NetworkInterfaceIp() string

	// HttpPort returns the HTTP port for VPC sessions
	HttpPort() string

	// FindServerForTool searches for the server that provides the given tool
	FindServerForTool(toolName string) string
}
