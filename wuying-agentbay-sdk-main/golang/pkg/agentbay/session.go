package agentbay

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"

	"math/rand"

	"github.com/alibabacloud-go/tea/tea"
	mcp "github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/agent"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/application"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/code"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/command"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/computer"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/filesystem"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/mobile"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/oss"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/ui"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/utils"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/window"
)

// SessionResult wraps Session object and RequestID
type SessionResult struct {
	models.ApiResponse
	Session      *Session
	Success      bool
	ErrorMessage string
}

// SessionListResult wraps Session list and RequestID
type SessionListResult struct {
	models.ApiResponse
	SessionIds []string // Session IDs
	NextToken  string   // Token for the next page
	MaxResults int32    // Number of results per page
	TotalCount int32    // Total number of results
}

// InfoResult wraps SessionInfo and RequestID
type InfoResult struct {
	models.ApiResponse
	Info *SessionInfo
}

// LabelResult wraps label operation result and RequestID
type LabelResult struct {
	models.ApiResponse
	Labels string
}

// LinkResult wraps link result and RequestID
type LinkResult struct {
	models.ApiResponse
	Link string
}

// DeleteResult wraps deletion operation result and RequestID
type DeleteResult struct {
	models.ApiResponse
	Success      bool
	ErrorMessage string
}

// McpTool represents an MCP tool with complete information
type McpTool struct {
	Name        string                 `json:"name"`        // Tool name
	Description string                 `json:"description"` // Tool description
	InputSchema map[string]interface{} `json:"inputSchema"` // Input parameter schema
	Server      string                 `json:"server"`      // Server name that provides this tool
	Tool        string                 `json:"tool"`        // Tool identifier
}

// GetName returns the tool name
func (m *McpTool) GetName() string {
	return m.Name
}

// GetServer returns the server name that provides this tool
func (m *McpTool) GetServer() string {
	return m.Server
}

// McpToolsResult wraps MCP tools list and RequestID
type McpToolsResult struct {
	models.ApiResponse
	Tools []McpTool
}

// SessionInfo contains information about a session.
type SessionInfo struct {
	SessionId            string
	ResourceUrl          string
	AppId                string
	AuthCode             string
	ConnectionProperties string
	ResourceId           string
	ResourceType         string
	Ticket               string
}

// Session represents a session in the AgentBay cloud environment.
type Session struct {
	AgentBay  *AgentBay
	SessionID string
	ImageId   string // ImageId used when creating this session

	// VPC-related information
	IsVpcEnabled       bool   // Whether this session uses VPC resources
	NetworkInterfaceIP string // Network interface IP for VPC sessions
	HttpPortNumber     string // HTTP port for VPC sessions
	Token              string // Token for VPC sessions

	// Resource URL for accessing the session
	ResourceUrl string

	// File, command and code handlers
	FileSystem *filesystem.FileSystem
	Command    *command.Command
	Code       *code.Code
	Oss        *oss.OSSManager

	// UI, application and window management
	UI          *ui.UIManager
	Application *application.ApplicationManager
	Window      *window.WindowManager

	// Platform-specific automation modules
	Computer *computer.Computer
	Mobile   *mobile.Mobile

	// Agent for task execution
	Agent *agent.Agent

	// Context management
	Context *ContextManager

	// MCP tools available for this session
	McpTools []McpTool
}

// NewSession creates a new Session object.
func NewSession(agentBay *AgentBay, sessionID string) *Session {
	session := &Session{
		AgentBay:  agentBay,
		SessionID: sessionID,
	}

	// Initialize filesystem, command and code handlers
	session.FileSystem = filesystem.NewFileSystem(session)
	session.Command = command.NewCommand(session)
	session.Code = code.NewCode(session)
	session.Oss = oss.NewOss(session)

	// Initialize UI
	session.UI = ui.NewUI(session)

	// Initialize application and window managers
	session.Application = application.NewApplicationManager(session)
	session.Window = window.NewWindowManager(session)

	// Initialize platform-specific automation modules
	session.Computer = computer.NewComputer(session)
	session.Mobile = mobile.NewMobile(session)

	// Initialize Agent
	session.Agent = agent.NewAgent(session)

	// Initialize context manager
	session.Context = NewContextManager(session)
	return session
}

// GetAPIKey returns the API key for this session.
func (s *Session) GetAPIKey() string {
	return s.AgentBay.APIKey
}

// GetClient returns the HTTP client for this session.
func (s *Session) GetClient() *mcp.Client {
	return s.AgentBay.Client
}

// GetSessionId returns the session ID for this session.
func (s *Session) GetSessionId() string {
	return s.SessionID
}

// GetCommand returns the command handler for this session.
func (s *Session) GetCommand() *command.Command {
	return s.Command
}

// Delete deletes this session.
func (s *Session) Delete(syncContext ...bool) (*DeleteResult, error) {
	shouldSync := len(syncContext) > 0 && syncContext[0]

	// If syncContext is true, trigger file uploads first
	if shouldSync {
		fmt.Println("Triggering context synchronization before session deletion...")
		syncStartTime := time.Now()

		// Use the new sync method without callback (sync mode)
		syncResult, err := s.Context.SyncWithCallback("", "", "", nil, 150, 1500)
		if err != nil {
			syncDuration := time.Since(syncStartTime)
			fmt.Printf("Warning: Failed to trigger context sync after %v: %v\n", syncDuration, err)
			// Continue with deletion even if sync fails
		} else {
			syncDuration := time.Since(syncStartTime)
			if syncResult.Success {
				fmt.Printf("Context sync completed successfully in %v\n", syncDuration)
			} else {
				fmt.Printf("Context sync completed with failures after %v\n", syncDuration)
			}
		}
	}

	releaseSessionRequest := &mcp.ReleaseMcpSessionRequest{
		Authorization: tea.String("Bearer " + s.GetAPIKey()),
		SessionId:     tea.String(s.SessionID),
	}

	// Log API request
	fmt.Println("API Call: ReleaseMcpSession")
	fmt.Printf("Request: SessionId=%s\n", *releaseSessionRequest.SessionId)

	response, err := s.GetClient().ReleaseMcpSession(releaseSessionRequest)

	// Log API response
	if err != nil {
		fmt.Println("Error calling ReleaseMcpSession:", err)
		return nil, err
	}

	// Extract RequestID
	requestID := models.ExtractRequestID(response)

	if response != nil && response.Body != nil {
		fmt.Println("Response from ReleaseMcpSession:", response.Body)
	}

	// Check for API-level errors
	if response.Body != nil {
		if response.Body.Success != nil && !*response.Body.Success {
			errorMsg := "Failed to delete session"
			if response.Body.Code != nil && response.Body.Message != nil {
				errorMsg = fmt.Sprintf("[%s] %s", *response.Body.Code, *response.Body.Message)
			} else if response.Body.Code != nil {
				errorMsg = fmt.Sprintf("[%s] Failed to delete session", *response.Body.Code)
			}
			return &DeleteResult{
				ApiResponse: models.ApiResponse{
					RequestID: requestID,
				},
				Success:      false,
				ErrorMessage: errorMsg,
			}, nil
		}
	}

	s.AgentBay.Sessions.Delete(s.SessionID)

	return &DeleteResult{
		ApiResponse: models.ApiResponse{
			RequestID: requestID,
		},
		Success: true,
	}, nil
}

// ValidateLabels validates labels parameter for label operations.
// Returns error message if validation fails, empty string if validation passes
func (s *Session) ValidateLabels(labels map[string]string) string {
	// Check if labels is nil
	if labels == nil {
		return "Labels cannot be nil. Please provide a valid labels map."
	}

	// Check if labels map is empty
	if len(labels) == 0 {
		return "Labels cannot be empty. Please provide at least one label."
	}

	for key, value := range labels {
		// Check key validity
		if key == "" || len(strings.TrimSpace(key)) == 0 {
			return "Label keys cannot be empty. Please provide valid keys."
		}

		// Check value validity
		if value == "" || len(strings.TrimSpace(value)) == 0 {
			return "Label values cannot be empty. Please provide valid values."
		}
	}

	// Validation passed
	return ""
}

// SetLabels sets the labels for this session.
func (s *Session) SetLabels(labels map[string]string) (*LabelResult, error) {
	// Validate labels using the validation function
	if validationError := s.ValidateLabels(labels); validationError != "" {
		return &LabelResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			Labels: "",
		}, fmt.Errorf("%s", validationError)
	}

	// Convert labels to JSON string
	labelsJSON, err := json.Marshal(labels)
	if err != nil {
		return &LabelResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			Labels: "",
		}, fmt.Errorf("failed to marshal labels to JSON: %v", err)
	}

	setLabelRequest := &mcp.SetLabelRequest{
		Authorization: tea.String("Bearer " + s.GetAPIKey()),
		Labels:        tea.String(string(labelsJSON)),
		SessionId:     tea.String(s.SessionID),
	}

	// Log API request
	fmt.Println("API Call: SetLabel")
	fmt.Printf("Request: SessionId=%s, Labels=%s\n", *setLabelRequest.SessionId, *setLabelRequest.Labels)

	response, err := s.GetClient().SetLabel(setLabelRequest)

	// Log API response
	if err != nil {
		fmt.Println("Error calling SetLabel:", err)
		return nil, err
	}

	// Extract RequestID
	requestID := models.ExtractRequestID(response)

	if response != nil && response.Body != nil {
		fmt.Println("Response from SetLabel:", response.Body)
	}

	return &LabelResult{
		ApiResponse: models.ApiResponse{
			RequestID: requestID,
		},
		Labels: string(labelsJSON),
	}, nil
}

// GetLabels gets the labels for this session.
func (s *Session) GetLabels() (*LabelResult, error) {
	getLabelRequest := &mcp.GetLabelRequest{
		Authorization: tea.String("Bearer " + s.GetAPIKey()),
		SessionId:     tea.String(s.SessionID),
	}

	// Log API request
	fmt.Println("API Call: GetLabel")
	fmt.Printf("Request: SessionId=%s\n", *getLabelRequest.SessionId)

	response, err := s.GetClient().GetLabel(getLabelRequest)

	// Log API response
	if err != nil {
		fmt.Println("Error calling GetLabel:", err)
		return nil, err
	}

	// Extract RequestID
	requestID := models.ExtractRequestID(response)

	if response != nil && response.Body != nil {
		fmt.Println("Response from GetLabel:", response.Body)
	}

	var labels string
	if response != nil && response.Body != nil && response.Body.Data != nil && response.Body.Data.Labels != nil {
		labels = *response.Body.Data.Labels
	}

	return &LabelResult{
		ApiResponse: models.ApiResponse{
			RequestID: requestID,
		},
		Labels: labels,
	}, nil
}

// GetLink gets the link for this session.
func (s *Session) GetLink(protocolType *string, port *int32) (*LinkResult, error) {
	// Validate port range if port is provided
	if port != nil {
		if *port < 30100 || *port > 30199 {
			return nil, fmt.Errorf("invalid port value: %d. Port must be an integer in the range [30100, 30199]", *port)
		}
	}

	getLinkRequest := &mcp.GetLinkRequest{
		Authorization: tea.String("Bearer " + s.GetAPIKey()),
		SessionId:     tea.String(s.SessionID),
		ProtocolType:  protocolType,
		Port:          port,
	}

	// Log API request
	fmt.Println("API Call: GetLink")
	fmt.Printf("Request: SessionId=%s", *getLinkRequest.SessionId)
	if getLinkRequest.ProtocolType != nil {
		fmt.Printf(", ProtocolType=%s", *getLinkRequest.ProtocolType)
	}
	if getLinkRequest.Port != nil {
		fmt.Printf(", Port=%d", *getLinkRequest.Port)
	}
	fmt.Println()

	response, err := s.GetClient().GetLink(getLinkRequest)

	// Log API response
	if err != nil {
		fmt.Println("Error calling GetLink:", err)
		return nil, err
	}

	// Extract RequestID
	requestID := models.ExtractRequestID(response)

	if response != nil && response.Body != nil {
		fmt.Println("Response from GetLink:", response.Body)
	}

	var link string
	if response != nil && response.Body != nil && response.Body.Data != nil {
		data := response.Body.Data
		fmt.Printf("Data: %v\n", data)
		if data.Url != nil {
			link = *data.Url
		}
	}

	return &LinkResult{
		ApiResponse: models.ApiResponse{
			RequestID: requestID,
		},
		Link: link,
	}, nil
}

// Info gets information about this session.
func (s *Session) Info() (*InfoResult, error) {
	getMcpResourceRequest := &mcp.GetMcpResourceRequest{
		Authorization: tea.String("Bearer " + s.GetAPIKey()),
		SessionId:     tea.String(s.SessionID),
	}

	// Log API request
	fmt.Println("API Call: GetMcpResource")
	fmt.Printf("Request: SessionId=%s\n", *getMcpResourceRequest.SessionId)

	response, err := s.GetClient().GetMcpResource(getMcpResourceRequest)

	// Log API response
	if err != nil {
		fmt.Println("Error calling GetMcpResource:", err)
		return nil, err
	}

	// Extract RequestID
	requestID := models.ExtractRequestID(response)

	if response != nil && response.Body != nil {
		fmt.Println("Response from GetMcpResource:", response.Body)
	}

	if response != nil && response.Body != nil && response.Body.Data != nil {
		sessionInfo := &SessionInfo{
			SessionId:            "",
			ResourceUrl:          "",
			AppId:                "",
			AuthCode:             "",
			ConnectionProperties: "",
			ResourceId:           "",
			ResourceType:         "",
			Ticket:               "",
		}

		if response.Body.Data.SessionId != nil {
			sessionInfo.SessionId = *response.Body.Data.SessionId
		}

		if response.Body.Data.ResourceUrl != nil {
			sessionInfo.ResourceUrl = *response.Body.Data.ResourceUrl
		}

		// Transfer DesktopInfo fields to SessionInfo
		if response.Body.Data.DesktopInfo != nil {
			if response.Body.Data.DesktopInfo.AppId != nil {
				sessionInfo.AppId = *response.Body.Data.DesktopInfo.AppId
			}
			if response.Body.Data.DesktopInfo.AuthCode != nil {
				sessionInfo.AuthCode = *response.Body.Data.DesktopInfo.AuthCode
			}
			if response.Body.Data.DesktopInfo.ConnectionProperties != nil {
				sessionInfo.ConnectionProperties = *response.Body.Data.DesktopInfo.ConnectionProperties
			}
			if response.Body.Data.DesktopInfo.ResourceId != nil {
				sessionInfo.ResourceId = *response.Body.Data.DesktopInfo.ResourceId
			}
			if response.Body.Data.DesktopInfo.ResourceType != nil {
				sessionInfo.ResourceType = *response.Body.Data.DesktopInfo.ResourceType
			}
			if response.Body.Data.DesktopInfo.Ticket != nil {
				sessionInfo.Ticket = *response.Body.Data.DesktopInfo.Ticket
			}
		}

		return &InfoResult{
			ApiResponse: models.ApiResponse{
				RequestID: requestID,
			},
			Info: sessionInfo,
		}, nil
	}

	return nil, fmt.Errorf("failed to get session info: empty response data")
}

// ListMcpTools lists MCP tools available for this session.
// It uses the ImageId from the session creation, or "linux_latest" as default.
func (s *Session) ListMcpTools() (*McpToolsResult, error) {
	// Use session's ImageId, or default to "linux_latest" if empty
	imageId := s.ImageId
	if imageId == "" {
		imageId = "linux_latest"
	}

	listMcpToolsRequest := &mcp.ListMcpToolsRequest{
		Authorization: tea.String("Bearer " + s.GetAPIKey()),
		ImageId:       tea.String(imageId),
	}

	// Log API request
	fmt.Println("API Call: ListMcpTools")
	fmt.Printf("Request: ImageId=%s\n", *listMcpToolsRequest.ImageId)

	response, err := s.GetClient().ListMcpTools(listMcpToolsRequest)

	// Log API response
	if err != nil {
		fmt.Println("Error calling ListMcpTools:", err)
		return nil, err
	}

	// Extract RequestID
	requestID := models.ExtractRequestID(response)

	if response != nil && response.Body != nil {
		fmt.Println("Response from ListMcpTools:", response.Body)
	}

	// Parse the response data
	var tools []McpTool
	if response != nil && response.Body != nil && response.Body.Data != nil {
		// The Data field is a JSON string, so we need to unmarshal it
		var toolsData []map[string]interface{}
		if err := json.Unmarshal([]byte(*response.Body.Data), &toolsData); err != nil {
			fmt.Printf("Error unmarshaling tools data: %v\n", err)
			return &McpToolsResult{
				ApiResponse: models.ApiResponse{
					RequestID: requestID,
				},
				Tools: []McpTool{},
			}, nil
		}

		// Convert the parsed data to McpTool structs
		for _, toolData := range toolsData {
			tool := McpTool{}
			if name, ok := toolData["name"].(string); ok {
				tool.Name = name
			}
			if description, ok := toolData["description"].(string); ok {
				tool.Description = description
			}
			if inputSchema, ok := toolData["inputSchema"].(map[string]interface{}); ok {
				tool.InputSchema = inputSchema
			}
			if server, ok := toolData["server"].(string); ok {
				tool.Server = server
			}
			if toolIdentifier, ok := toolData["tool"].(string); ok {
				tool.Tool = toolIdentifier
			}
			tools = append(tools, tool)
		}
	}

	s.McpTools = tools // Update the session's McpTools field

	return &McpToolsResult{
		ApiResponse: models.ApiResponse{
			RequestID: requestID,
		},
		Tools: tools,
	}, nil
}

// IsVpc returns whether this session uses VPC resources
func (s *Session) IsVpc() bool {
	return s.IsVpcEnabled
}

// NetworkInterfaceIp returns the network interface IP for VPC sessions
func (s *Session) NetworkInterfaceIp() string {
	return s.NetworkInterfaceIP
}

// HttpPort returns the HTTP port for VPC sessions
func (s *Session) HttpPort() string {
	return s.HttpPortNumber
}

// GetToken returns the token for VPC sessions
func (s *Session) GetToken() string {
	return s.Token
}

// GetMcpTools returns the MCP tools available for this session
func (s *Session) GetMcpTools() []interface{} {
	result := make([]interface{}, len(s.McpTools))
	for i, tool := range s.McpTools {
		result[i] = &tool
	}
	return result
}

// FindServerForTool searches for the server that provides the given tool
func (s *Session) FindServerForTool(toolName string) string {
	for _, tool := range s.McpTools {
		if tool.Name == toolName {
			return tool.Server
		}
	}
	return ""
}

// CallMcpTool calls the MCP tool and handles both VPC and non-VPC scenarios
func (s *Session) CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error) {
	// Marshal arguments to JSON
	argsJSON, err := json.Marshal(args)
	if err != nil {
		return &models.McpToolResult{
			Success:      false,
			Data:         "",
			ErrorMessage: fmt.Sprintf("Failed to marshal args: %v", err),
			RequestID:    "",
		}, nil
	}

	// Check if this is a VPC session
	if s.IsVpc() {
		return s.callMcpToolVPC(toolName, string(argsJSON))
	}

	// Non-VPC mode: use traditional API call
	return s.callMcpToolAPI(toolName, string(argsJSON))
}

// callMcpToolVPC handles VPC-based MCP tool calls
func (s *Session) callMcpToolVPC(toolName, argsJSON string) (*models.McpToolResult, error) {
	// VPC mode: Use HTTP request to the VPC endpoint
	fmt.Println("API Call: CallMcpTool (VPC) -", toolName)
	fmt.Printf("Request: Args=%s\n", argsJSON)

	// Find server for this tool
	server := s.FindServerForTool(toolName)
	if server == "" {
		sanitizedErr := fmt.Sprintf("server not found for tool: %s", toolName)
		fmt.Println("Error calling VPC CallMcpTool -", toolName, ":", sanitizedErr)
		return &models.McpToolResult{
			Success:      false,
			Data:         "",
			ErrorMessage: sanitizedErr,
			RequestID:    "",
		}, nil
	}

	// Check VPC network configuration
	if s.NetworkInterfaceIp() == "" || s.HttpPort() == "" {
		sanitizedErr := fmt.Sprintf("VPC network configuration incomplete: networkInterfaceIp=%s, httpPort=%s", s.NetworkInterfaceIp(), s.HttpPort())
		fmt.Println("Error calling VPC CallMcpTool -", toolName, ":", sanitizedErr)
		return &models.McpToolResult{
			Success:      false,
			Data:         "",
			ErrorMessage: sanitizedErr,
			RequestID:    "",
		}, nil
	}

	// Construct VPC URL with query parameters
	baseURL := fmt.Sprintf("http://%s:%s/callTool", s.NetworkInterfaceIp(), s.HttpPort())
	params := url.Values{}
	params.Add("server", server)
	params.Add("tool", toolName)
	params.Add("args", argsJSON)
	params.Add("token", s.GetToken())
	// Add requestId for debugging purposes
	requestID := fmt.Sprintf("vpc-%d-%d", time.Now().UnixMilli(), rand.Intn(1000000000))
	params.Add("requestId", requestID)

	fullURL := fmt.Sprintf("%s?%s", baseURL, params.Encode())

	// Send HTTP request
	response, err := http.Get(fullURL)
	if err != nil {
		sanitizedErr := utils.SanitizeError(err)
		fmt.Println("Error calling VPC CallMcpTool -", toolName, ":", sanitizedErr)
		return &models.McpToolResult{
			Success:      false,
			Data:         "",
			ErrorMessage: fmt.Sprintf("VPC request failed: %v", err),
			RequestID:    "",
		}, nil
	}
	defer response.Body.Close()

	if response.StatusCode != http.StatusOK {
		sanitizedErr := fmt.Sprintf("VPC request failed with status: %d", response.StatusCode)
		fmt.Println("Error calling VPC CallMcpTool -", toolName, ":", sanitizedErr)
		return &models.McpToolResult{
			Success:      false,
			Data:         "",
			ErrorMessage: sanitizedErr,
			RequestID:    "",
		}, nil
	}

	// Parse response
	var responseData interface{}
	if err := json.NewDecoder(response.Body).Decode(&responseData); err != nil {
		sanitizedErr := utils.SanitizeError(err)
		fmt.Println("Error calling VPC CallMcpTool -", toolName, ":", sanitizedErr)
		return &models.McpToolResult{
			Success:      false,
			Data:         "",
			ErrorMessage: fmt.Sprintf("Failed to parse VPC response: %v", err),
			RequestID:    "",
		}, nil
	}

	fmt.Println("Response from VPC CallMcpTool -", toolName, ":", responseData)

	// Extract text content from the response
	textContent := s.extractTextContentFromResponse(responseData)

	return &models.McpToolResult{
		Success:      true,
		Data:         textContent,
		ErrorMessage: "",
		RequestID:    "", // VPC requests don't have traditional request IDs
	}, nil
}

// callMcpToolAPI handles traditional API-based MCP tool calls
func (s *Session) callMcpToolAPI(toolName, argsJSON string) (*models.McpToolResult, error) {
	// Helper function to convert string to *string
	stringPtr := func(s string) *string { return &s }

	callToolRequest := &mcp.CallMcpToolRequest{
		Authorization:  stringPtr(fmt.Sprintf("Bearer %s", s.GetAPIKey())),
		SessionId:      stringPtr(s.SessionID),
		Name:           stringPtr(toolName),
		Args:           stringPtr(argsJSON),
		ExternalUserId: stringPtr(""),
		ImageId:        stringPtr(""),
	}

	// Log API request
	fmt.Println("API Call: CallMcpTool -", toolName)
	fmt.Printf("Request: SessionId=%s, Args=%s\n", *callToolRequest.SessionId, *callToolRequest.Args)

	response, err := s.GetClient().CallMcpTool(callToolRequest)

	// Log API response
	if err != nil {
		sanitizedErr := utils.SanitizeError(err)
		fmt.Println("Error calling CallMcpTool -", toolName, ":", sanitizedErr)
		return &models.McpToolResult{
			Success:      false,
			Data:         "",
			ErrorMessage: fmt.Sprintf("API request failed: %v", err),
			RequestID:    "",
		}, nil
	}
	if response != nil && response.Body != nil {
		fmt.Println("Response from CallMcpTool -", toolName, ":", response.Body)
	}

	// Extract request ID
	requestID := ""
	if response.Body != nil && response.Body.GetRequestId() != nil {
		requestID = *response.Body.GetRequestId()
	}

	// Check for API-level errors
	if response.Body == nil || response.Body.GetData() == nil {
		return &models.McpToolResult{
			Success:      false,
			Data:         "",
			ErrorMessage: "Invalid response data format",
			RequestID:    requestID,
		}, nil
	}

	// Parse response data
	data := response.Body.GetData()

	// Check if there's an error in the response
	if dataMap, ok := data.(map[string]interface{}); ok {
		if isError, exists := dataMap["isError"]; exists && isError == true {
			// Extract error message from content
			errorMessage := "Unknown error"
			if content, contentExists := dataMap["content"]; contentExists {
				if contentArray, isArray := content.([]interface{}); isArray && len(contentArray) > 0 {
					if contentItem, isMap := contentArray[0].(map[string]interface{}); isMap {
						if text, textExists := contentItem["text"]; textExists {
							if textStr, isString := text.(string); isString {
								errorMessage = textStr
							}
						}
					}
				}
			}

			return &models.McpToolResult{
				Success:      false,
				Data:         "",
				ErrorMessage: errorMessage,
				RequestID:    requestID,
			}, nil
		}
	}

	// Extract text content from response
	textContent := s.extractTextContentFromResponse(data)

	return &models.McpToolResult{
		Success:      true,
		Data:         textContent,
		ErrorMessage: "",
		RequestID:    requestID,
	}, nil
}

// extractTextContentFromResponse extracts text content from various response formats
func (s *Session) extractTextContentFromResponse(data interface{}) string {
	if data == nil {
		return ""
	}

	// Try to extract text from different response formats
	if dataMap, ok := data.(map[string]interface{}); ok {
		// Check for content array first
		if content, exists := dataMap["content"]; exists {
			if contentArray, isArray := content.([]interface{}); isArray && len(contentArray) > 0 {
				if contentItem, isMap := contentArray[0].(map[string]interface{}); isMap {
					if text, textExists := contentItem["text"]; textExists {
						if textStr, isString := text.(string); isString {
							return textStr
						}
					}
				}
			}
		}

		// Check for direct result field
		if result, exists := dataMap["result"]; exists {
			if resultMap, isMap := result.(map[string]interface{}); isMap {
				if content, contentExists := resultMap["content"]; contentExists {
					if contentArray, isArray := content.([]interface{}); isArray && len(contentArray) > 0 {
						if contentItem, isMap := contentArray[0].(map[string]interface{}); isMap {
							if text, textExists := contentItem["text"]; textExists {
								if textStr, isString := text.(string); isString {
									return textStr
								}
							}
						}
					}
				}
			}
		}
	}

	// If no text content found, return JSON representation
	if dataBytes, err := json.Marshal(data); err == nil {
		return string(dataBytes)
	}

	return ""
}
