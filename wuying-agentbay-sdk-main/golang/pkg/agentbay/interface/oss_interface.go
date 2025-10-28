package interfaces

import (
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/oss"
)

//go:generate mockgen -destination=../../../tests/pkg/unit/mock/mock_oss.go -package=mock github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/interface OSSInterface

// OSSInterface defines the interface for OSS operations
type OSSInterface interface {
	// EnvInit initializes the OSS environment
	EnvInit(accessKeyId, accessKeySecret, securityToken, endpoint, region string) (*oss.EnvInitResult, error)

	// Upload uploads a file to OSS
	Upload(bucket, object, path string) (*oss.UploadResult, error)

	// UploadAnonymous uploads a file to OSS anonymously
	UploadAnonymous(url, path string) (*oss.UploadResult, error)

	// Download downloads a file from OSS
	Download(bucket, object, path string) (*oss.DownloadResult, error)

	// DownloadAnonymous downloads a file from OSS anonymously
	DownloadAnonymous(url, path string) (*oss.DownloadResult, error)
}
