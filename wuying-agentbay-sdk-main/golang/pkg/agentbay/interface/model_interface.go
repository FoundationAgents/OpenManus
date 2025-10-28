package interfaces

import (
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

//go:generate mockgen -destination=../../../tests/pkg/unit/mock/mock_model.go -package=mock github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/interface ModelInterface

// ModelInterface defines the interface for model operations
type ModelInterface interface {
	// GetRequestID returns the unique identifier for the API request
	GetRequestID() string

	// WithRequestID creates a new ApiResponse with the specified RequestID
	WithRequestID(requestID string) models.ApiResponse

	// ExtractRequestID extracts RequestID from API response
	ExtractRequestID(response interface{}) string
}
