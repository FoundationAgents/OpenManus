package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/unit/mock"
	"github.com/golang/mock/gomock"
	"github.com/stretchr/testify/assert"
)

func TestSessionPagination_ListByLabels_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock SessionPagination
	mockPagination := mock.NewMockSessionPaginationInterface(ctrl)

	// Set expected behavior
	labels := map[string]string{"env": "test"}
	expectedResult := &agentbay.SessionListResult{
		SessionIds: []string{"session-1", "session-2", "session-3"},
		NextToken:  "next-page-token",
		MaxResults: 5,
		TotalCount: 15,
	}
	mockPagination.EXPECT().ListByLabels(labels, int32(5), "").Return(expectedResult, nil)

	// Test ListByLabels method call
	result, err := mockPagination.ListByLabels(labels, 5, "")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Len(t, result.SessionIds, 3)
	assert.Equal(t, "session-1", result.SessionIds[0])
	assert.Equal(t, "session-2", result.SessionIds[1])
	assert.Equal(t, "session-3", result.SessionIds[2])
	assert.Equal(t, "next-page-token", result.NextToken)
	assert.Equal(t, int32(5), result.MaxResults)
	assert.Equal(t, int32(15), result.TotalCount)
}

func TestSessionPagination_ListByLabels_Empty_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock SessionPagination
	mockPagination := mock.NewMockSessionPaginationInterface(ctrl)

	// Set expected behavior
	labels := map[string]string{"env": "test"}
	expectedResult := &agentbay.SessionListResult{
		SessionIds: []string{},
		NextToken:  "",
		MaxResults: 5,
		TotalCount: 0,
	}
	mockPagination.EXPECT().ListByLabels(labels, int32(5), "").Return(expectedResult, nil)

	// Test ListByLabels method call
	result, err := mockPagination.ListByLabels(labels, 5, "")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Empty(t, result.SessionIds)
	assert.Equal(t, "", result.NextToken)
	assert.Equal(t, int32(5), result.MaxResults)
	assert.Equal(t, int32(0), result.TotalCount)
}

func TestSessionPagination_ListByLabels_Error_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock SessionPagination
	mockPagination := mock.NewMockSessionPaginationInterface(ctrl)

	// Set expected behavior - return error
	labels := map[string]string{"env": "test"}
	mockPagination.EXPECT().ListByLabels(labels, int32(5), "").Return(nil, assert.AnError)

	// Test error case
	result, err := mockPagination.ListByLabels(labels, 5, "")

	// Verify error handling
	assert.Error(t, err)
	assert.Nil(t, result)
}
