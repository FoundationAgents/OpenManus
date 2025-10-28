package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/code"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/unit/mock"
	"github.com/golang/mock/gomock"
	"github.com/stretchr/testify/assert"
)

func TestCode_RunCode_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Code
	mockCode := mock.NewMockCodeInterface(ctrl)

	// Set expected behavior
	expectedResult := &code.CodeResult{
		Output: "Code executed successfully",
	}
	mockCode.EXPECT().RunCode("print('hello')", "python").Return(expectedResult, nil)

	// Test RunCode method call
	result, err := mockCode.RunCode("print('hello')", "python")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "Code executed successfully", result.Output)
}

func TestCode_RunCode_WithTimeout_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Code
	mockCode := mock.NewMockCodeInterface(ctrl)

	// Set expected behavior with timeout
	expectedResult := &code.CodeResult{
		Output: "JavaScript code executed successfully",
	}
	mockCode.EXPECT().RunCode("console.log('test')", "javascript", 60).Return(expectedResult, nil)

	// Test RunCode method call with timeout
	result, err := mockCode.RunCode("console.log('test')", "javascript", 60)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "JavaScript code executed successfully", result.Output)
}
