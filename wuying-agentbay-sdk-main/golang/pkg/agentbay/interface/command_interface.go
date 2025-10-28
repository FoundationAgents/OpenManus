package interfaces

import (
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/command"
)

//go:generate mockgen -destination=../../../tests/pkg/unit/mock/mock_command.go -package=mock github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/interface CommandInterface

// CommandInterface defines the interface for command operations
type CommandInterface interface {
	// ExecuteCommand executes a command with optional timeout
	ExecuteCommand(command string, timeoutMs ...int) (*command.CommandResult, error)
}
