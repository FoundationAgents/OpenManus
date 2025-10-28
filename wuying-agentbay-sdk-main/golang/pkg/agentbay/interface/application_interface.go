package interfaces

import (
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/application"
)

//go:generate mockgen -destination=../../../tests/pkg/unit/mock/mock_application.go -package=mock github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/interface ApplicationInterface

// ApplicationInterface defines the interface for application operations
type ApplicationInterface interface {
	// GetInstalledApps retrieves a list of installed applications
	GetInstalledApps(startMenu bool, desktop bool, ignoreSystemApps bool) (*application.ApplicationListResult, error)

	// StartApp starts an application with the given command
	StartApp(startCmd string, workDirectory string, activity string) (*application.ProcessListResult, error)

	// StopAppByPName stops an application by process name
	StopAppByPName(pname string) (*application.AppOperationResult, error)

	// StopAppByPID stops an application by process ID
	StopAppByPID(pid int) (*application.AppOperationResult, error)

	// StopAppByCmd stops an application by stop command
	StopAppByCmd(stopCmd string) (*application.AppOperationResult, error)

	// ListVisibleApps returns a list of currently visible applications
	ListVisibleApps() (*application.ProcessListResult, error)
}
