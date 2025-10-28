package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/unit/mock"
	"github.com/golang/mock/gomock"
	"github.com/stretchr/testify/assert"
)

func TestModel_GetRequestID_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Model
	mockModel := mock.NewMockModelInterface(ctrl)

	// Set expected behavior
	mockModel.EXPECT().GetRequestID().Return("test-request-id")

	// Test GetRequestID method call
	result := mockModel.GetRequestID()

	// Verify call success
	assert.Equal(t, "test-request-id", result)
}

func TestModel_WithRequestID_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Model
	mockModel := mock.NewMockModelInterface(ctrl)

	// Set expected behavior
	expectedResult := models.ApiResponse{
		RequestID: "test-request-id",
	}
	mockModel.EXPECT().WithRequestID("test-request-id").Return(expectedResult)

	// Test WithRequestID method call
	result := mockModel.WithRequestID("test-request-id")

	// Verify call success
	assert.Equal(t, "test-request-id", result.RequestID)
}

func TestModel_ExtractRequestID_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Model
	mockModel := mock.NewMockModelInterface(ctrl)

	// Set expected behavior
	mockResponse := map[string]interface{}{
		"Body": map[string]interface{}{
			"RequestId": "test-request-id",
		},
	}
	mockModel.EXPECT().ExtractRequestID(mockResponse).Return("test-request-id")

	// Test ExtractRequestID method call
	result := mockModel.ExtractRequestID(mockResponse)

	// Verify call success
	assert.Equal(t, "test-request-id", result)
}

func TestModel_ExtractRequestID_WithNilResponse_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock Model
	mockModel := mock.NewMockModelInterface(ctrl)

	// Set expected behavior - nil response returns empty string
	mockModel.EXPECT().ExtractRequestID(nil).Return("")

	// Test ExtractRequestID method call with nil
	result := mockModel.ExtractRequestID(nil)

	// Verify call success
	assert.Equal(t, "", result)
}
