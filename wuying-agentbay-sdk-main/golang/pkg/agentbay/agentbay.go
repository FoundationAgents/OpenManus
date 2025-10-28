package agentbay

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"sync"
	"time"

	openapiutil "github.com/alibabacloud-go/darabonba-openapi/v2/utils"
	"github.com/alibabacloud-go/tea/tea"
	mcp "github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

// Option is a function that sets optional parameters for AgentBay client.
type Option func(*AgentBayConfig)

// AgentBayConfig holds optional configuration for the AgentBay client.
type AgentBayConfig struct {
	cfg     *Config
	envFile string
}

// WithConfig returns an Option that sets the configuration for the AgentBay client.
func WithConfig(cfg *Config) Option {
	return func(c *AgentBayConfig) {
		c.cfg = cfg
	}
}

// WithEnvFile returns an Option that sets a custom .env file path for the AgentBay client.
func WithEnvFile(envFile string) Option {
	return func(c *AgentBayConfig) {
		c.envFile = envFile
	}
}

// AgentBay represents the main client for interacting with the AgentBay cloud runtime environment.
type AgentBay struct {
	APIKey   string
	Client   *mcp.Client
	Sessions sync.Map
	Context  *ContextService
}

// NewAgentBay creates a new AgentBay client.
// If apiKey is empty, it will look for the AGENTBAY_API_KEY environment variable.
func NewAgentBay(apiKey string, opts ...Option) (*AgentBay, error) {
	if apiKey == "" {
		apiKey = os.Getenv("AGENTBAY_API_KEY")
		if apiKey == "" {
			return nil, fmt.Errorf("API key is required. Provide it as a parameter or set the AGENTBAY_API_KEY environment variable")
		}
	}

	// Apply options safely
	config_option := &AgentBayConfig{}
	if opts != nil {
		for _, opt := range opts {
			if opt != nil {
				opt(config_option)
			}
		}
	}

	// Load configuration using LoadConfig function
	// This will load from environment variables, .env file (searched upward), or use defaults
	config := LoadConfig(config_option.cfg, config_option.envFile)

	// Create API client
	apiConfig := &openapiutil.Config{
		RegionId:       tea.String(""),
		Endpoint:       tea.String(config.Endpoint),
		ReadTimeout:    tea.Int(config.TimeoutMs),
		ConnectTimeout: tea.Int(config.TimeoutMs),
	}

	client, err := mcp.NewClient(apiConfig)
	if err != nil {
		return nil, fmt.Errorf("create openapi client fails: %v", err)
	}

	// Create AgentBay instance
	agentBay := &AgentBay{
		APIKey:  apiKey,
		Client:  client,
		Context: nil, // Will be initialized after creation
	}

	// Initialize context service
	agentBay.Context = &ContextService{AgentBay: agentBay}

	return agentBay, nil
}

// NewAgentBayWithDefaults creates a new AgentBay client using default configuration.
// This is a convenience function that allows calling NewAgentBay without a config parameter.
func NewAgentBayWithDefaults(apiKey string) (*AgentBay, error) {
	return NewAgentBay(apiKey, nil)
}

// Create creates a new session in the AgentBay cloud environment.
// If params is nil, default parameters will be used.
func (a *AgentBay) Create(params *CreateSessionParams) (*SessionResult, error) {
	if params == nil {
		params = NewCreateSessionParams()
	}

	createSessionRequest := &mcp.CreateMcpSessionRequest{
		Authorization: tea.String("Bearer " + a.APIKey),
	}

	// Add image_id if provided
	if params.ImageId != "" {
		createSessionRequest.ImageId = tea.String(params.ImageId)
	}

	// Add VPC resource if specified
	createSessionRequest.VpcResource = tea.Bool(params.IsVpc)

	// Add PolicyId if provided
	if params.PolicyId != "" {
		createSessionRequest.McpPolicyId = tea.String(params.PolicyId)
	}

	// Add labels if provided
	if len(params.Labels) > 0 {
		labelsJSON, err := params.GetLabelsJSON()
		if err != nil {
			return nil, fmt.Errorf("failed to marshal labels to JSON: %v", err)
		}
		createSessionRequest.Labels = tea.String(labelsJSON)
	}

	// Add extra configs if provided
	if params.ExtraConfigs != nil {
		extraConfigsJSON, err := params.GetExtraConfigsJSON()
		if err != nil {
			return nil, fmt.Errorf("failed to marshal extra configs to JSON: %v", err)
		}
		if extraConfigsJSON != "" {
			createSessionRequest.ExtraConfigs = tea.String(extraConfigsJSON)
		}
	}

	// Flag to indicate if we need to wait for context synchronization
	needsContextSync := false

	// Add context sync configurations if provided
	var persistenceDataList []*mcp.CreateMcpSessionRequestPersistenceDataList

	if len(params.ContextSync) > 0 {
		for _, contextSync := range params.ContextSync {
			persistenceItem := &mcp.CreateMcpSessionRequestPersistenceDataList{
				ContextId: tea.String(contextSync.ContextID),
				Path:      tea.String(contextSync.Path),
			}

			// Convert policy to JSON string if provided
			if contextSync.Policy != nil {
				policyJSON, err := json.Marshal(contextSync.Policy)
				if err != nil {
					return nil, fmt.Errorf("failed to marshal context sync policy to JSON: %v", err)
				}
				persistenceItem.Policy = tea.String(string(policyJSON))
			}

			persistenceDataList = append(persistenceDataList, persistenceItem)
		}
	}

	if len(persistenceDataList) > 0 {
		createSessionRequest.PersistenceDataList = persistenceDataList
		needsContextSync = true
	}

	// Log API request
	fmt.Println("API Call: CreateMcpSession")
	fmt.Printf("Request: ")
	if createSessionRequest.ContextId != nil {
		fmt.Printf("ContextId=%s, ", *createSessionRequest.ContextId)
	}
	if createSessionRequest.ImageId != nil {
		fmt.Printf("ImageId=%s, ", *createSessionRequest.ImageId)
	}
	if createSessionRequest.McpPolicyId != nil {
		fmt.Printf("PolicyId=%s, ", *createSessionRequest.McpPolicyId)
	}
	if createSessionRequest.VpcResource != nil {
		fmt.Printf("VpcResource=%t, ", *createSessionRequest.VpcResource)
	}
	if createSessionRequest.Labels != nil {
		fmt.Printf("Labels=%s, ", *createSessionRequest.Labels)
	}
	if len(createSessionRequest.PersistenceDataList) > 0 {
		fmt.Printf("PersistenceDataList=%d items, ", len(createSessionRequest.PersistenceDataList))
		for i, pd := range createSessionRequest.PersistenceDataList {
			fmt.Printf("Item%d[ContextId=%s, Path=%s", i, tea.StringValue(pd.ContextId), tea.StringValue(pd.Path))
			if pd.Policy != nil {
				fmt.Printf(", Policy=%s", tea.StringValue(pd.Policy))
			}
			fmt.Printf("], ")
		}
	}
	fmt.Println()

	response, err := a.Client.CreateMcpSession(createSessionRequest)

	// Log API response
	if err != nil {
		fmt.Println("Error calling CreateMcpSession:", err)
		return nil, err
	}

	// Extract RequestID
	requestID := models.ExtractRequestID(response)

	// Log only the response body
	if response != nil && response.Body != nil {
		// Convert response body to JSON for proper printing without escaped characters
		responseJSON, _ := json.MarshalIndent(response.Body, "", "  ")
		// Replace \u0026 with & for better readability
		jsonStr := strings.ReplaceAll(string(responseJSON), "\\u0026", "&")
		fmt.Println("Response from CreateMcpSession:")
		fmt.Println(jsonStr)
	}

	// Check if the session creation was successful
	if response == nil || response.Body == nil || response.Body.Data == nil {
		return nil, fmt.Errorf("invalid response from CreateMcpSession")
	}

	// Check if there's an error message in the response
	if response.Body.Data.Success != nil && !*response.Body.Data.Success {
		errMsg := "session creation failed"
		if response.Body.Data.ErrMsg != nil {
			errMsg = *response.Body.Data.ErrMsg
		}
		return nil, fmt.Errorf("%s", errMsg)
	}

	// Check if SessionId is present
	if response.Body.Data.SessionId == nil {
		return nil, fmt.Errorf("no session ID returned from CreateMcpSession")
	}

	// ResourceUrl is optional in CreateMcpSession response

	// Create a new session object
	session := NewSession(a, *response.Body.Data.SessionId)
	session.ImageId = params.ImageId // Store the ImageId used for this session

	// Set VPC-related information from response
	session.IsVpcEnabled = params.IsVpc
	if response.Body.Data.NetworkInterfaceIp != nil {
		session.NetworkInterfaceIP = *response.Body.Data.NetworkInterfaceIp
	}
	if response.Body.Data.HttpPort != nil {
		session.HttpPortNumber = *response.Body.Data.HttpPort
	}
	if response.Body.Data.Token != nil {
		session.Token = *response.Body.Data.Token
	}

	// Set ResourceUrl
	if response.Body.Data.ResourceUrl != nil {
		session.ResourceUrl = *response.Body.Data.ResourceUrl
	}

	a.Sessions.Store(session.SessionID, *session)

	// Apply mobile configuration if provided
	if params.ExtraConfigs != nil && params.ExtraConfigs.Mobile != nil {
		fmt.Println("Applying mobile configuration...")
		if err := session.Mobile.Configure(params.ExtraConfigs.Mobile); err != nil {
			fmt.Printf("Warning: Failed to apply mobile configuration: %v\n", err)
			// Continue with session creation even if mobile config fails
		} else {
			fmt.Println("Mobile configuration applied successfully")
		}
	}

	// For VPC sessions, automatically fetch MCP tools information
	if params.IsVpc {
		fmt.Println("VPC session detected, automatically fetching MCP tools...")
		toolsResult, err := session.ListMcpTools()
		if err != nil {
			fmt.Printf("Warning: Failed to fetch MCP tools for VPC session: %v\n", err)
			// Continue with session creation even if tools fetch fails
		} else {
			fmt.Printf("Successfully fetched %d MCP tools for VPC session (RequestID: %s)\n",
				len(toolsResult.Tools), toolsResult.RequestID)
		}
	}

	// If we have persistence data, wait for context synchronization
	if needsContextSync {
		fmt.Println("Waiting for context synchronization to complete...")

		// Wait for context synchronization to complete
		const maxRetries = 150                        // Maximum number of retries
		const retryInterval = 1500 * time.Millisecond // 1.5 seconds between retries

		for retry := 0; retry < maxRetries; retry++ {
			// Get context status data
			infoResult, err := session.Context.Info()
			if err != nil {
				fmt.Printf("Error getting context info on attempt %d: %v\n", retry+1, err)
				time.Sleep(retryInterval)
				continue
			}

			// Check if all context items have status "Success" or "Failed"
			allCompleted := true
			hasFailure := false

			for _, item := range infoResult.ContextStatusData {
				fmt.Printf("Context %s status: %s, path: %s\n", item.ContextId, item.Status, item.Path)

				if item.Status != "Success" && item.Status != "Failed" {
					allCompleted = false
					break
				}

				if item.Status == "Failed" {
					hasFailure = true
					fmt.Printf("Context synchronization failed for %s: %s\n", item.ContextId, item.ErrorMessage)
				}
			}

			if allCompleted || len(infoResult.ContextStatusData) == 0 {
				if hasFailure {
					fmt.Println("Context synchronization completed with failures")
				} else {
					fmt.Println("Context synchronization completed successfully")
				}
				break
			}

			fmt.Printf("Waiting for context synchronization, attempt %d/%d\n", retry+1, maxRetries)
			time.Sleep(retryInterval)
		}
	}

	// Return result with RequestID
	return &SessionResult{
		ApiResponse: models.ApiResponse{
			RequestID: requestID,
		},
		Session: session,
	}, nil
}

// ListSessionParams contains parameters for listing sessions
type ListSessionParams struct {
	MaxResults int32             // Number of results per page
	NextToken  string            // Token for the next page
	Labels     map[string]string // Labels to filter by
}

// NewListSessionParams creates a new ListSessionParams with default values
func NewListSessionParams() *ListSessionParams {
	return &ListSessionParams{
		MaxResults: 10, // Default page size
		NextToken:  "",
		Labels:     make(map[string]string),
	}
}

// ListByLabels lists sessions filtered by the provided labels with pagination support.
// It returns sessions that match all the specified labels.
//
// Deprecated: This method is deprecated and will be removed in a future version. Use List() instead.
func (a *AgentBay) ListByLabels(params *ListSessionParams) (*SessionListResult, error) {
	if params == nil {
		params = NewListSessionParams()
	}

	// Convert labels to JSON
	labelsJSON, err := json.Marshal(params.Labels)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal labels to JSON: %v", err)
	}

	listSessionRequest := &mcp.ListSessionRequest{
		Authorization: tea.String("Bearer " + a.APIKey),
		Labels:        tea.String(string(labelsJSON)),
		MaxResults:    tea.Int32(params.MaxResults),
	}

	// Add NextToken if provided
	if params.NextToken != "" {
		listSessionRequest.NextToken = tea.String(params.NextToken)
	}

	// Log API request
	fmt.Println("API Call: ListSession")
	fmt.Printf("Request: Labels=%s, MaxResults=%d", *listSessionRequest.Labels, *listSessionRequest.MaxResults)
	if listSessionRequest.NextToken != nil {
		fmt.Printf(", NextToken=%s", *listSessionRequest.NextToken)
	}
	fmt.Println()

	response, err := a.Client.ListSession(listSessionRequest)

	// Log API response
	if err != nil {
		fmt.Println("Error calling ListSession:", err)
		return nil, err
	}

	// Extract RequestID
	requestID := models.ExtractRequestID(response)

	if response != nil && response.Body != nil {
		fmt.Println("Response from ListSession:", response.Body)
	}

	var sessions []Session
	var sessionIds []string
	var nextToken string
	var maxResults int32 = params.MaxResults // Use the requested MaxResults
	var totalCount int32

	if response.Body != nil {
		// Extract pagination information
		if response.Body.NextToken != nil {
			nextToken = *response.Body.NextToken
		}
		// Use API response MaxResults if present, otherwise use requested value
		if response.Body.MaxResults != nil {
			maxResults = *response.Body.MaxResults
		}
		if response.Body.TotalCount != nil {
			totalCount = *response.Body.TotalCount
		}

		// Extract session data
		if response.Body.Data != nil {
			for _, sessionData := range response.Body.Data {
				if sessionData.SessionId != nil {
					sessionIds = append(sessionIds, *sessionData.SessionId)
					session := NewSession(a, *sessionData.SessionId)
					// Use default ImageId for sessions retrieved from API
					session.ImageId = "linux_latest"
					sessions = append(sessions, *session)
					// Also store in the local cache
					a.Sessions.Store(*sessionData.SessionId, *session)
				}
			}
		}
	}

	return &SessionListResult{
		ApiResponse: models.ApiResponse{
			RequestID: requestID,
		},
		SessionIds: sessionIds,
		NextToken:  nextToken,
		MaxResults: maxResults,
		TotalCount: totalCount,
	}, nil
}

// List returns paginated list of session IDs filtered by labels.
//
// Parameters:
//   - labels: Optional labels to filter sessions (can be nil for no filtering)
//   - page: Optional page number for pagination (starting from 1, nil or 0 for first page)
//   - limit: Optional maximum number of items per page (nil or 0 uses default of 10)
//
// Returns:
//   - *SessionListResult: Paginated list of session IDs that match the labels
//   - error: An error if the operation fails
//
// Example:
//
//	agentBay, _ := agentbay.NewAgentBay("your_api_key")
//
//	// List all sessions
//	result, err := agentBay.List(nil, nil, nil)
//
//	// List sessions with specific labels
//	result, err := agentBay.List(map[string]string{"project": "demo"}, nil, nil)
//
//	// List sessions with pagination
//	page := 2
//	limit := int32(10)
//	result, err := agentBay.List(map[string]string{"my-label": "my-value"}, &page, &limit)
//
//	if err == nil {
//	    for _, sessionId := range result.SessionIds {
//	        fmt.Printf("Session ID: %s\n", sessionId)
//	    }
//	    fmt.Printf("Total count: %d\n", result.TotalCount)
//	    fmt.Printf("Request ID: %s\n", result.RequestID)
//	}
func (a *AgentBay) List(labels map[string]string, page *int, limit *int32) (*SessionListResult, error) {
	// Set default values
	if labels == nil {
		labels = make(map[string]string)
	}
	actualLimit := int32(10)
	if limit != nil && *limit > 0 {
		actualLimit = *limit
	}

	// Validate page number
	if page != nil && *page < 1 {
		return &SessionListResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			SessionIds: []string{},
			NextToken:  "",
			MaxResults: actualLimit,
			TotalCount: 0,
		}, fmt.Errorf("cannot reach page %d: Page number must be >= 1", *page)
	}

	// Convert labels to JSON
	labelsJSON, err := json.Marshal(labels)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal labels to JSON: %v", err)
	}

	// Calculate next_token based on page number
	nextToken := ""
	if page != nil && *page > 1 {
		// We need to fetch pages 1 through page-1 to get the next_token
		currentPage := 1
		for currentPage < *page {
			// Make API call to get next_token
			listSessionRequest := &mcp.ListSessionRequest{
				Authorization: tea.String("Bearer " + a.APIKey),
				Labels:        tea.String(string(labelsJSON)),
				MaxResults:    tea.Int32(actualLimit),
			}
			if nextToken != "" {
				listSessionRequest.NextToken = tea.String(nextToken)
			}

			response, err := a.Client.ListSession(listSessionRequest)
			if err != nil {
				return &SessionListResult{
					ApiResponse: models.ApiResponse{
						RequestID: models.ExtractRequestID(response),
					},
					SessionIds: []string{},
					NextToken:  "",
					MaxResults: actualLimit,
					TotalCount: 0,
				}, fmt.Errorf("cannot reach page %d: %v", *page, err)
			}

			if response.Body == nil || response.Body.Success == nil || !*response.Body.Success {
				errorMsg := "Unknown error"
				if response.Body != nil && response.Body.Message != nil {
					errorMsg = *response.Body.Message
				} else if response.Body != nil && response.Body.Code != nil {
					errorMsg = *response.Body.Code
				}
				return &SessionListResult{
					ApiResponse: models.ApiResponse{
						RequestID: models.ExtractRequestID(response),
					},
					SessionIds: []string{},
					NextToken:  "",
					MaxResults: actualLimit,
					TotalCount: 0,
				}, fmt.Errorf("cannot reach page %d: %s", *page, errorMsg)
			}

			if response.Body.NextToken == nil || *response.Body.NextToken == "" {
				// No more pages available
				totalCount := int32(0)
				if response.Body.TotalCount != nil {
					totalCount = *response.Body.TotalCount
				}
				return &SessionListResult{
					ApiResponse: models.ApiResponse{
						RequestID: models.ExtractRequestID(response),
					},
					SessionIds: []string{},
					NextToken:  "",
					MaxResults: actualLimit,
					TotalCount: totalCount,
				}, fmt.Errorf("cannot reach page %d: No more pages available", *page)
			}
			nextToken = *response.Body.NextToken
			currentPage++
		}
	}

	// Make the actual request for the desired page
	listSessionRequest := &mcp.ListSessionRequest{
		Authorization: tea.String("Bearer " + a.APIKey),
		Labels:        tea.String(string(labelsJSON)),
		MaxResults:    tea.Int32(actualLimit),
	}
	if nextToken != "" {
		listSessionRequest.NextToken = tea.String(nextToken)
	}

	// Log API request
	fmt.Println("API Call: ListSession")
	fmt.Printf("Request: Labels=%s, MaxResults=%d", *listSessionRequest.Labels, *listSessionRequest.MaxResults)
	if listSessionRequest.NextToken != nil {
		fmt.Printf(", NextToken=%s", *listSessionRequest.NextToken)
	}
	fmt.Println()

	response, err := a.Client.ListSession(listSessionRequest)

	// Log API response
	if err != nil {
		fmt.Println("Error calling ListSession:", err)
		return nil, err
	}

	// Extract RequestID
	requestID := models.ExtractRequestID(response)

	if response != nil && response.Body != nil {
		fmt.Println("Response from ListSession:", response.Body)
	}

	// Check for errors in the response
	if response.Body == nil || response.Body.Success == nil || !*response.Body.Success {
		errorMsg := "Unknown error"
		if response.Body != nil && response.Body.Message != nil {
			errorMsg = *response.Body.Message
		} else if response.Body != nil && response.Body.Code != nil {
			errorMsg = *response.Body.Code
		}
		return &SessionListResult{
			ApiResponse: models.ApiResponse{
				RequestID: requestID,
			},
			SessionIds: []string{},
			NextToken:  "",
			MaxResults: actualLimit,
			TotalCount: 0,
		}, fmt.Errorf("failed to list sessions: %s", errorMsg)
	}

	var sessionIds []string
	var nextTokenResult string
	var maxResults int32 = actualLimit
	var totalCount int32

	if response.Body != nil {
		// Extract pagination information
		if response.Body.NextToken != nil {
			nextTokenResult = *response.Body.NextToken
		}
		if response.Body.MaxResults != nil {
			maxResults = *response.Body.MaxResults
		}
		if response.Body.TotalCount != nil {
			totalCount = *response.Body.TotalCount
		}

		// Extract session data
		if response.Body.Data != nil {
			for _, sessionData := range response.Body.Data {
				if sessionData.SessionId != nil {
					sessionIds = append(sessionIds, *sessionData.SessionId)
				}
			}
		}
	}

	return &SessionListResult{
		ApiResponse: models.ApiResponse{
			RequestID: requestID,
		},
		SessionIds: sessionIds,
		NextToken:  nextTokenResult,
		MaxResults: maxResults,
		TotalCount: totalCount,
	}, nil
}

// Delete deletes a session by ID.
func (a *AgentBay) Delete(session *Session, syncContext ...bool) (*DeleteResult, error) {
	result, err := session.Delete(syncContext...)
	if err == nil {
		a.Sessions.Delete(session.SessionID)
	}
	return result, err
}

// GetSessionResult represents the result of GetSession operation
type GetSessionResult struct {
	models.ApiResponse
	HttpStatusCode int32
	Code           string
	Success        bool
	Data           *GetSessionData
	ErrorMessage   string
}

// GetSessionData represents the data returned by GetSession API
type GetSessionData struct {
	AppInstanceID      string
	ResourceID         string
	SessionID          string
	Success            bool
	HttpPort           string
	NetworkInterfaceIP string
	Token              string
	VpcResource        bool
	ResourceUrl        string
}

// GetSession retrieves session information by session ID
func (a *AgentBay) GetSession(sessionID string) (*GetSessionResult, error) {
	getSessionRequest := &mcp.GetSessionRequest{
		Authorization: tea.String("Bearer " + a.APIKey),
		SessionId:     tea.String(sessionID),
	}

	// Log API request
	fmt.Println("API Call: GetSession")
	fmt.Printf("Request: SessionId=%s\n", *getSessionRequest.SessionId)

	response, err := a.Client.GetSession(getSessionRequest)

	// Log API response
	if err != nil {
		fmt.Println("Error calling GetSession:", err)
		return nil, err
	}

	// Extract RequestID
	requestID := models.ExtractRequestID(response)

	if response != nil && response.Body != nil {
		fmt.Println("Response from GetSession:", response.Body)
	}

	result := &GetSessionResult{
		ApiResponse: models.ApiResponse{
			RequestID: requestID,
		},
	}

	if response != nil && response.Body != nil {
		if response.Body.HttpStatusCode != nil {
			result.HttpStatusCode = *response.Body.HttpStatusCode
		}
		if response.Body.Code != nil {
			result.Code = *response.Body.Code
		}
		if response.Body.Success != nil {
			result.Success = *response.Body.Success
		}

		// Check for API-level errors
		if !result.Success && response.Body.Code != nil {
			code := tea.StringValue(response.Body.Code)
			message := tea.StringValue(response.Body.Message)
			if message == "" {
				message = "Unknown error"
			}
			result.ErrorMessage = fmt.Sprintf("[%s] %s", code, message)
			return result, nil
		}

		if response.Body.Data != nil {
			data := &GetSessionData{}
			if response.Body.Data.AppInstanceId != nil {
				data.AppInstanceID = *response.Body.Data.AppInstanceId
			}
			if response.Body.Data.ResourceId != nil {
				data.ResourceID = *response.Body.Data.ResourceId
			}
			if response.Body.Data.SessionId != nil {
				data.SessionID = *response.Body.Data.SessionId
			}
			if response.Body.Data.Success != nil {
				data.Success = *response.Body.Data.Success
			}
			if response.Body.Data.HttpPort != nil {
				data.HttpPort = *response.Body.Data.HttpPort
			}
			if response.Body.Data.NetworkInterfaceIp != nil {
				data.NetworkInterfaceIP = *response.Body.Data.NetworkInterfaceIp
			}
			if response.Body.Data.Token != nil {
				data.Token = *response.Body.Data.Token
			}
			if response.Body.Data.VpcResource != nil {
				data.VpcResource = *response.Body.Data.VpcResource
			}
			if response.Body.Data.ResourceUrl != nil {
				data.ResourceUrl = *response.Body.Data.ResourceUrl
			}
			result.Data = data
		}

		result.ErrorMessage = ""
	}

	return result, nil
}

// Get retrieves a session by its ID.
// This method calls the GetSession API and returns a SessionResult containing the Session object and request ID.
//
// Parameters:
//   - sessionID: The ID of the session to retrieve
//
// Returns:
//   - *SessionResult: Result containing the Session instance, request ID, and success status
//   - error: An error if the operation fails
//
// Example:
//
//	result, err := agentBay.Get("my-session-id")
//	if err != nil {
//	    log.Fatal(err)
//	}
//	if result.Success {
//	    fmt.Printf("Session ID: %s\n", result.Session.SessionID)
//	    fmt.Printf("Request ID: %s\n", result.RequestID)
//	}
func (a *AgentBay) Get(sessionID string) (*SessionResult, error) {
	if sessionID == "" {
		return &SessionResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			Success:      false,
			ErrorMessage: "session_id is required",
		}, nil
	}

	// Call GetSession API
	getResult, err := a.GetSession(sessionID)
	if err != nil {
		return &SessionResult{
			ApiResponse: models.ApiResponse{
				RequestID: "",
			},
			Success:      false,
			ErrorMessage: fmt.Sprintf("failed to get session %s: %v", sessionID, err),
		}, nil
	}

	// Check if the API call was successful
	if !getResult.Success {
		errorMsg := "unknown error"
		if getResult.Data != nil && !getResult.Data.Success {
			errorMsg = "Session not found"
		}
		return &SessionResult{
			ApiResponse: models.ApiResponse{
				RequestID: getResult.RequestID,
			},
			Success:      false,
			ErrorMessage: fmt.Sprintf("failed to get session %s: %s", sessionID, errorMsg),
		}, nil
	}

	// Create the Session object
	session := NewSession(a, sessionID)

	// Set VPC-related information and ResourceUrl from GetSession response
	if getResult.Data != nil {
		session.IsVpcEnabled = getResult.Data.VpcResource
		session.NetworkInterfaceIP = getResult.Data.NetworkInterfaceIP
		session.HttpPortNumber = getResult.Data.HttpPort
		session.Token = getResult.Data.Token
		session.ResourceUrl = getResult.Data.ResourceUrl
	}

	// Store the session in the local cache
	a.Sessions.Store(sessionID, *session)

	return &SessionResult{
		ApiResponse: models.ApiResponse{
			RequestID: getResult.RequestID,
		},
		Success: true,
		Session: session,
	}, nil
}
