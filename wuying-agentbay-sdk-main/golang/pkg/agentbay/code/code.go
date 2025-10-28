package code

import (
	"fmt"

	mcp "github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

// CodeResult represents the result of a code execution
type CodeResult struct {
	models.ApiResponse // Embedded ApiResponse
	Output             string
}

// Code handles code execution operations in the AgentBay cloud environment.
type Code struct {
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

// NewCode creates a new Code instance
func NewCode(session interface {
	GetAPIKey() string
	GetClient() *mcp.Client
	GetSessionId() string
	IsVpc() bool
	NetworkInterfaceIp() string
	HttpPort() string
	FindServerForTool(toolName string) string
	CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error)
}) *Code {
	return &Code{
		Session: session,
	}
}

// RunCode executes code in the session environment.
// timeoutS: The timeout for the code execution in seconds. Default is 60s.
// Note: Due to gateway limitations, each request cannot exceed 60 seconds.
func (c *Code) RunCode(code string, language string, timeoutS ...int) (*CodeResult, error) {
	// Set default timeout if not provided
	timeout := 60
	if len(timeoutS) > 0 && timeoutS[0] > 0 {
		timeout = timeoutS[0]
	}

	// Validate language
	if language != "python" && language != "javascript" {
		return nil, fmt.Errorf("unsupported language: %s. Supported languages are 'python' and 'javascript'", language)
	}

	args := map[string]interface{}{
		"code":      code,
		"language":  language,
		"timeout_s": timeout,
	}

	// Use Session's CallMcpTool method
	result, err := c.Session.CallMcpTool("run_code", args)
	if err != nil {
		return nil, fmt.Errorf("failed to execute code: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("code execution failed: %s", result.ErrorMessage)
	}

	return &CodeResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Output: result.Data,
	}, nil
}
