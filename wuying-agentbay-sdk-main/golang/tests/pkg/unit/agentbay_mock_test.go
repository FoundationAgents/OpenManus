package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/unit/mock"
	"github.com/golang/mock/gomock"
	"github.com/stretchr/testify/assert"
)

func TestAgentBay_Create_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock AgentBay
	mockAgentBay := mock.NewMockAgentBayInterface(ctrl)

	// Set expected behavior
	params := &agentbay.CreateSessionParams{
		Labels: map[string]string{"env": "test"},
	}
	expectedResult := &agentbay.SessionResult{
		Session: &agentbay.Session{
			SessionID: "new_session_id",
		},
	}
	mockAgentBay.EXPECT().Create(params).Return(expectedResult, nil)

	// Test Create method call
	result, err := mockAgentBay.Create(params)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "new_session_id", result.Session.SessionID)
}

func TestAgentBay_Delete_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock AgentBay
	mockAgentBay := mock.NewMockAgentBayInterface(ctrl)

	// Set expected behavior
	session := &agentbay.Session{
		SessionID: "test_session_id",
	}
	expectedResult := &agentbay.DeleteResult{
		Success: true,
	}
	mockAgentBay.EXPECT().Delete(session).Return(expectedResult, nil)

	// Test Delete method call
	result, err := mockAgentBay.Delete(session)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.True(t, result.Success)
}

func TestAgentBay_List_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock AgentBay
	mockAgentBay := mock.NewMockAgentBayInterface(ctrl)

	// Set expected behavior
	expectedResult := &agentbay.SessionListResult{
		SessionIds: []string{"session-1", "session-2"},
		NextToken:  "next-page-token",
		MaxResults: 5,
		TotalCount: 15,
	}
	params := &agentbay.ListSessionParams{}
	mockAgentBay.EXPECT().ListByLabels(params).Return(expectedResult, nil)

	// Test ListByLabels method call
	result, err := mockAgentBay.ListByLabels(params)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Len(t, result.SessionIds, 2)
	assert.Equal(t, "session-1", result.SessionIds[0])
	assert.Equal(t, "session-2", result.SessionIds[1])
	assert.Equal(t, "next-page-token", result.NextToken)
	assert.Equal(t, int32(5), result.MaxResults)
	assert.Equal(t, int32(15), result.TotalCount)
}

func TestAgentBay_ListByLabels_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock AgentBay
	mockAgentBay := mock.NewMockAgentBayInterface(ctrl)

	// Set expected behavior
	params := &agentbay.ListSessionParams{
		MaxResults: 10,
		NextToken:  "next-token",
		Labels:     map[string]string{"env": "test"},
	}
	expectedResult := &agentbay.SessionListResult{
		SessionIds: []string{"session-1", "session-2"},
		NextToken:  "next-page-token",
		MaxResults: 10,
		TotalCount: 20,
	}
	mockAgentBay.EXPECT().ListByLabels(params).Return(expectedResult, nil)

	// Test ListByLabels method call
	result, err := mockAgentBay.ListByLabels(params)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Len(t, result.SessionIds, 2)
	assert.Equal(t, "session-1", result.SessionIds[0])
	assert.Equal(t, "session-2", result.SessionIds[1])
	assert.Equal(t, "next-page-token", result.NextToken)
	assert.Equal(t, int32(10), result.MaxResults)
	assert.Equal(t, int32(20), result.TotalCount)
}

func TestAgentBay_List_NoLabels_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock AgentBay
	mockAgentBay := mock.NewMockAgentBayInterface(ctrl)

	// Set expected behavior - list all sessions without labels
	expectedResult := &agentbay.SessionListResult{
		SessionIds: []string{"session-1", "session-2", "session-3"},
		MaxResults: 10,
		TotalCount: 3,
	}
	mockAgentBay.EXPECT().List(nil, nil, nil).Return(expectedResult, nil)

	// Test List method call without labels
	result, err := mockAgentBay.List(nil, nil, nil)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Len(t, result.SessionIds, 3)
	assert.Equal(t, "session-1", result.SessionIds[0])
	assert.Equal(t, int32(10), result.MaxResults)
	assert.Equal(t, int32(3), result.TotalCount)
}

func TestAgentBay_List_WithLabels_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock AgentBay
	mockAgentBay := mock.NewMockAgentBayInterface(ctrl)

	// Set expected behavior - list sessions with labels
	labels := map[string]string{"env": "prod"}
	expectedResult := &agentbay.SessionListResult{
		SessionIds: []string{"session-prod-1"},
		MaxResults: 10,
		TotalCount: 1,
	}
	mockAgentBay.EXPECT().List(labels, nil, nil).Return(expectedResult, nil)

	// Test List method call with labels
	result, err := mockAgentBay.List(labels, nil, nil)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Len(t, result.SessionIds, 1)
	assert.Equal(t, "session-prod-1", result.SessionIds[0])
}

func TestAgentBay_List_WithPagination_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock AgentBay
	mockAgentBay := mock.NewMockAgentBayInterface(ctrl)

	// Set expected behavior - list sessions with pagination
	labels := map[string]string{"env": "prod"}
	page := 2
	limit := int32(5)
	expectedResult := &agentbay.SessionListResult{
		SessionIds: []string{"session-6", "session-7"},
		MaxResults: 5,
		TotalCount: 10,
	}
	mockAgentBay.EXPECT().List(labels, &page, &limit).Return(expectedResult, nil)

	// Test List method call with pagination
	result, err := mockAgentBay.List(labels, &page, &limit)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Len(t, result.SessionIds, 2)
	assert.Equal(t, "session-6", result.SessionIds[0])
	assert.Equal(t, int32(5), result.MaxResults)
	assert.Equal(t, int32(10), result.TotalCount)
}

func TestAgentBay_Error_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock AgentBay
	mockAgentBay := mock.NewMockAgentBayInterface(ctrl)

	// Set expected behavior - return error
	params := &agentbay.ListSessionParams{}
	mockAgentBay.EXPECT().ListByLabels(params).Return(nil, assert.AnError)

	// Test error case
	result, err := mockAgentBay.ListByLabels(params)

	// Verify error handling
	assert.Error(t, err)
	assert.Nil(t, result)
}
