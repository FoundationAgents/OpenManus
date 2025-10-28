package agent

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

// ExecutionResult represents the result of task execution
type ExecutionResult struct {
	models.ApiResponse
	Success      bool   `json:"success"`
	ErrorMessage string `json:"error_message"`
	TaskID       string `json:"task_id"`
	TaskStatus   string `json:"task_status"`
}

// QueryResult represents the result of query operations
type QueryResult struct {
	models.ApiResponse
	Success      bool   `json:"success"`
	Output       string `json:"output"`
	ErrorMessage string `json:"error_message"`
}

// Agent represents an agent to manipulate applications to complete specific tasks
type Agent struct {
	Session McpSession
}

// McpSession interface defines the methods needed by Agent
type McpSession interface {
	GetAPIKey() string
	GetSessionId() string
	CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error)
}

// NewAgent creates a new Agent instance
func NewAgent(session McpSession) *Agent {
	return &Agent{
		Session: session,
	}
}

// ExecuteTask executes a specific task described in human language
func (a *Agent) ExecuteTask(task string, maxTryTimes int) *ExecutionResult {
	args := map[string]interface{}{
		"task": task,
	}

	result, err := a.Session.CallMcpTool("flux_execute_task", args)
	if err != nil {
		return &ExecutionResult{
			ApiResponse:  models.ApiResponse{RequestID: ""},
			Success:      false,
			ErrorMessage: fmt.Sprintf("Failed to execute: %v", err),
			TaskStatus:   "failed",
			TaskID:       "",
		}
	}

	if !result.Success {
		return &ExecutionResult{
			ApiResponse:  models.ApiResponse{RequestID: result.RequestID},
			Success:      false,
			ErrorMessage: result.ErrorMessage,
			TaskStatus:   "failed",
			TaskID:       "",
		}
	}

	// Parse task ID from response
	var content map[string]interface{}
	if err := json.Unmarshal([]byte(result.Data), &content); err != nil {
		return &ExecutionResult{
			ApiResponse:  models.ApiResponse{RequestID: result.RequestID},
			Success:      false,
			ErrorMessage: fmt.Sprintf("Failed to parse response: %v", err),
			TaskStatus:   "failed",
			TaskID:       "",
		}
	}

	taskID, ok := content["task_id"].(string)
	if !ok {
		return &ExecutionResult{
			ApiResponse:  models.ApiResponse{RequestID: result.RequestID},
			Success:      false,
			ErrorMessage: "Task ID not found in response",
			TaskStatus:   "failed",
			TaskID:       "",
		}
	}

	// Poll for task completion
	triedTime := 0
	for triedTime < maxTryTimes {
		query := a.GetTaskStatus(taskID)
		if !query.Success {
			return &ExecutionResult{
				ApiResponse:  models.ApiResponse{RequestID: result.RequestID},
				Success:      false,
				ErrorMessage: query.ErrorMessage,
				TaskStatus:   "failed",
				TaskID:       taskID,
			}
		}

		var statusContent map[string]interface{}
		if err := json.Unmarshal([]byte(query.Output), &statusContent); err != nil {
			return &ExecutionResult{
				ApiResponse:  models.ApiResponse{RequestID: result.RequestID},
				Success:      false,
				ErrorMessage: fmt.Sprintf("Failed to parse status response: %v", err),
				TaskStatus:   "failed",
				TaskID:       taskID,
			}
		}

		taskStatus, ok := statusContent["status"].(string)
		if !ok {
			return &ExecutionResult{
				ApiResponse:  models.ApiResponse{RequestID: result.RequestID},
				Success:      false,
				ErrorMessage: "Task status not found in response",
				TaskStatus:   "failed",
				TaskID:       taskID,
			}
		}

		switch taskStatus {
		case "finished":
			return &ExecutionResult{
				ApiResponse:  models.ApiResponse{RequestID: result.RequestID},
				Success:      true,
				ErrorMessage: "",
				TaskID:       taskID,
				TaskStatus:   taskStatus,
			}
		case "failed":
			return &ExecutionResult{
				ApiResponse:  models.ApiResponse{RequestID: result.RequestID},
				Success:      false,
				ErrorMessage: "Failed to execute task.",
				TaskID:       taskID,
				TaskStatus:   taskStatus,
			}
		case "unsupported":
			return &ExecutionResult{
				ApiResponse:  models.ApiResponse{RequestID: result.RequestID},
				Success:      false,
				ErrorMessage: "Unsupported task.",
				TaskID:       taskID,
				TaskStatus:   taskStatus,
			}
		}

		fmt.Printf("Task %s is still running, please wait for a while.\n", taskID)
		time.Sleep(3 * time.Second)
		triedTime++
	}

	return &ExecutionResult{
		ApiResponse:  models.ApiResponse{RequestID: result.RequestID},
		Success:      false,
		ErrorMessage: "Task execution timed out",
		TaskStatus:   "timeout",
		TaskID:       taskID,
	}
}

// GetTaskStatus gets the status of the task with the given task ID
func (a *Agent) GetTaskStatus(taskID string) *QueryResult {
	args := map[string]interface{}{
		"task_id": taskID,
	}

	result, err := a.Session.CallMcpTool("flux_get_task_status", args)
	if err != nil {
		return &QueryResult{
			ApiResponse:  models.ApiResponse{RequestID: ""},
			Success:      false,
			ErrorMessage: fmt.Sprintf("Failed to get task status: %v", err),
		}
	}

	if !result.Success {
		return &QueryResult{
			ApiResponse:  models.ApiResponse{RequestID: result.RequestID},
			Success:      false,
			ErrorMessage: result.ErrorMessage,
		}
	}

	return &QueryResult{
		ApiResponse: models.ApiResponse{RequestID: result.RequestID},
		Success:     true,
		Output:      result.Data,
	}
}

// TerminateTask terminates a task with a specified task ID
func (a *Agent) TerminateTask(taskID string) *ExecutionResult {
	fmt.Println("Terminating task")

	args := map[string]interface{}{
		"task_id": taskID,
	}

	result, err := a.Session.CallMcpTool("flux_terminate_task", args)
	if err != nil {
		return &ExecutionResult{
			ApiResponse:  models.ApiResponse{RequestID: ""},
			Success:      false,
			ErrorMessage: fmt.Sprintf("Failed to terminate: %v", err),
			TaskID:       taskID,
			TaskStatus:   "failed",
		}
	}

	var content map[string]interface{}
	if err := json.Unmarshal([]byte(result.Data), &content); err != nil {
		return &ExecutionResult{
			ApiResponse:  models.ApiResponse{RequestID: result.RequestID},
			Success:      false,
			ErrorMessage: fmt.Sprintf("Failed to parse response: %v", err),
			TaskID:       taskID,
			TaskStatus:   "failed",
		}
	}

	terminatedTaskID, ok := content["task_id"].(string)
	if !ok {
		terminatedTaskID = taskID
	}

	status, ok := content["status"].(string)
	if !ok {
		status = "unknown"
	}

	if result.Success {
		return &ExecutionResult{
			ApiResponse:  models.ApiResponse{RequestID: result.RequestID},
			Success:      true,
			ErrorMessage: "",
			TaskID:       terminatedTaskID,
			TaskStatus:   status,
		}
	}

	return &ExecutionResult{
		ApiResponse:  models.ApiResponse{RequestID: result.RequestID},
		Success:      false,
		ErrorMessage: result.ErrorMessage,
		TaskID:       terminatedTaskID,
		TaskStatus:   status,
	}
}
