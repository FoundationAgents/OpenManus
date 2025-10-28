# OSS API Reference

The OSS (Object Storage Service) module provides functionality for interacting with cloud storage services.

## 📖 Related Tutorial

- [OSS Integration Guide](../../../docs/guides/common-features/advanced/oss-integration.md) - Detailed tutorial on integrating with Object Storage Service

## Oss Struct

The `Oss` struct provides methods for OSS operations.

### EnvInit

Creates and initializes OSS environment variables with the specified credentials.

```go
func (o *Oss) EnvInit(accessKeyId, accessKeySecret, securityToken, endpoint, region string) (*EnvInitResult, error)
```

**Parameters:**
- `accessKeyId`: The Access Key ID for OSS authentication.
- `accessKeySecret`: The Access Key Secret for OSS authentication.
- `securityToken`: The security token for OSS authentication.
- `endpoint`: The OSS service endpoint. If not specified, the default is used.
- `region`: The OSS region. If not specified, the default is used.

**Returns:**
- `*EnvInitResult`: A result object containing the initialization result and RequestID.
- `error`: An error if the operation fails.

**EnvInitResult Structure:**
```go
type EnvInitResult struct {
    RequestID string // Unique request identifier for debugging
    Result    string // The result of the environment initialization operation
}
```

**Example:**
```go
package main

import (
	"fmt"
	"os"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	// Initialize the SDK
	client, err := agentbay.NewAgentBay("your_api_key", nil)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Create a session first
	sessionResult, err := client.Create(agentbay.NewCreateSessionParams())
	if err != nil {
		fmt.Printf("Error creating session: %v\n", err)
		os.Exit(1)
	}
	session := sessionResult.Session

	// Initialize OSS environment
	result, err := session.Oss.EnvInit(
		"your_access_key_id",
		"your_access_key_secret",
		"your_security_token",
		"oss-cn-hangzhou.aliyuncs.com",
		"cn-hangzhou",
	)
	if err != nil {
		fmt.Printf("Error initializing OSS environment: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("OSS environment initialized successfully, request ID: %s\n", result.RequestID)
}
```

### Upload

**Note:** Before calling this API, you must call `EnvInit` to initialize the OSS environment.

Uploads a local file or directory to OSS.

```go
func (o *Oss) Upload(bucket, object, path string) (*UploadResult, error)
```

**Parameters:**
- `bucket`: OSS bucket name.
- `object`: Object key in OSS.
- `path`: Local file or directory path to upload.

**Returns:**
- `*UploadResult`: A result object containing the upload URL and RequestID.
- `error`: An error if the operation fails.

**UploadResult Structure:**
```go
type UploadResult struct {
    RequestID string // Unique request identifier for debugging
    URL       string // The URL of the uploaded file
}
```

**Example:**
```go
package main

import (
	"fmt"
	"os"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	// Initialize the SDK
	client, err := agentbay.NewAgentBay("your_api_key", nil)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Create a session first
	sessionResult, err := client.Create(agentbay.NewCreateSessionParams())
	if err != nil {
		fmt.Printf("Error creating session: %v\n", err)
		os.Exit(1)
	}
	session := sessionResult.Session

	// Step 1: Initialize OSS environment
	_, err = session.Oss.EnvInit(
		"your_access_key_id",
		"your_access_key_secret",
		"your_security_token",
		"oss-cn-hangzhou.aliyuncs.com",
		"cn-hangzhou",
	)
	if err != nil {
		fmt.Printf("Error initializing OSS environment: %v\n", err)
		os.Exit(1)
	}

	// Step 2: Upload file to OSS
	result, err := session.Oss.Upload("my-bucket", "my-object", "/path/to/local/file")
	if err != nil {
		fmt.Printf("Error uploading file: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("File uploaded successfully, URL: %s, request ID: %s\n", result.URL, result.RequestID)
}
```

### UploadAnonymous

**Note:** Before calling this API, you must call `EnvInit` to initialize the OSS environment.

Uploads a local file or directory to a URL anonymously.

```go
func (o *Oss) UploadAnonymous(url, path string) (*UploadResult, error)
```

**Parameters:**
- `url`: The HTTP/HTTPS URL to upload the file to.
- `path`: Local file or directory path to upload.

**Returns:**
- `*UploadResult`: A result object containing the upload URL and RequestID.
- `error`: An error if the operation fails.

**Example:**
```go
package main

import (
	"fmt"
	"os"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	// Initialize the SDK
	client, err := agentbay.NewAgentBay("your_api_key", nil)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Create a session first
	sessionResult, err := client.Create(agentbay.NewCreateSessionParams())
	if err != nil {
		fmt.Printf("Error creating session: %v\n", err)
		os.Exit(1)
	}
	session := sessionResult.Session

	// Step 1: Initialize OSS environment
	_, err = session.Oss.EnvInit(
		"your_access_key_id",
		"your_access_key_secret",
		"your_security_token",
		"oss-cn-hangzhou.aliyuncs.com",
		"cn-hangzhou",
	)
	if err != nil {
		fmt.Printf("Error initializing OSS environment: %v\n", err)
		os.Exit(1)
	}

	// Step 2: Upload file anonymously
	result, err := session.Oss.UploadAnonymous("https://example.com/upload", "/path/to/local/file")
	if err != nil {
		fmt.Printf("Error uploading file anonymously: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("File uploaded anonymously successfully, URL: %s, request ID: %s\n", result.URL, result.RequestID)
}
```

### Download

**Note:** Before calling this API, you must call `EnvInit` to initialize the OSS environment.

Downloads an object from OSS to a local file.

```go
func (o *Oss) Download(bucket, object, path string) (*DownloadResult, error)
```

**Parameters:**
- `bucket`: OSS bucket name.
- `object`: Object key in OSS.
- `path`: Local path to save the downloaded file.

**Returns:**
- `*DownloadResult`: A result object containing the local file path and RequestID.
- `error`: An error if the operation fails.

**DownloadResult Structure:**
```go
type DownloadResult struct {
    RequestID string // Unique request identifier for debugging
    LocalPath string // The local path where the file was downloaded
}
```

**Example:**
```go
package main

import (
	"fmt"
	"os"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	// Initialize the SDK
	client, err := agentbay.NewAgentBay("your_api_key", nil)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Create a session first
	sessionResult, err := client.Create(agentbay.NewCreateSessionParams())
	if err != nil {
		fmt.Printf("Error creating session: %v\n", err)
		os.Exit(1)
	}
	session := sessionResult.Session

	// Step 1: Initialize OSS environment
	_, err = session.Oss.EnvInit(
		"your_access_key_id",
		"your_access_key_secret",
		"your_security_token",
		"oss-cn-hangzhou.aliyuncs.com",
		"cn-hangzhou",
	)
	if err != nil {
		fmt.Printf("Error initializing OSS environment: %v\n", err)
		os.Exit(1)
	}

	// Step 2: Download file from OSS
	result, err := session.Oss.Download("my-bucket", "my-object", "/path/to/local/file")
	if err != nil {
		fmt.Printf("Error downloading file: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("File downloaded successfully to: %s, request ID: %s\n", result.LocalPath, result.RequestID)
}
```

### DownloadAnonymous

**Note:** Before calling this API, you must call `EnvInit` to initialize the OSS environment.

Downloads a file from a URL anonymously to a local file.

```go
func (o *Oss) DownloadAnonymous(url, path string) (*DownloadResult, error)
```

**Parameters:**
- `url`: The HTTP/HTTPS URL to download the file from.
- `path`: The full local file path to save the downloaded file.

**Returns:**
- `*DownloadResult`: A result object containing the local file path and RequestID.
- `error`: An error if the operation fails.

**Example:**
```go
package main

import (
	"fmt"
	"os"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func main() {
	// Initialize the SDK
	client, err := agentbay.NewAgentBay("your_api_key", nil)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Create a session first
	sessionResult, err := client.Create(agentbay.NewCreateSessionParams())
	if err != nil {
		fmt.Printf("Error creating session: %v\n", err)
		os.Exit(1)
	}
	session := sessionResult.Session

	// Step 1: Initialize OSS environment
	_, err = session.Oss.EnvInit(
		"your_access_key_id",
		"your_access_key_secret",
		"your_security_token",
		"oss-cn-hangzhou.aliyuncs.com",
		"cn-hangzhou",
	)
	if err != nil {
		fmt.Printf("Error initializing OSS environment: %v\n", err)
		os.Exit(1)
	}

	// Step 2: Download file anonymously
	result, err := session.Oss.DownloadAnonymous("https://example.com/file.txt", "/path/to/local/file.txt")
	if err != nil {
		fmt.Printf("Error downloading file anonymously: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("File downloaded anonymously successfully to: %s, request ID: %s\n", result.LocalPath, result.RequestID)
}
```

## Related Resources

- [Filesystem API Reference](filesystem.md)
- [Session API Reference](session.md)