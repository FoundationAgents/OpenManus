package agentbay_test

import (
	"fmt"
	"os"
	"strings"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

func TestOss_EnvInit(t *testing.T) {
	// Setup session with cleanup and ImageId set to code_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("code_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test OSS EnvInit
	if session.Oss != nil {
		accessKeyId := os.Getenv("OSS_ACCESS_KEY_ID")
		if accessKeyId == "" {
			t.Log("OSS_ACCESS_KEY_ID environment variable not set, using default value")
			accessKeyId = "test-access-key-id"
		}

		accessKeySecret := os.Getenv("OSS_ACCESS_KEY_SECRET")
		if accessKeySecret == "" {
			t.Log("OSS_ACCESS_KEY_SECRET environment variable not set, using default value")
			accessKeySecret = "test-access-key-secret"
		}

		securityToken := os.Getenv("OSS_SECURITY_TOKEN")
		if securityToken == "" {
			t.Log("OSS_SECURITY_TOKEN environment variable not set, using default value")
			securityToken = "test-security-token"
		}

		endpoint := os.Getenv("OSS_ENDPOINT")
		if endpoint == "" {
			t.Log("OSS_ENDPOINT environment variable not set, using default value")
			endpoint = "https://oss-cn-hangzhou.aliyuncs.com"
		}

		region := os.Getenv("OSS_REGION")
		if region == "" {
			t.Log("OSS_REGION environment variable not set, using default value")
			region = "cn-hangzhou"
		}

		fmt.Println("Initializing OSS environment...")
		envInitResult, err := session.Oss.EnvInit(accessKeyId, accessKeySecret, securityToken, endpoint, region)
		if err != nil {
			t.Errorf("OSS environment initialization failed: %v", err)
		} else {
			t.Logf("OSS environment initialization successful (RequestID: %s)", envInitResult.RequestID)
			t.Logf("EnvInit result: %s", envInitResult.Result)

			// Check if response contains "tool not found"
			if strings.Contains(envInitResult.Result, "tool not found") {
				t.Errorf("Oss.EnvInit returned 'tool not found'")
			}
		}
	} else {
		t.Logf("Note: OSS interface is nil, skipping OSS test")
	}
}

func TestOss_Upload(t *testing.T) {
	// Setup session with cleanup and ImageId set to code_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("code_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test OSS Upload
	if session.Oss != nil {
		// First initialize the OSS environment
		accessKeyId := os.Getenv("OSS_ACCESS_KEY_ID")
		if accessKeyId == "" {
			t.Log("OSS_ACCESS_KEY_ID environment variable not set, using default value")
			accessKeyId = "test-access-key-id"
		}

		accessKeySecret := os.Getenv("OSS_ACCESS_KEY_SECRET")
		if accessKeySecret == "" {
			t.Log("OSS_ACCESS_KEY_SECRET environment variable not set, using default value")
			accessKeySecret = "test-access-key-secret"
		}

		securityToken := os.Getenv("OSS_SECURITY_TOKEN")
		if securityToken == "" {
			t.Log("OSS_SECURITY_TOKEN environment variable not set, using default value")
			securityToken = "test-security-token"
		}

		endpoint := os.Getenv("OSS_ENDPOINT")
		if endpoint == "" {
			t.Log("OSS_ENDPOINT environment variable not set, using default value")
			endpoint = "https://oss-cn-hangzhou.aliyuncs.com"
		}

		region := os.Getenv("OSS_REGION")
		if region == "" {
			t.Log("OSS_REGION environment variable not set, using default value")
			region = "cn-hangzhou"
		}

		initResult, err := session.Oss.EnvInit(accessKeyId, accessKeySecret, securityToken, endpoint, region)
		if err != nil {
			t.Fatalf("Failed to initialize OSS environment: %v", err)
		}
		t.Logf("OSS environment initialized (RequestID: %s)", initResult.RequestID)

		// Create a test file to upload
		testContent := "This is a test file for OSS upload."
		testFilePath := "/tmp/test_oss_upload.txt"
		if session.FileSystem != nil {
			writeResult, err := session.FileSystem.WriteFile(testFilePath, testContent, "overwrite")
			if err != nil {
				t.Fatalf("Failed to create test file for upload: %v", err)
			}
			t.Logf("Test file created (RequestID: %s)", writeResult.RequestID)
		} else {
			t.Skip("FileSystem interface is nil, skipping upload test")
		}

		fmt.Println("Uploading file to OSS...")
		bucket := os.Getenv("OSS_TEST_BUCKET")
		if bucket == "" {
			bucket = "test-bucket"
		}
		objectKey := "test-object.txt"
		uploadResult, err := session.Oss.Upload(bucket, objectKey, testFilePath)
		if err != nil {
			t.Errorf("OSS upload failed: %v", err)
		} else {
			t.Logf("OSS upload successful (RequestID: %s)", uploadResult.RequestID)
			t.Logf("Upload URL: %s", uploadResult.URL)

			// Check if response contains "tool not found"
			if strings.Contains(uploadResult.URL, "tool not found") {
				t.Errorf("Oss.Upload returned 'tool not found'")
			}
		}
	} else {
		t.Logf("Note: OSS interface is nil, skipping OSS test")
	}
}

func TestOss_UploadAnonymous(t *testing.T) {
	// Setup session with cleanup and ImageId set to code_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("code_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test OSS UploadAnonymous
	if session.Oss != nil {
		// Create a test file to upload
		testContent := "This is a test file for OSS anonymous upload."
		testFilePath := "/tmp/test_oss_upload_anon.txt"
		if session.FileSystem != nil {
			writeResult, err := session.FileSystem.WriteFile(testFilePath, testContent, "overwrite")
			if err != nil {
				t.Fatalf("Failed to create test file for anonymous upload: %v", err)
			}
			t.Logf("Test file created (RequestID: %s)", writeResult.RequestID)
		} else {
			t.Skip("FileSystem interface is nil, skipping anonymous upload test")
		}

		fmt.Println("Uploading file to OSS anonymously...")
		url := os.Getenv("OSS_TEST_URL")
		if url == "" {
			// This is a placeholder URL for testing purposes
			url = "https://example.oss-cn-hangzhou.aliyuncs.com/test-upload-url"
		}

		result, err := session.Oss.UploadAnonymous(url, testFilePath)
		if err != nil {
			// This is expected to fail in most tests since we're using a fake URL
			t.Logf("OSS anonymous upload failed (as expected): %v", err)
		} else {
			t.Logf("OSS anonymous upload successful (RequestID: %s)", result.RequestID)
			t.Logf("Upload URL: %s", result.URL)
		}
	} else {
		t.Logf("Note: OSS interface is nil, skipping OSS anonymous upload test")
	}
}

func TestOss_Download(t *testing.T) {
	// Setup session with cleanup and ImageId set to code_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("code_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test OSS Download
	if session.Oss != nil {
		// First initialize the OSS environment
		accessKeyId := os.Getenv("OSS_ACCESS_KEY_ID")
		if accessKeyId == "" {
			t.Log("OSS_ACCESS_KEY_ID environment variable not set, using default value")
			accessKeyId = "test-access-key-id"
		}

		accessKeySecret := os.Getenv("OSS_ACCESS_KEY_SECRET")
		if accessKeySecret == "" {
			t.Log("OSS_ACCESS_KEY_SECRET environment variable not set, using default value")
			accessKeySecret = "test-access-key-secret"
		}

		securityToken := os.Getenv("OSS_SECURITY_TOKEN")
		if securityToken == "" {
			t.Log("OSS_SECURITY_TOKEN environment variable not set, using default value")
			securityToken = "test-security-token"
		}

		endpoint := os.Getenv("OSS_ENDPOINT")
		if endpoint == "" {
			t.Log("OSS_ENDPOINT environment variable not set, using default value")
			endpoint = "https://oss-cn-hangzhou.aliyuncs.com"
		}

		region := os.Getenv("OSS_REGION")
		if region == "" {
			t.Log("OSS_REGION environment variable not set, using default value")
			region = "cn-hangzhou"
		}

		initResult, err := session.Oss.EnvInit(accessKeyId, accessKeySecret, securityToken, endpoint, region)
		if err != nil {
			t.Fatalf("Failed to initialize OSS environment: %v", err)
		}
		t.Logf("OSS environment initialized (RequestID: %s)", initResult.RequestID)

		fmt.Println("Downloading file from OSS...")
		bucket := os.Getenv("OSS_TEST_BUCKET")
		if bucket == "" {
			bucket = "test-bucket"
		}
		objectKey := "test-object.txt"
		downloadPath := "/tmp/test_oss_download.txt"

		result, err := session.Oss.Download(bucket, objectKey, downloadPath)
		if err != nil {
			// This is expected to fail in most tests since we don't have the actual object
			t.Logf("OSS download failed (as expected): %v", err)
		} else {
			t.Logf("OSS download successful (RequestID: %s)", result.RequestID)
			t.Logf("Download LocalPath: %s", result.LocalPath)

			// Verify the downloaded content if the download was successful
			if session.FileSystem != nil {
				readResult, err := session.FileSystem.ReadFile(downloadPath)
				if err != nil {
					t.Logf("Failed to read downloaded file: %v", err)
				} else {
					t.Logf("Downloaded content length: %d bytes", len(readResult.Content))
				}
			}
		}
	} else {
		t.Logf("Note: OSS interface is nil, skipping OSS download test")
	}
}

func TestOss_DownloadAnonymous(t *testing.T) {
	// Setup session with cleanup and ImageId set to code_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("code_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test OSS DownloadAnonymous
	if session.Oss != nil {
		fmt.Println("Downloading file anonymously from OSS...")
		url := os.Getenv("OSS_TEST_DOWNLOAD_URL")
		if url == "" {
			// This is a placeholder URL for testing purposes
			url = "https://example.oss-cn-hangzhou.aliyuncs.com/test-download-url"
		}
		downloadPath := "/tmp/test_oss_download_anon.txt"

		result, err := session.Oss.DownloadAnonymous(url, downloadPath)
		if err != nil {
			// This is expected to fail in most tests since we're using a fake URL
			t.Logf("OSS anonymous download failed (as expected): %v", err)
		} else {
			t.Logf("OSS anonymous download successful (RequestID: %s)", result.RequestID)
			t.Logf("Download LocalPath: %s", result.LocalPath)

			// Verify the downloaded content if the download was successful
			if session.FileSystem != nil {
				readResult, err := session.FileSystem.ReadFile(downloadPath)
				if err != nil {
					t.Logf("Failed to read downloaded file: %v", err)
				} else {
					t.Logf("Downloaded content length: %d bytes", len(readResult.Content))
				}
			}
		}
	} else {
		t.Logf("Note: OSS interface is nil, skipping OSS anonymous download test")
	}
}
