package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/application"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/unit/mock"
	"github.com/golang/mock/gomock"
	"github.com/stretchr/testify/assert"
)

func TestApplication_GetInstalledApps_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Application
	mockApp := mock.NewMockApplicationInterface(ctrl)

	// Set expected behavior
	expectedResult := &application.ApplicationListResult{
		Applications: []application.Application{
			{ID: "app1", Name: "App 1"},
			{ID: "app2", Name: "App 2"},
		},
	}
	mockApp.EXPECT().GetInstalledApps(true, true, false).Return(expectedResult, nil)

	// Test GetInstalledApps method call
	result, err := mockApp.GetInstalledApps(true, true, false)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Len(t, result.Applications, 2)
	assert.Equal(t, "app1", result.Applications[0].ID)
	assert.Equal(t, "app2", result.Applications[1].ID)
}

func TestApplication_StartApp_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Application
	mockApp := mock.NewMockApplicationInterface(ctrl)

	// Set expected behavior
	expectedResult := &application.ProcessListResult{
		Processes: []application.Process{
			{PName: "test_app", PID: 123},
		},
	}
	mockApp.EXPECT().StartApp("test_app", "/tmp", "").Return(expectedResult, nil)

	// Test StartApp method call
	result, err := mockApp.StartApp("test_app", "/tmp", "")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Len(t, result.Processes, 1)
	assert.Equal(t, "test_app", result.Processes[0].PName)
	assert.Equal(t, 123, result.Processes[0].PID)
}

func TestApplication_StopAppByPName_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Application
	mockApp := mock.NewMockApplicationInterface(ctrl)

	// Set expected behavior
	expectedResult := &application.AppOperationResult{
		Success: true,
	}
	mockApp.EXPECT().StopAppByPName("test_app").Return(expectedResult, nil)

	// Test StopAppByPName method call
	result, err := mockApp.StopAppByPName("test_app")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.True(t, result.Success)
}

func TestApplication_StopAppByPID_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Application
	mockApp := mock.NewMockApplicationInterface(ctrl)

	// Set expected behavior
	expectedResult := &application.AppOperationResult{
		Success: true,
	}
	mockApp.EXPECT().StopAppByPID(123).Return(expectedResult, nil)

	// Test StopAppByPID method call
	result, err := mockApp.StopAppByPID(123)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.True(t, result.Success)
}

func TestApplication_ListVisibleApps_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Application
	mockApp := mock.NewMockApplicationInterface(ctrl)

	// Set expected behavior
	expectedResult := &application.ProcessListResult{
		Processes: []application.Process{
			{PName: "app1", PID: 123},
			{PName: "app2", PID: 456},
		},
	}
	mockApp.EXPECT().ListVisibleApps().Return(expectedResult, nil)

	// Test ListVisibleApps method call
	result, err := mockApp.ListVisibleApps()

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Len(t, result.Processes, 2)
	assert.Equal(t, "app1", result.Processes[0].PName)
	assert.Equal(t, 123, result.Processes[0].PID)
	assert.Equal(t, "app2", result.Processes[1].PName)
	assert.Equal(t, 456, result.Processes[1].PID)
}

func TestApplication_Error_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Application
	mockApp := mock.NewMockApplicationInterface(ctrl)

	// Set expected behavior - return error
	mockApp.EXPECT().GetInstalledApps(true, true, false).Return(nil, assert.AnError)

	// Test error case
	result, err := mockApp.GetInstalledApps(true, true, false)

	// Verify error handling
	assert.Error(t, err)
	assert.Nil(t, result)
}
