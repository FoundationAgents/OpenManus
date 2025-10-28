package interfaces

import (
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

//go:generate mockgen -destination=../../../tests/pkg/unit/mock/mock_session_pagination.go -package=mock github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/interface SessionPaginationInterface

// SessionPaginationInterface defines the interface for session pagination operations
type SessionPaginationInterface interface {
	// ListByLabels lists sessions by labels with pagination
	ListByLabels(labels map[string]string, maxResults int32, nextToken string) (*agentbay.SessionListResult, error)
}
