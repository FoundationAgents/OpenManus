package interfaces

import (
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

//go:generate mockgen -destination=../../../tests/pkg/unit/mock/mock_session_params.go -package=mock github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/interface SessionParamsInterface

// SessionParamsInterface defines the interface for session parameter operations
type SessionParamsInterface interface {
	// NewCreateSessionParams creates a new CreateSessionParams with default values
	NewCreateSessionParams() *agentbay.CreateSessionParams

	// WithLabels sets the labels for the session parameters
	WithLabels(labels map[string]string) *agentbay.CreateSessionParams

	// WithContextID sets the context ID for the session parameters
	WithContextID(contextID string) *agentbay.CreateSessionParams

	// WithImageId sets the image ID for the session parameters
	WithImageId(imageId string) *agentbay.CreateSessionParams

	// GetLabelsJSON returns the labels as a JSON string
	GetLabelsJSON() (string, error)

	// AddContextSync adds a context sync configuration
	AddContextSync(contextID, path string, policy *agentbay.SyncPolicy) *agentbay.CreateSessionParams

	// AddContextSyncConfig adds a pre-configured context sync
	AddContextSyncConfig(contextSync *agentbay.ContextSync) *agentbay.CreateSessionParams

	// WithContextSync sets the context sync configurations
	WithContextSync(contextSyncs []*agentbay.ContextSync) *agentbay.CreateSessionParams
}
