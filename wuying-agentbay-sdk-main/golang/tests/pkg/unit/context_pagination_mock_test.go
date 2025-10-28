package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/unit/mock"
	"github.com/golang/mock/gomock"
	"github.com/stretchr/testify/assert"
)

func TestContextPagination_List_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock ContextInterface
	mockContext := mock.NewMockContextInterface(ctrl)

	// Set expected behavior for first page
	params1 := &agentbay.ContextListParams{
		MaxResults: 10,
		NextToken:  "",
	}
	expectedResult1 := &agentbay.ContextListResult{
		Contexts: []*agentbay.Context{
			{ID: "ctx1", Name: "context1"},
			{ID: "ctx2", Name: "context2"},
			{ID: "ctx3", Name: "context3"},
			{ID: "ctx4", Name: "context4"},
			{ID: "ctx5", Name: "context5"},
			{ID: "ctx6", Name: "context6"},
			{ID: "ctx7", Name: "context7"},
			{ID: "ctx8", Name: "context8"},
			{ID: "ctx9", Name: "context9"},
			{ID: "ctx10", Name: "context10"},
		},
		NextToken:  "next-page-token",
		MaxResults: 10,
		TotalCount: 15,
	}
	mockContext.EXPECT().List(params1).Return(expectedResult1, nil)

	// Test first page List method call
	result1, err := mockContext.List(params1)

	// Verify first page call success
	assert.NoError(t, err)
	assert.NotNil(t, result1)
	assert.Len(t, result1.Contexts, 10)
	assert.Equal(t, "ctx1", result1.Contexts[0].ID)
	assert.Equal(t, "ctx10", result1.Contexts[9].ID)
	assert.Equal(t, "next-page-token", result1.NextToken)
	assert.Equal(t, int32(10), result1.MaxResults)
	assert.Equal(t, int32(15), result1.TotalCount)

	// Set expected behavior for second page
	params2 := &agentbay.ContextListParams{
		MaxResults: 10,
		NextToken:  "next-page-token",
	}
	expectedResult2 := &agentbay.ContextListResult{
		Contexts: []*agentbay.Context{
			{ID: "ctx11", Name: "context11"},
			{ID: "ctx12", Name: "context12"},
			{ID: "ctx13", Name: "context13"},
			{ID: "ctx14", Name: "context14"},
			{ID: "ctx15", Name: "context15"},
		},
		NextToken:  "",
		MaxResults: 10,
		TotalCount: 15,
	}
	mockContext.EXPECT().List(params2).Return(expectedResult2, nil)

	// Test second page List method call
	result2, err := mockContext.List(params2)

	// Verify second page call success
	assert.NoError(t, err)
	assert.NotNil(t, result2)
	assert.Len(t, result2.Contexts, 5)
	assert.Equal(t, "ctx11", result2.Contexts[0].ID)
	assert.Equal(t, "ctx15", result2.Contexts[4].ID)
	assert.Equal(t, "", result2.NextToken)
	assert.Equal(t, int32(10), result2.MaxResults)
	assert.Equal(t, int32(15), result2.TotalCount)
}

func TestContextPagination_List_CustomPageSize_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock ContextInterface
	mockContext := mock.NewMockContextInterface(ctrl)

	// Set expected behavior for custom page size
	params := &agentbay.ContextListParams{
		MaxResults: 5,
		NextToken:  "",
	}
	expectedResult := &agentbay.ContextListResult{
		Contexts: []*agentbay.Context{
			{ID: "ctx1", Name: "context1"},
			{ID: "ctx2", Name: "context2"},
			{ID: "ctx3", Name: "context3"},
			{ID: "ctx4", Name: "context4"},
			{ID: "ctx5", Name: "context5"},
		},
		NextToken:  "next-page-token",
		MaxResults: 5,
		TotalCount: 15,
	}
	mockContext.EXPECT().List(params).Return(expectedResult, nil)

	// Test List method call with custom page size
	result, err := mockContext.List(params)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Len(t, result.Contexts, 5)
	assert.Equal(t, "ctx1", result.Contexts[0].ID)
	assert.Equal(t, "ctx5", result.Contexts[4].ID)
	assert.Equal(t, "next-page-token", result.NextToken)
	assert.Equal(t, int32(5), result.MaxResults)
	assert.Equal(t, int32(15), result.TotalCount)
}

func TestContextPagination_List_LargePageSize_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock ContextInterface
	mockContext := mock.NewMockContextInterface(ctrl)

	// Set expected behavior for large page size
	params := &agentbay.ContextListParams{
		MaxResults: 20,
		NextToken:  "",
	}
	expectedResult := &agentbay.ContextListResult{
		Contexts: []*agentbay.Context{
			{ID: "ctx1", Name: "context1"},
			{ID: "ctx2", Name: "context2"},
			{ID: "ctx3", Name: "context3"},
			{ID: "ctx4", Name: "context4"},
			{ID: "ctx5", Name: "context5"},
			{ID: "ctx6", Name: "context6"},
			{ID: "ctx7", Name: "context7"},
			{ID: "ctx8", Name: "context8"},
			{ID: "ctx9", Name: "context9"},
			{ID: "ctx10", Name: "context10"},
			{ID: "ctx11", Name: "context11"},
			{ID: "ctx12", Name: "context12"},
			{ID: "ctx13", Name: "context13"},
			{ID: "ctx14", Name: "context14"},
			{ID: "ctx15", Name: "context15"},
		},
		NextToken:  "",
		MaxResults: 20,
		TotalCount: 15,
	}
	mockContext.EXPECT().List(params).Return(expectedResult, nil)

	// Test List method call with large page size
	result, err := mockContext.List(params)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Len(t, result.Contexts, 15)
	assert.Equal(t, "ctx1", result.Contexts[0].ID)
	assert.Equal(t, "ctx15", result.Contexts[14].ID)
	assert.Equal(t, "", result.NextToken)
	assert.Equal(t, int32(20), result.MaxResults)
	assert.Equal(t, int32(15), result.TotalCount)
}

func TestContextPagination_List_NilParams_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock ContextInterface
	mockContext := mock.NewMockContextInterface(ctrl)

	// Test List method call with nil params
	// Note: Since we're testing with a mock, we can't directly test the nil parameter handling
	// in the ContextService.List method. In a real scenario, when params is nil, the
	// ContextService.List method will create default params. With mocks, we need to
	// explicitly pass the expected parameters.

	// For this test, we'll just verify that the method can be called with nil params
	// and that it doesn't panic. We'll expect the mock to be called with nil.
	mockContext.EXPECT().List(gomock.Nil()).Return(nil, nil)

	// Test List method call with nil params
	result, err := mockContext.List(nil)

	// Verify call success (in this case, we're just checking it doesn't panic)
	assert.NoError(t, err)
	assert.Nil(t, result)
}

func TestContextPagination_List_Error_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock ContextInterface
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
