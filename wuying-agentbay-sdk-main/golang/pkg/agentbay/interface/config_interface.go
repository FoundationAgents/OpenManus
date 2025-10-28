package interfaces

import (
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

//go:generate mockgen -destination=../../../tests/pkg/unit/mock/mock_config.go -package=mock github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/interface ConfigInterface

// ConfigInterface defines the interface for configuration operations
type ConfigInterface interface {
	// LoadConfig loads configuration from file or environment variables
	LoadConfig(cfg *agentbay.Config) agentbay.Config

	// DefaultConfig returns the default configuration
	DefaultConfig() agentbay.Config
}
