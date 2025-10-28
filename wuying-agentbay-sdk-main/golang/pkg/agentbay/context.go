package agentbay

import (
	"fmt"

	"github.com/alibabacloud-go/tea/tea"
	mcp "github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

// Context represents a persistent storage context in the AgentBay cloud environment.
type Context struct {
	// ID is the unique identifier of the context.
	ID string

	// Name is the name of the context.
	Name string

	// State is deprecated and will be removed in a future version.
	// Deprecated: This field is no longer used.
	State string

	// CreatedAt is the date and time when the Context was created.
	CreatedAt string

	// LastUsedAt is the date and time when the Context was last used.
	LastUsedAt string

	// OSType is deprecated and will be removed in a future version.
	// Deprecated: This field is no longer used.
	OSType string
}

// ContextResult wraps context operation result and RequestID
type ContextResult struct {
	models.ApiResponse
	Success      bool
	ContextID    string
	Context      *Context
	ErrorMessage string
}

// ContextListResult wraps context list and RequestID
type ContextListResult struct {
	models.ApiResponse
	Success      bool
	Contexts     []*Context
	NextToken    string
	MaxResults   int32
	TotalCount   int32
	ErrorMessage string
}

// ContextCreateResult wraps context creation result and RequestID
type ContextCreateResult struct {
	models.ApiResponse
	ContextID string
}

// ContextModifyResult wraps context modification result and RequestID
type ContextModifyResult struct {
	models.ApiResponse
	Success      bool
	ErrorMessage string
}

// ContextDeleteResult wraps context deletion result and RequestID
type ContextDeleteResult struct {
	models.ApiResponse
	Success      bool
	ErrorMessage string
}

// ContextService provides methods to manage persistent contexts in the AgentBay cloud environment.
type ContextService struct {
	// AgentBay is the AgentBay instance.
	AgentBay *AgentBay
}

// ContextListParams contains parameters for listing contexts
type ContextListParams struct {
	MaxResults int32  // Number of results per page
	NextToken  string // Token for the next page
}

// NewContextListParams creates a new ContextListParams with default values
func NewContextListParams() *ContextListParams {
	return &ContextListParams{
		MaxResults: 10, // Default page size
		NextToken:  "",
	}
}

// List lists all available contexts with pagination support.
func (cs *ContextService) List(params *ContextListParams) (*ContextListResult, error) {
	if params == nil {
		params = NewContextListParams()
	}

	request := &mcp.ListContextsRequest{
		Authorization: tea.String("Bearer " + cs.AgentBay.APIKey),
		MaxResults:    tea.Int32(params.MaxResults),
	}

	// Add NextToken if provided
	if params.NextToken != "" {
		request.NextToken = tea.String(params.NextToken)
	}

	// Log API request
	fmt.Println("API Call: ListContexts")
	fmt.Printf("Request: MaxResults=%d", *request.MaxResults)
	if request.NextToken != nil {
		fmt.Printf(", NextToken=%s", *request.NextToken)
	}
	fmt.Println()

	response, err := cs.AgentBay.Client.ListContexts(request)

	// Extract RequestID
	requestID := models.ExtractRequestID(response)

	// Log API response
	if err != nil {
		fmt.Println("Error calling ListContexts:", err)
		return &ContextListResult{
			ApiResponse: models.ApiResponse{
				RequestID: requestID,
			},
			Success:      false,
			Contexts:     []*Context{},
			ErrorMessage: fmt.Sprintf("Failed to list contexts: %v", err),
		}, nil
	}

	if response != nil && response.Body != nil {
		fmt.Println("Response from ListContexts:", response.Body)
	}

	// Check for API-level errors
	if response.Body != nil {
		if response.Body.Success != nil && !*response.Body.Success && response.Body.Code != nil {
			errorMsg := "Unknown error"
			if response.Body.Message != nil {
				errorMsg = fmt.Sprintf("[%s] %s", *response.Body.Code, *response.Body.Message)
			} else {
				errorMsg = fmt.Sprintf("[%s] Unknown error", *response.Body.Code)
			}
			return &ContextListResult{
				ApiResponse: models.ApiResponse{
					RequestID: requestID,
				},
				Success:      false,
				Contexts:     []*Context{},
				ErrorMessage: errorMsg,
			}, nil
		}
	}

	var contexts []*Context
	var nextToken string
	var maxResults int32
	var totalCount int32

	if response.Body != nil {
		// Extract pagination information
		if response.Body.NextToken != nil {
			nextToken = *response.Body.NextToken
		}
		// Set maxResults and totalCount from params or response
		maxResults = params.MaxResults
		if response.Body.TotalCount != nil {
			totalCount = *response.Body.TotalCount
		}

		// Extract context data
		if response.Body.Data != nil {
			for _, contextData := range response.Body.Data {
				context := &Context{
					ID:         tea.StringValue(contextData.Id),
					Name:       tea.StringValue(contextData.Name),
					State:      tea.StringValue(contextData.State),
					CreatedAt:  tea.StringValue(contextData.CreateTime),
					LastUsedAt: tea.StringValue(contextData.LastUsedTime),
					OSType:     tea.StringValue(contextData.OsType),
				}
				contexts = append(contexts, context)
			}
		}
	}

	return &ContextListResult{
		ApiResponse: models.ApiResponse{
			RequestID: requestID,
		},
		Success:      true,
		Contexts:     contexts,
		NextToken:    nextToken,
		MaxResults:   maxResults,
		TotalCount:   totalCount,
		ErrorMessage: "",
	}, nil
}

// Get gets a context by name. Optionally creates it if it doesn't exist.
func (cs *ContextService) Get(name string, create bool) (*ContextResult, error) {
	request := &mcp.GetContextRequest{
		Name:          tea.String(name),
		AllowCreate:   tea.Bool(create),
		Authorization: tea.String("Bearer " + cs.AgentBay.APIKey),
	}

	// Log API request
	fmt.Println("API Call: GetContext")
	fmt.Printf("Request: Name=%s, AllowCreate=%t\n", *request.Name, *request.AllowCreate)

	response, err := cs.AgentBay.Client.GetContext(request)

	// Extract RequestID
	requestID := models.ExtractRequestID(response)

	// Log API response
	if err != nil {
		fmt.Println("Error calling GetContext:", err)
		return &ContextResult{
			ApiResponse: models.ApiResponse{
				RequestID: requestID,
			},
			Success:      false,
			ContextID:    "",
			Context:      nil,
			ErrorMessage: fmt.Sprintf("Failed to get context %s: %v", name, err),
		}, nil
	}

	if response != nil && response.Body != nil {
		fmt.Println("Response from GetContext:", response.Body)
	}

	// Check for API-level errors
	if response.Body != nil {
		if response.Body.Success != nil && !*response.Body.Success && response.Body.Code != nil {
			errorMsg := "Unknown error"
			if response.Body.Message != nil {
				errorMsg = fmt.Sprintf("[%s] %s", *response.Body.Code, *response.Body.Message)
			} else {
				errorMsg = fmt.Sprintf("[%s] Unknown error", *response.Body.Code)
			}
			return &ContextResult{
				ApiResponse: models.ApiResponse{
					RequestID: requestID,
				},
				Success:      false,
				ContextID:    "",
				Context:      nil,
				ErrorMessage: errorMsg,
			}, nil
		}
	}

	if response.Body == nil || response.Body.Data == nil || response.Body.Data.Id == nil {
		return &ContextResult{
			ApiResponse: models.ApiResponse{
				RequestID: requestID,
			},
			Success:      false,
			ContextID:    "",
			Context:      nil,
			ErrorMessage: "Context ID not found in response",
		}, nil
	}

	// Create context object
	context := &Context{
		ID:         tea.StringValue(response.Body.Data.Id),
		Name:       tea.StringValue(response.Body.Data.Name),
		State:      tea.StringValue(response.Body.Data.State),
		CreatedAt:  tea.StringValue(response.Body.Data.CreateTime),
		LastUsedAt: tea.StringValue(response.Body.Data.LastUsedTime),
		OSType:     tea.StringValue(response.Body.Data.OsType),
	}

	return &ContextResult{
		ApiResponse: models.ApiResponse{
			RequestID: requestID,
		},
		Success:      true,
		ContextID:    tea.StringValue(response.Body.Data.Id),
		Context:      context,
		ErrorMessage: "",
	}, nil
}

// Create creates a new context with the given name.
func (cs *ContextService) Create(name string) (*ContextCreateResult, error) {
	result, err := cs.Get(name, true)
	if err != nil {
		return nil, err
	}

	if result == nil || !result.Success || result.ContextID == "" {
		errorMsg := "failed to create context"
		if result != nil && result.ErrorMessage != "" {
			errorMsg = result.ErrorMessage
		}
		return nil, fmt.Errorf("%s", errorMsg)
	}

	return &ContextCreateResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		ContextID: result.ContextID,
	}, nil
}

// Update updates the specified context.
// Returns a result with success status.
func (cs *ContextService) Update(context *Context) (*ContextModifyResult, error) {
	request := &mcp.ModifyContextRequest{
		Id:            tea.String(context.ID),
		Name:          tea.String(context.Name),
		Authorization: tea.String("Bearer " + cs.AgentBay.APIKey),
	}

	// Log API request
	fmt.Println("API Call: ModifyContext")
	fmt.Printf("Request: Id=%s, Name=%s\n", *request.Id, *request.Name)

	response, err := cs.AgentBay.Client.ModifyContext(request)

	// Log API response
	if err != nil {
		fmt.Println("Error calling ModifyContext:", err)
		return nil, fmt.Errorf("failed to update context %s: %v", context.ID, err)
	}

	// Extract RequestID
	requestID := models.ExtractRequestID(response)

	if response != nil && response.Body != nil {
		fmt.Println("Response from ModifyContext:", response.Body)
	}

	// Check for API-level errors
	if response.Body != nil {
		if response.Body.Success != nil && !*response.Body.Success {
			errorMsg := "Unknown error"
			if response.Body.Code != nil && response.Body.Message != nil {
				errorMsg = fmt.Sprintf("[%s] %s", *response.Body.Code, *response.Body.Message)
			} else if response.Body.Code != nil {
				errorMsg = fmt.Sprintf("[%s] Unknown error", *response.Body.Code)
			}
			return &ContextModifyResult{
				ApiResponse: models.ApiResponse{
					RequestID: requestID,
				},
				Success:      false,
				ErrorMessage: errorMsg,
			}, nil
		}
	}

	return &ContextModifyResult{
		ApiResponse: models.ApiResponse{
			RequestID: requestID,
		},
		Success: true,
	}, nil
}

// Delete deletes the specified context.
func (cs *ContextService) Delete(context *Context) (*ContextDeleteResult, error) {
	request := &mcp.DeleteContextRequest{
		Id:            tea.String(context.ID),
		Authorization: tea.String("Bearer " + cs.AgentBay.APIKey),
	}

	// Log API request
	fmt.Println("API Call: DeleteContext")
	fmt.Printf("Request: Id=%s\n", *request.Id)

	response, err := cs.AgentBay.Client.DeleteContext(request)

	// Log API response
	if err != nil {
		fmt.Println("Error calling DeleteContext:", err)
		return nil, fmt.Errorf("failed to delete context %s: %v", context.ID, err)
	}

	// Extract RequestID
	requestID := models.ExtractRequestID(response)

	if response != nil && response.Body != nil {
		fmt.Println("Response from DeleteContext:", response.Body)
	}

	// Check for API-level errors
	if response.Body != nil {
		if response.Body.Success != nil && !*response.Body.Success {
			errorMsg := "Unknown error"
			if response.Body.Code != nil && response.Body.Message != nil {
				errorMsg = fmt.Sprintf("[%s] %s", *response.Body.Code, *response.Body.Message)
			} else if response.Body.Code != nil {
				errorMsg = fmt.Sprintf("[%s] Unknown error", *response.Body.Code)
			}
			return &ContextDeleteResult{
				ApiResponse: models.ApiResponse{
					RequestID: requestID,
				},
				Success:      false,
				ErrorMessage: errorMsg,
			}, nil
		}
	}

	return &ContextDeleteResult{
		ApiResponse: models.ApiResponse{
			RequestID: requestID,
		},
		Success: true,
	}, nil
}

// ContextFileUrlResult represents a presigned URL operation result.
type ContextFileUrlResult struct {
	models.ApiResponse
	Success      bool
	Url          string
	ExpireTime   *int64
	ErrorMessage string
}

// ContextFileEntry represents a file item in a context.
type ContextFileEntry struct {
	FileID      string
	FileName    string
	FilePath    string
	FileType    string
	GmtCreate   string
	GmtModified string
	Size        int64
	Status      string
}

// ContextFileListResult represents the result of listing files under a context path.
type ContextFileListResult struct {
	models.ApiResponse
	Success      bool
	Entries      []*ContextFileEntry
	Count        *int32
	ErrorMessage string
}

// ContextFileDeleteResult represents the result of deleting a file in a context.
type ContextFileDeleteResult struct {
	models.ApiResponse
	Success      bool
	ErrorMessage string
}

// GetFileDownloadUrl gets a presigned download URL for a file in a context.
func (cs *ContextService) GetFileDownloadUrl(contextID string, filePath string) (*ContextFileUrlResult, error) {
	req := &mcp.GetContextFileDownloadUrlRequest{
		Authorization: tea.String("Bearer " + cs.AgentBay.APIKey),
		ContextId:     tea.String(contextID),
		FilePath:      tea.String(filePath),
	}

	fmt.Println("API Call: GetContextFileDownloadUrl")
	fmt.Printf("Request: ContextId=%s, FilePath=%s\n", contextID, filePath)

	resp, err := cs.AgentBay.Client.GetContextFileDownloadUrl(req)
	if err != nil {
		fmt.Println("Error calling GetContextFileDownloadUrl:", err)
		return nil, err
	}

	requestID := models.ExtractRequestID(resp)

	success := false
	var url string
	var expire *int64
	var errorMessage string

	if resp != nil && resp.Body != nil {
		if resp.Body.Success != nil {
			success = *resp.Body.Success
		}

		// Check for API-level errors
		if !success && resp.Body.Code != nil {
			code := tea.StringValue(resp.Body.Code)
			message := tea.StringValue(resp.Body.Message)
			if message == "" {
				message = "Unknown error"
			}
			errorMessage = fmt.Sprintf("[%s] %s", code, message)
			return &ContextFileUrlResult{
				ApiResponse:  models.WithRequestID(requestID),
				Success:      false,
				Url:          "",
				ExpireTime:   nil,
				ErrorMessage: errorMessage,
			}, nil
		}

		if resp.Body.Data != nil {
			if resp.Body.Data.Url != nil {
				url = *resp.Body.Data.Url
			}
			if resp.Body.Data.ExpireTime != nil {
				expire = resp.Body.Data.ExpireTime
			}
		}
		fmt.Println("Response from GetContextFileDownloadUrl:", resp.Body)
	}

	return &ContextFileUrlResult{
		ApiResponse:  models.WithRequestID(requestID),
		Success:      success,
		Url:          url,
		ExpireTime:   expire,
		ErrorMessage: "",
	}, nil
}

// GetFileUploadUrl gets a presigned upload URL for a file in a context.
func (cs *ContextService) GetFileUploadUrl(contextID string, filePath string) (*ContextFileUrlResult, error) {
	req := &mcp.GetContextFileUploadUrlRequest{
		Authorization: tea.String("Bearer " + cs.AgentBay.APIKey),
		ContextId:     tea.String(contextID),
		FilePath:      tea.String(filePath),
	}

	fmt.Println("API Call: GetContextFileUploadUrl")
	fmt.Printf("Request: ContextId=%s, FilePath=%s\n", contextID, filePath)

	resp, err := cs.AgentBay.Client.GetContextFileUploadUrl(req)
	if err != nil {
		fmt.Println("Error calling GetContextFileUploadUrl:", err)
		return nil, err
	}

	requestID := models.ExtractRequestID(resp)

	success := false
	var url string
	var expire *int64
	var errorMessage string

	if resp != nil && resp.Body != nil {
		if resp.Body.Success != nil {
			success = *resp.Body.Success
		}

		// Check for API-level errors
		if !success && resp.Body.Code != nil {
			code := tea.StringValue(resp.Body.Code)
			message := tea.StringValue(resp.Body.Message)
			if message == "" {
				message = "Unknown error"
			}
			errorMessage = fmt.Sprintf("[%s] %s", code, message)
			return &ContextFileUrlResult{
				ApiResponse:  models.WithRequestID(requestID),
				Success:      false,
				Url:          "",
				ExpireTime:   nil,
				ErrorMessage: errorMessage,
			}, nil
		}

		if resp.Body.Data != nil {
			if resp.Body.Data.Url != nil {
				url = *resp.Body.Data.Url
			}
			if resp.Body.Data.ExpireTime != nil {
				expire = resp.Body.Data.ExpireTime
			}
		}
		fmt.Println("Response from GetContextFileUploadUrl:", resp.Body)
	}

	return &ContextFileUrlResult{
		ApiResponse:  models.WithRequestID(requestID),
		Success:      success,
		Url:          url,
		ExpireTime:   expire,
		ErrorMessage: "",
	}, nil
}

// ListFiles lists files under a specific folder path in a context.
func (cs *ContextService) ListFiles(contextID string, parentFolderPath string, pageNumber int32, pageSize int32) (*ContextFileListResult, error) {
	req := &mcp.DescribeContextFilesRequest{
		Authorization:    tea.String("Bearer " + cs.AgentBay.APIKey),
		PageNumber:       tea.Int32(pageNumber),
		PageSize:         tea.Int32(pageSize),
		ParentFolderPath: tea.String(parentFolderPath),
		ContextId:        tea.String(contextID),
	}

	fmt.Println("API Call: DescribeContextFiles")
	fmt.Printf("Request: ContextId=%s, ParentFolderPath=%s, PageNumber=%d, PageSize=%d\n", contextID, parentFolderPath, pageNumber, pageSize)

	resp, err := cs.AgentBay.Client.DescribeContextFiles(req)
	if err != nil {
		fmt.Println("Error calling DescribeContextFiles:", err)
		return nil, err
	}

	requestID := models.ExtractRequestID(resp)

	entries := []*ContextFileEntry{}
	success := false
	var count *int32
	var errorMessage string

	if resp != nil && resp.Body != nil {
		if resp.Body.Success != nil {
			success = *resp.Body.Success
		}

		// Check for API-level errors
		if !success && resp.Body.Code != nil {
			code := tea.StringValue(resp.Body.Code)
			message := tea.StringValue(resp.Body.Message)
			if message == "" {
				message = "Unknown error"
			}
			errorMessage = fmt.Sprintf("[%s] %s", code, message)
			return &ContextFileListResult{
				ApiResponse:  models.WithRequestID(requestID),
				Success:      false,
				Entries:      []*ContextFileEntry{},
				Count:        nil,
				ErrorMessage: errorMessage,
			}, nil
		}

		if resp.Body.Count != nil {
			count = resp.Body.Count
		}
		for _, it := range resp.Body.Data {
			if it == nil {
				continue
			}
			entry := &ContextFileEntry{}
			if it.FileId != nil {
				entry.FileID = *it.FileId
			}
			if it.FileName != nil {
				entry.FileName = *it.FileName
			}
			if it.FilePath != nil {
				entry.FilePath = *it.FilePath
			}
			if it.FileType != nil {
				entry.FileType = *it.FileType
			}
			if it.GmtCreate != nil {
				entry.GmtCreate = *it.GmtCreate
			}
			if it.GmtModified != nil {
				entry.GmtModified = *it.GmtModified
			}
			if it.Size != nil {
				entry.Size = *it.Size
			}
			if it.Status != nil {
				entry.Status = *it.Status
			}
			entries = append(entries, entry)
		}
		fmt.Println("Response from DescribeContextFiles:", resp.Body)
	}

	return &ContextFileListResult{
		ApiResponse:  models.WithRequestID(requestID),
		Success:      success,
		Entries:      entries,
		Count:        count,
		ErrorMessage: "",
	}, nil
}

// DeleteFile deletes a file in a context.
func (cs *ContextService) DeleteFile(contextID string, filePath string) (*ContextFileDeleteResult, error) {
	req := &mcp.DeleteContextFileRequest{
		Authorization: tea.String("Bearer " + cs.AgentBay.APIKey),
		ContextId:     tea.String(contextID),
		FilePath:      tea.String(filePath),
	}

	fmt.Println("API Call: DeleteContextFile")
	fmt.Printf("Request: ContextId=%s, FilePath=%s\n", contextID, filePath)

	resp, err := cs.AgentBay.Client.DeleteContextFile(req)
	if err != nil {
		fmt.Println("Error calling DeleteContextFile:", err)
		return nil, err
	}

	requestID := models.ExtractRequestID(resp)
	success := false
	var errorMessage string

	if resp != nil && resp.Body != nil {
		if resp.Body.Success != nil {
			success = *resp.Body.Success
		}

		// Check for API-level errors
		if !success && resp.Body.Code != nil {
			code := tea.StringValue(resp.Body.Code)
			message := tea.StringValue(resp.Body.Message)
			if message == "" {
				message = "Failed to delete file"
			}
			errorMessage = fmt.Sprintf("[%s] %s", code, message)
		}

		fmt.Println("Response from DeleteContextFile:", resp.Body)
	}

	return &ContextFileDeleteResult{
		ApiResponse:  models.WithRequestID(requestID),
		Success:      success,
		ErrorMessage: errorMessage,
	}, nil
}
