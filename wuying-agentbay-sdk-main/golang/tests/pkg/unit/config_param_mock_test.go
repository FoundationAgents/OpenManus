package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/unit/mock"
	"github.com/golang/mock/gomock"
	"github.com/stretchr/testify/assert"
)

func TestConfig_LoadConfig_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Config
	mockConfig := mock.NewMockConfigInterface(ctrl)

	// Set expected behavior
	inputConfig := &agentbay.Config{
		Endpoint:  "example.com",
		TimeoutMs: 5000,
	}
	expectedResult := agentbay.Config{
		Endpoint:  "example.com",
		TimeoutMs: 5000,
	}
	mockConfig.EXPECT().LoadConfig(inputConfig).Return(expectedResult)

	// Test LoadConfig method call
	result := mockConfig.LoadConfig(inputConfig)

	// Verify call success
	assert.Equal(t, "example.com", result.Endpoint)
	assert.Equal(t, 5000, result.TimeoutMs)
}

func TestConfig_DefaultConfig_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Config
	mockConfig := mock.NewMockConfigInterface(ctrl)

	// Set expected behavior
	expectedResult := agentbay.Config{
		Endpoint:  "wuying.aliyuncs.com",
		TimeoutMs: 30000,
	}
	mockConfig.EXPECT().DefaultConfig().Return(expectedResult)

	// Test DefaultConfig method call
	result := mockConfig.DefaultConfig()

	// Verify call success
	assert.Equal(t, "wuying.aliyuncs.com", result.Endpoint)
	assert.Equal(t, 30000, result.TimeoutMs)
}
