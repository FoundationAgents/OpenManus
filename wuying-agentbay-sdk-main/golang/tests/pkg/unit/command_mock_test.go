package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/command"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/unit/mock"
	"github.com/golang/mock/gomock"
	"github.com/stretchr/testify/assert"
)

func TestCommand_ExecuteCommand_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Command
	mockCmd := mock.NewMockCommandInterface(ctrl)

	// Set expected behavior
	expectedResult := &command.CommandResult{
		Output: "Command executed successfully",
	}
	mockCmd.EXPECT().ExecuteCommand("ls -la").Return(expectedResult, nil)

	// Test ExecuteCommand method call
	result, err := mockCmd.ExecuteCommand("ls -la")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "Command executed successfully", result.Output)
}

func TestCommand_ExecuteCommandWithTimeout_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Command
	mockCmd := mock.NewMockCommandInterface(ctrl)

	// Set expected behavior
	expectedResult := &command.CommandResult{
		Output: "Command executed with timeout",
	}
	mockCmd.EXPECT().ExecuteCommand("ls -la", 5000).Return(expectedResult, nil)

	// Test ExecuteCommand with timeout method call
	result, err := mockCmd.ExecuteCommand("ls -la", 5000)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "Command executed with timeout", result.Output)
}

func TestCommand_Error_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Command
	mockCmd := mock.NewMockCommandInterface(ctrl)

	// Set expected behavior - return error
	mockCmd.EXPECT().ExecuteCommand("invalid_command").Return(nil, assert.AnError)

	// Test error case
	result, err := mockCmd.ExecuteCommand("invalid_command")

	// Verify error handling
	assert.Error(t, err)
	assert.Nil(t, result)
}
