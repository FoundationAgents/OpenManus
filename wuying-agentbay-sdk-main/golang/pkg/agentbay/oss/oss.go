package oss

import (
	"fmt"

	mcp "github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

// EnvInitResult represents the result of OSS environment initialization
type EnvInitResult struct {
	models.ApiResponse
	Result string
}

// UploadResult represents the result of a file upload operation
type UploadResult struct {
	models.ApiResponse
	URL string
}

// DownloadResult represents the result of a file download operation
type DownloadResult struct {
	models.ApiResponse
	LocalPath string
}

// OSSManager handles Object Storage Service operations in the AgentBay cloud environment
type OSSManager struct {
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

// NewOss creates a new OSS manager instance
func NewOss(session interface {
	GetAPIKey() string
	GetClient() *mcp.Client
	GetSessionId() string
	IsVpc() bool
	NetworkInterfaceIp() string
	HttpPort() string
	FindServerForTool(toolName string) string
	CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error)
}) *OSSManager {
	return &OSSManager{
		Session: session,
	}
}

// EnvInit initializes OSS environment variables with the specified endpoint, access key ID, access key secret, security token, and region
func (o *OSSManager) EnvInit(accessKeyId, accessKeySecret, securityToken, endpoint, region string) (*EnvInitResult, error) {
	// Build arguments map
	args := map[string]interface{}{
		"access_key_id":     accessKeyId,
		"access_key_secret": accessKeySecret,
		"security_token":    securityToken,
	}

	// Add optional parameters if provided
	if endpoint != "" {
		args["endpoint"] = endpoint
	}
	if region != "" {
		args["region"] = region
	}

	result, err := o.Session.CallMcpTool("oss_env_init", args)
	if err != nil {
		return nil, fmt.Errorf("error initializing OSS environment: %w", err)
	}

	return &EnvInitResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Result: result.Data,
	}, nil
}

// Upload uploads a local file or directory to the specified OSS bucket
func (o *OSSManager) Upload(bucket, object, path string) (*UploadResult, error) {
	args := map[string]interface{}{
		"bucket": bucket,
		"object": object,
		"path":   path,
	}

	result, err := o.Session.CallMcpTool("oss_upload", args)
	if err != nil {
		return nil, fmt.Errorf("error uploading to OSS: %w", err)
	}

	return &UploadResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		URL: result.Data,
	}, nil
}

// UploadAnonymous uploads a local file or directory to the specified URL using HTTP PUT
func (o *OSSManager) UploadAnonymous(url, path string) (*UploadResult, error) {
	args := map[string]interface{}{
		"url":  url,
		"path": path,
	}

	result, err := o.Session.CallMcpTool("oss_upload_annon", args)
	if err != nil {
		return nil, fmt.Errorf("error uploading anonymously: %w", err)
	}

	return &UploadResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		URL: result.Data,
	}, nil
}

// Download downloads an object from the specified OSS bucket to the given local path
func (o *OSSManager) Download(bucket, object, path string) (*DownloadResult, error) {
	args := map[string]interface{}{
		"bucket": bucket,
		"object": object,
		"path":   path,
	}

	result, err := o.Session.CallMcpTool("oss_download", args)
	if err != nil {
		return nil, fmt.Errorf("error downloading from OSS: %w", err)
	}

	return &DownloadResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		LocalPath: path,
	}, nil
}

// DownloadAnonymous downloads a file from the specified URL to the given local path
func (o *OSSManager) DownloadAnonymous(url, path string) (*DownloadResult, error) {
	args := map[string]interface{}{
		"url":  url,
		"path": path,
	}

	result, err := o.Session.CallMcpTool("oss_download_annon", args)
	if err != nil {
		return nil, fmt.Errorf("error downloading anonymously: %w", err)
	}

	return &DownloadResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		LocalPath: path,
	}, nil
}
