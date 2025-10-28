package application

import (
	"encoding/json"
	"fmt"

	mcp "github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

// Application represents an application
type Application struct {
	ID      string `json:"id"`
	Name    string `json:"name"`
	CmdLine string `json:"cmdline,omitempty"`
}

// InstalledApp represents an installed application
type InstalledApp struct {
	Name          string `json:"name"`
	StartCmd      string `json:"start_cmd"`
	StopCmd       string `json:"stop_cmd,omitempty"`
	WorkDirectory string `json:"work_directory,omitempty"`
}

// Process represents a running process
type Process struct {
	PName   string `json:"pname"`
	PID     int    `json:"pid"`
	CmdLine string `json:"cmdline,omitempty"`
}

// ApplicationListResult wraps application list and RequestID
type ApplicationListResult struct {
	models.ApiResponse
	Applications []Application
}

// AppOperationResult wraps application operation result and RequestID
type AppOperationResult struct {
	models.ApiResponse
	Success bool
}

// ProcessListResult wraps process list and RequestID
type ProcessListResult struct {
	models.ApiResponse
	Processes []Process
}

// ApplicationManager handles application management operations in the AgentBay cloud environment.
type ApplicationManager struct {
	Session interface {
		GetAPIKey() string
		GetClient() *mcp.Client
		GetSessionId() string
		IsVpc() bool
		NetworkInterfaceIp() string
		HttpPort() string
		FindServerForTool(toolName string) string
		CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error)
	}
}

// parseInstalledAppsFromJSON parses JSON string into array of InstalledApp objects
func parseInstalledAppsFromJSON(jsonStr string) ([]InstalledApp, error) {
	var apps []InstalledApp
	err := json.Unmarshal([]byte(jsonStr), &apps)
	if err != nil {
		return nil, fmt.Errorf("failed to parse applications JSON: %w", err)
	}
	return apps, nil
}

// parseProcessesFromJSON parses JSON string into array of Process objects
func parseProcessesFromJSON(jsonStr string) ([]Process, error) {
	var processes []Process
	err := json.Unmarshal([]byte(jsonStr), &processes)
	if err != nil {
		return nil, fmt.Errorf("failed to parse processes JSON: %w", err)
	}
	return processes, nil
}

// NewApplicationManager creates a new ApplicationManager object.
func NewApplicationManager(session interface {
	GetAPIKey() string
	GetClient() *mcp.Client
	GetSessionId() string
	IsVpc() bool
	NetworkInterfaceIp() string
	HttpPort() string
	FindServerForTool(toolName string) string
	CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error)
}) *ApplicationManager {
	return &ApplicationManager{
		Session: session,
	}
}

// GetInstalledApps retrieves a list of installed applications.
func (am *ApplicationManager) GetInstalledApps(startMenu bool, desktop bool, ignoreSystemApps bool) (*ApplicationListResult, error) {
	args := map[string]interface{}{
		"start_menu":         startMenu,
		"desktop":            desktop,
		"ignore_system_apps": ignoreSystemApps,
	}

	// Use Session's CallMcpTool method
	result, err := am.Session.CallMcpTool("get_installed_apps", args)
	if err != nil {
		return nil, fmt.Errorf("error getting installed apps: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("error getting installed apps: %s", result.ErrorMessage)
	}

	// Parse application list
	installedApps, err := parseInstalledAppsFromJSON(result.Data)
	if err != nil {
		return nil, err
	}

	// Convert to Application type
	var applications []Application
	for _, app := range installedApps {
		applications = append(applications, Application{
			ID:      app.Name, // Use Name as ID
			Name:    app.Name,
			CmdLine: app.StartCmd,
		})
	}

	return &ApplicationListResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Applications: applications,
	}, nil
}

// StartApp starts an application with the given command, optional working directory, and optional activity.
func (am *ApplicationManager) StartApp(startCmd string, workDirectory string, activity string) (*ProcessListResult, error) {
	args := map[string]interface{}{
		"start_cmd": startCmd,
	}
	if workDirectory != "" {
		args["work_directory"] = workDirectory
	}
	if activity != "" {
		args["activity"] = activity
	}

	// Use Session's CallMcpTool method
	result, err := am.Session.CallMcpTool("start_app", args)
	if err != nil {
		return nil, fmt.Errorf("error starting app: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("error starting app: %s", result.ErrorMessage)
	}

	// Parse process list
	processes, err := parseProcessesFromJSON(result.Data)
	if err != nil {
		return nil, err
	}

	return &ProcessListResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Processes: processes,
	}, nil
}

// StopAppByPName stops an application by process name.
func (am *ApplicationManager) StopAppByPName(pname string) (*AppOperationResult, error) {
	args := map[string]interface{}{
		"pname": pname,
	}

	// Use Session's CallMcpTool method
	result, err := am.Session.CallMcpTool("stop_app_by_pname", args)
	if err != nil {
		return nil, fmt.Errorf("error stopping app by process name: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("error stopping app by process name: %s", result.ErrorMessage)
	}

	return &AppOperationResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: true,
	}, nil
}

// StopAppByPID stops an application by its process ID.
func (am *ApplicationManager) StopAppByPID(pid int) (*AppOperationResult, error) {
	args := map[string]interface{}{
		"pid": pid,
	}

	// Use Session's CallMcpTool method
	result, err := am.Session.CallMcpTool("stop_app_by_pid", args)
	if err != nil {
		return nil, fmt.Errorf("error stopping app by PID: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("error stopping app by PID: %s", result.ErrorMessage)
	}

	return &AppOperationResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: true,
	}, nil
}

// StopAppByCmd stops an application by stop command.
func (am *ApplicationManager) StopAppByCmd(stopCmd string) (*AppOperationResult, error) {
	args := map[string]interface{}{
		"stop_cmd": stopCmd,
	}

	// Use Session's CallMcpTool method
	result, err := am.Session.CallMcpTool("stop_app_by_cmd", args)
	if err != nil {
		return nil, fmt.Errorf("error stopping app by command: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("error stopping app by command: %s", result.ErrorMessage)
	}

	return &AppOperationResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: true,
	}, nil
}

// ListVisibleApps returns a list of currently visible applications.
func (am *ApplicationManager) ListVisibleApps() (*ProcessListResult, error) {
	// Use Session's CallMcpTool method
	result, err := am.Session.CallMcpTool("list_visible_apps", nil)
	if err != nil {
		return nil, fmt.Errorf("error listing visible apps: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("error listing visible apps: %s", result.ErrorMessage)
	}

	// Parse process list
	processes, err := parseProcessesFromJSON(result.Data)
	if err != nil {
		return nil, err
	}

	return &ProcessListResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Processes: processes,
	}, nil
}
