package command

import (
	"fmt"

	mcp "github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

// CommandResult represents the result of a command execution
type CommandResult struct {
	// Embed the basic API response structure
	models.ApiResponse
	// Output contains the command execution output
	Output string
}

// Command handles command execution operations in the AgentBay cloud environment.
type Command struct {
	Session interface {
		GetAPIKey() string
		GetClient() *mcp.Client
		GetSessionId() string
		IsVpc() bool
		NetworkInterfaceIp() string
		HttpPort() string
		FindServerForTool(toolName string) string
		CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error)
	}
}

// NewCommand creates a new Command instance
func NewCommand(session interface {
	GetAPIKey() string
	GetClient() *mcp.Client
	GetSessionId() string
	IsVpc() bool
	NetworkInterfaceIp() string
	HttpPort() string
	FindServerForTool(toolName string) string
	CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error)
}) *Command {
	return &Command{
		Session: session,
	}
}

// ExecuteCommand executes a command in the session environment.
func (c *Command) ExecuteCommand(command string, timeoutMs ...int) (*CommandResult, error) {
	// Set default timeout if not provided
	timeout := 1000
	if len(timeoutMs) > 0 && timeoutMs[0] > 0 {
		timeout = timeoutMs[0]
	}

	args := map[string]interface{}{
		"command":    command,
		"timeout_ms": timeout,
	}

	// Use Session's CallMcpTool method
	result, err := c.Session.CallMcpTool("shell", args)
	if err != nil {
		return nil, fmt.Errorf("failed to execute command: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("command execution failed: %s", result.ErrorMessage)
	}

	return &CommandResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Output: result.Data,
	}, nil
}
