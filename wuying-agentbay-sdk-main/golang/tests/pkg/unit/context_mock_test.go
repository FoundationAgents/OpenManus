package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/unit/mock"
	"github.com/golang/mock/gomock"
	"github.com/stretchr/testify/assert"
)

func TestContext_List_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Context
	mockContext := mock.NewMockContextInterface(ctrl)

	// Set expected behavior
	params := &agentbay.ContextListParams{
		MaxResults: 10,
		NextToken:  "",
	}
	expectedResult := &agentbay.ContextListResult{
		Contexts: []*agentbay.Context{
			{ID: "ctx1", Name: "context1"},
			{ID: "ctx2", Name: "context2"},
		},
	}
	mockContext.EXPECT().List(params).Return(expectedResult, nil)

	// Test List method call
	result, err := mockContext.List(params)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Len(t, result.Contexts, 2)
	assert.Equal(t, "ctx1", result.Contexts[0].ID)
	assert.Equal(t, "ctx2", result.Contexts[1].ID)
}

func TestContext_Get_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Context
	mockContext := mock.NewMockContextInterface(ctrl)

	// Set expected behavior
	expectedResult := &agentbay.ContextResult{
		ContextID: "ctx1",
		Context:   &agentbay.Context{ID: "ctx1", Name: "context1"},
	}
	mockContext.EXPECT().Get("context1", true).Return(expectedResult, nil)

	// Test Get method call
	result, err := mockContext.Get("context1", true)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "ctx1", result.ContextID)
	assert.Equal(t, "ctx1", result.Context.ID)
}

func TestContext_Create_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Context
	mockContext := mock.NewMockContextInterface(ctrl)

	// Set expected behavior
	expectedResult := &agentbay.ContextCreateResult{
		ContextID: "new_ctx",
	}
	mockContext.EXPECT().Create("new_context").Return(expectedResult, nil)

	// Test Create method call
	result, err := mockContext.Create("new_context")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "new_ctx", result.ContextID)
}

func TestContext_Update_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Context
	mockContext := mock.NewMockContextInterface(ctrl)

	// Set expected behavior
	ctx := &agentbay.Context{ID: "ctx1", Name: "updated_context"}
	expectedResult := &agentbay.ContextModifyResult{
		Success: true,
	}
	mockContext.EXPECT().Update(ctx).Return(expectedResult, nil)

	// Test Update method call
	result, err := mockContext.Update(ctx)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.True(t, result.Success)
}

func TestContext_Delete_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Context
	mockContext := mock.NewMockContextInterface(ctrl)

	// Set expected behavior
	ctx := &agentbay.Context{ID: "ctx1", Name: "context1"}
	expectedResult := &agentbay.ContextDeleteResult{
		Success: true,
	}
	mockContext.EXPECT().Delete(ctx).Return(expectedResult, nil)

	// Test Delete method call
	result, err := mockContext.Delete(ctx)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.True(t, result.Success)
}

func TestContext_Error_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Context
	mockContext := mock.NewMockContextInterface(ctrl)

	// Set expected behavior - return error
	params := &agentbay.ContextListParams{
		MaxResults: 10,
		NextToken:  "",
	}
	mockContext.EXPECT().List(params).Return(nil, assert.AnError)

	// Test error case
	result, err := mockContext.List(params)

	// Verify error handling
	assert.Error(t, err)
	assert.Nil(t, result)
}
